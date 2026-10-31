"""Synthetic browser regressions; these checks are not human measurement evidence."""
import functools
import http.server
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unittest

from playwright.sync_api import expect, sync_playwright
from browser_support import browser_args

ROOT = Path(__file__).resolve().parents[1]
RULES = ['event_exact_repeat', 'registration_missing_date', 'event_unknown_site']
ANSWERS = [(787170, 'review', 'open'), (45, 'review', 'open'), (0, 'block', 'clear')]


class PracticeAccessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'web'))
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/operations-practice.html'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=browser_args())

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)

    def ready(self):
        self.page.goto(self.url)
        self.page.locator('#workspace').wait_for()
        self.page.select_option('#origin', 'developer_synthetic')
        self.page.fill('#context-notes', 'Synthetic accessibility regression; no human participant.')
        self.page.check('#scope-confirm')

    def fill_correct(self):
        for i, (count, severity, status) in enumerate(ANSWERS):
            self.page.fill(f'#count-{i}', str(count))
            self.page.select_option(f'#severity-{i}', severity)
            self.page.select_option(f'#status-{i}', status)
            self.page.check(f'#reviewed-{i}')

    def test_retry_restores_focus_without_stealing_initial_focus(self):
        self.page.goto(self.url)
        self.page.locator('#workspace').wait_for()
        self.assertEqual(self.page.evaluate('document.activeElement.tagName'), 'BODY')
        self.page.route('**/data/report.json', lambda route: route.fulfill(status=503, body='Unavailable'))
        self.page.reload()
        self.page.locator('#load-error').wait_for()
        self.page.locator('#retry').focus()
        self.page.keyboard.press('Enter')
        self.page.locator('#load-error').wait_for()
        expect(self.page.locator('#retry')).to_be_focused()
        self.page.unroute('**/data/report.json')
        self.page.keyboard.press('Enter')
        self.page.locator('#workspace').wait_for()
        expect(self.page.locator('#session-title')).to_be_focused()
        self.page.keyboard.press('Tab')
        expect(self.page.locator('#origin')).to_be_focused()

    def test_every_control_names_its_rule_and_field(self):
        self.ready()
        self.page.click('#start')
        for i, rule in enumerate(RULES):
            for field, label in [('count', '건수'), ('severity', '심각도'), ('status', '상태'), ('reviewed', '대조')]:
                expect(self.page.locator(f'#{field}-{i}')).to_have_accessible_name(re.compile(rf'(?=.*{rule})(?=.*{label})'))

    def test_environment_textarea_boundary_has_three_to_one_contrast(self):
        self.ready()
        colors = self.page.locator('#context-notes').evaluate('el => {const s=getComputedStyle(el); return [s.borderTopColor,s.backgroundColor]}')
        def luminance(color):
            channels = [int(value) / 255 for value in re.findall(r'\d+', color)[:3]]
            linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
            return sum(value * weight for value, weight in zip(linear, [.2126, .7152, .0722]))
        values = sorted(luminance(color) for color in colors)
        self.assertGreaterEqual((values[1] + .05) / (values[0] + .05), 3, colors)

    def test_text_spacing_at_320px_keeps_setup_and_invalid_result_in_page(self):
        self.ready()
        self.page.set_viewport_size({'width': 320, 'height': 900})
        self.page.add_style_tag(content='* {line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important} p {margin-bottom:2em!important}')
        for state in ['ready', 'invalid']:
            if state == 'invalid':
                self.page.click('#start')
                self.page.click('#finish')
            geometry = self.page.evaluate('({page:document.documentElement.scrollWidth, viewport:innerWidth})')
            self.assertLessEqual(geometry['page'], geometry['viewport'], (state, geometry))
            for selector in ['#setup', '#origin', '#context-notes']:
                self.assertTrue(self.page.locator(selector).evaluate('el => el.getBoundingClientRect().right <= innerWidth'), selector)

    def test_empty_finish_identifies_all_omissions_and_unreviewed_rows(self):
        self.ready()
        self.page.click('#start')
        self.page.click('#finish')
        self.assertIn('누락 9', self.page.locator('#result').inner_text())
        for i, rule in enumerate(RULES):
            for field, label in [('count', '건수'), ('severity', '심각도'), ('status', '상태'), ('reviewed', '대조')]:
                control = self.page.locator(f'#{field}-{i}')
                expect(control).to_have_attribute('aria-invalid', 'true')
                expect(control).to_have_accessible_description(re.compile(rf'(?=.*{rule})(?=.*{label})(?=.*(?:누락|미확인))'))
        expect(self.page.locator('#next')).to_have_accessible_description(re.compile('누락 9'))
        self.page.click('#next')
        self.page.click('#start')
        self.assertEqual(self.page.locator('[aria-invalid="true"]').count(), 0)
        self.assertEqual(self.page.locator('#result').inner_text(), '')

    def test_completed_history_can_be_scrolled_with_keyboard_at_320px(self):
        self.ready()
        self.page.set_viewport_size({'width': 320, 'height': 844})
        self.page.click('#start')
        self.page.click('#finish')
        self.page.keyboard.press('Tab')
        history = self.page.locator('#history > .table-wrap')
        expect(history).to_be_focused()
        expect(history).to_have_accessible_name('이 브라우저의 완료 기록')
        self.assertTrue(history.evaluate('el => el.scrollWidth > el.clientWidth'))
        self.page.keyboard.press('ArrowRight')
        self.page.wait_for_function("document.querySelector('#history > .table-wrap').scrollLeft > 0")
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        if axe := os.environ.get('AXE_SCRIPT'):
            self.page.add_script_tag(path=axe)
            violations = self.page.evaluate("async () => (await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']}})).violations.map(v => ({id: v.id, nodes: v.nodes.map(n => n.target)}))")
            self.assertEqual(violations, [])

    def test_invalid_measured_round_identifies_errors_and_stays_in_export(self):
        self.ready()
        for _ in range(2):
            self.page.click('#start')
            self.fill_correct()
            self.page.click('#finish')
            self.page.click('#next')
        self.page.click('#start')
        self.fill_correct()
        self.page.fill('#count-0', '')
        self.page.select_option('#severity-0', 'block')
        self.page.select_option('#status-0', 'clear')
        self.page.uncheck('#reviewed-0')
        self.page.click('#finish')
        result = self.page.locator('#result').inner_text()
        for text in ['누락 1', '기록 오류 2', '대조 미확인 1']:
            self.assertIn(text, result)
        expect(self.page.locator('#severity-0')).to_have_accessible_description(re.compile(r'(?=.*event_exact_repeat)(?=.*심각도)(?=.*오류)(?=.*review)'))
        expect(self.page.locator('#status-0')).to_have_accessible_description(re.compile(r'(?=.*event_exact_repeat)(?=.*상태)(?=.*오류)(?=.*open)'))
        self.assertEqual(self.page.locator('[aria-invalid="true"]').count(), 4)
        expect(self.page.locator('#count-0')).to_be_disabled()
        expect(self.page.locator('#start')).to_be_disabled()
        expect(self.page.locator('#finish')).to_be_disabled()
        self.page.click('#next')
        self.assertIn('측정 2/6', self.page.locator('#round-label').inner_text())
        for i in range(5):
            self.page.click('#start')
            self.fill_correct()
            self.page.click('#finish')
            if i < 4:
                self.page.click('#next')
        with self.page.expect_download() as download:
            self.page.click('#export')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.json'
            download.value.save_as(path)
            payload = json.loads(path.read_text())
        self.assertEqual(payload['protocol'], 'three-rule-transfer-v1')
        self.assertEqual(payload['origin'], 'developer_synthetic')
        self.assertEqual(len(payload['rounds']), 8)
        self.assertEqual([r['mode'] for r in payload['rounds'][2:]], list('ABBAAB'))
        invalid = payload['rounds'][2]
        self.assertFalse(invalid['valid'])
        self.assertEqual((invalid['omissions'], invalid['errors'], invalid['unreviewed']), (1, 2, 1))
        self.assertEqual(invalid['outputs'][0], {'rule_id': 'event_exact_repeat', 'count': None, 'severity': 'block', 'status': 'clear', 'reviewed': False})


if __name__ == '__main__':
    unittest.main()

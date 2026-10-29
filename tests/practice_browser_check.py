"""Developer-driven browser checks; exported data is synthetic, never participant evidence."""
import argparse
import functools
import http.server
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright
from browser_support import browser_args

ROOT=Path(__file__).resolve().parents[1]

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url', help='Public base URL; omit to run a temporary local server')
    args=parser.parse_args()
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'web'))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=(args.url.rstrip('/') if args.url else f'http://127.0.0.1:{server.server_port}')+'/operations-practice.html'
    spec=importlib.util.spec_from_file_location('validator',ROOT/'scripts/import_practice.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(args=browser_args())
        page=browser.new_page(viewport={'width':1280,'height':900})
        response=page.goto(url)
        assert response.status==200,'Exercise page not implemented'
        page.locator('#start').wait_for(state='visible')
        axe=os.environ.get('AXE_SCRIPT')
        def accessibility(target):
            if axe:
                target.add_script_tag(path=axe)
                violations=target.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))")
                assert not violations,violations
        accessibility(page)
        assert page.locator('#start').is_disabled()
        page.select_option('#origin','developer_synthetic')
        page.fill('#context-notes','Automated developer test; no human observation.')
        page.check('#scope-confirm')
        page.locator('#start').focus();page.keyboard.press('Enter')
        page.click('#finish')
        assert '누락 9' in page.locator('#result').inner_text()
        page.click('#next')
        for i,mode in enumerate('ABABBAAB'):
            page.click('#start')
            if i==2:
                page.click('#pause')
                assert page.locator('#finish').is_disabled()
                page.wait_for_timeout(20)
                page.click('#pause')
                # Synthetic visibility event exercises exclusion, not an actual attention observation.
                page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
                assert page.locator('#finish').is_disabled()
                page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'))")
                page.click('#pause')
            if mode=='A':
                for j,(count,severity,status) in enumerate([(787170,'review','open'),(45,'review','open'),(0,'block','clear')]):
                    page.fill(f'#count-{j}',str(count));page.select_option(f'#severity-{j}',severity);page.select_option(f'#status-{j}',status)
            else:assert page.input_value('#count-0')=='787170'
            for j in range(3):page.check(f'#reviewed-{j}')
            page.click('#finish')
            assert '유효' in page.locator('#result').inner_text()
            if i<7:page.click('#next')
        with page.expect_download() as d:page.click('#export')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.json';d.value.save_as(path)
            payload=json.loads(path.read_text());result=module.validate(payload,ROOT/'data/report.json' if (ROOT/'data/report.json').exists() else ROOT/'web/data/report.json')
            assert result['all_measured_rounds_valid'] and not result['comparison_ready'] and not result['human_measurement']
            assert len(payload['rounds'])==9
            assert {s['kind'] for s in payload['rounds'][3]['timing']['segments']}=={'active','manual_pause','hidden'}
        page.close()
        mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        mobile.goto(url);mobile.locator('#start').wait_for()
        assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
        mobile.select_option('#origin','developer_synthetic');mobile.fill('#context-notes','Mobile synthetic check');mobile.check('#scope-confirm');mobile.click('#start')
        assert mobile.locator('#count-0').is_editable()
        accessibility(mobile)
        mobile.set_viewport_size({'width':320,'height':844})
        assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
        accessibility(mobile)
        mobile.close()
        for body in ['{}','{"quality":{"checks":[]}}','not json']:
            bad=browser.new_page()
            bad.route('**/data/report.json',lambda route,request,b=body:route.fulfill(status=200,body=b))
            bad.goto(url);bad.locator('#load-error').wait_for()
            assert bad.locator('#start').is_disabled()
            accessibility(bad)
            bad.unroute('**/data/report.json');bad.click('#retry')
            bad.locator('#workspace').wait_for();bad.close()
        browser.close()
    finally:server.shutdown();server.server_close()
    print('PASS: desktop full synthetic flow + export validation, omissions/review gate, pause/visibility simulation, keyboard, mobile, bad/empty-load recovery')

if __name__=='__main__':run()

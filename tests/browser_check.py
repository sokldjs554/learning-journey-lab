"""Actual task flows against local or deployed static site; exact report comparisons."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8766');ap.add_argument('--label',default='local');a=ap.parse_args()
    expected=json.loads((ROOT/'reports/report.json').read_text());ops=json.loads((ROOT/'web/data/operations.json').read_text())
    evidence=[];out=ROOT/'reports/screenshots';out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        b=p.chromium.launch(args=browser_args())
        for width,height,name in [(1440,900,'desktop'),(390,844,'mobile')]:
            page=b.new_page(viewport={'width':width,'height':height},reduced_motion='reduce');errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(a.url,wait_until='networkidle');page.locator('#app:not([hidden])').wait_for()
            assert '공개 데이터' in page.locator('#real-source').inner_text()
            assert page.locator('#review-list [data-rule]').count()==5
            page.screenshot(path=str(out/f'{a.label}-{name}-cover.png'))
            page.locator('[data-rule="event_exact_repeat"]').click();page.locator('[data-tab="impact"]').click()
            assert '369' in page.locator('#detail-content').inner_text()
            page.screenshot(path=str(out/f'{a.label}-{name}-impact-cover.png'))
            if name=='desktop':
                page.select_option('#rule-filter','all')
                for rule in ops['rules']:
                    page.locator(f'[data-rule="{rule["rule_id"]}"]').click()
                    assert page.locator('#sql-link').get_attribute('href').endswith(f'{rule["sql_file"]}#L{rule["sql_line"]}')
            page.locator('[data-view="analysis"]').click()
            assert page.locator('#eligible').inner_text()=='29,671'
            assert page.locator('#w1').inner_text()=='23,522'
            for c in expected['cohorts'] if name=='desktop' else expected['cohorts'][:1]:
                page.select_option('#cohort',c['module']+'|'+c['term'])
                assert page.locator('#eligible').inner_text()==format(c['eligible'],',')
                assert page.locator('#return-rate').inner_text()==f"{100*c['return_rate']:.1f}%"
                assert page.locator('.day-col strong').all_text_contents()==[f"{100*d['rate']:.1f}%" if d['rate'] is not None else '비교 불가' for d in c['days']]
                assert page.locator('#content-diff').inner_text()==f"{100*c['content_comparison']['difference']:+.1f}%p"
                assert page.locator('#global-evidence').is_hidden()
                page.locator('#show-table').click()
                assert page.locator('#day-table tr').count()==8
                assert page.locator('#day-table tr td:last-child').all_text_contents()==[f"{100*d['rate']:.1f}%" if d['rate'] is not None else '비교 불가' for d in c['days']]
                page.locator('#show-chart').click()
            page.select_option('#cohort','all');page.locator('#cohort-search').fill('no-such-cohort');assert page.locator('#cohort-empty').is_visible();page.locator('#cohort-search').fill('')
            page.locator('[data-view="lab"]').click()
            for stage in expected['fault_lab']['stages']:
                page.locator(f'[data-stage="{stage["id"]}"]').click()
                assert page.locator('#lab-rate').inner_text()==f"{100*stage['rate']:.1f}%"
                assert page.locator('#lab-gate').inner_text()==stage['gate']
            assert '생성 데이터' in page.locator('#real-source').inner_text()
            page.locator('[data-view="plan"]').click();page.locator('.sample-method summary').click()
            for s in expected['experiment']['samples']:
                page.select_option('#baseline',str(s['baseline']));page.select_option('#mde',str(s['mde']))
                assert format(s['per_arm'],',') in page.locator('#sample-size').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors
            evidence.append({'viewport':[width,height],'checks':['first review entry','policy impact','20 exact SQL links (desktop)','22 scoped cohorts + content + chart/table values (desktop)','global isolation','empty search','5 synthetic stages','6 sample scenarios','no horizontal overflow or JS exception'],'status':'pass'});page.close()
        page=b.new_page();page.goto(a.url,wait_until='networkidle');page.keyboard.press('Tab');assert page.locator(':focus').get_attribute('href')=='#main';page.keyboard.press('Enter');assert page.evaluate('document.activeElement.id')=='main'
        page.goto(a.url+'?view=review&detail=1');page.locator('#app:not([hidden])').wait_for();page.locator('#tab-evidence').focus();page.keyboard.press('ArrowRight');assert page.locator(':focus').get_attribute('id')=='tab-impact';page.keyboard.press('End');assert page.locator(':focus').get_attribute('id')=='tab-decision';page.close()
        evidence.append({'checks':['skip link','roving detail tabs arrows/end'],'status':'pass'})
        for asset in ['report','operations']:
            page=b.new_page();pattern=f'**/data/{asset}.json';page.route(pattern,lambda route:route.fulfill(status=500,body='unavailable'))
            page.goto(a.url);page.locator('#error:not([hidden])').wait_for();assert page.locator('#app').is_hidden()
            page.unroute(pattern);page.locator('#retry').click();page.locator('#app:not([hidden])').wait_for();page.close()
            evidence.append({'checks':[f'{asset} HTTP failure and retry'],'status':'pass'})
        b.close()
    (ROOT/f'reports/browser-{a.label}.json').write_text(json.dumps({'url':a.url,'engine':'Chromium 141 / Playwright 1.56','results':evidence},indent=2)+'\n');print(json.dumps(evidence))
if __name__=='__main__':main()

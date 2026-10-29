"""Research-led regressions: tasks, exact evidence, scope and browser history."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8766');ap.add_argument('--label',default='local');a=ap.parse_args()
    report=json.loads((ROOT/'reports/report.json').read_text());out=[]
    with sync_playwright() as p:
        b=p.chromium.launch(args=browser_args())
        for width,height in [(1440,900),(390,844)]:
            page=b.new_page(viewport={'width':width,'height':height},reduced_motion='reduce');page.set_default_timeout(4000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(a.url,wait_until='networkidle');page.locator('#app:not([hidden])').wait_for()
            assert page.locator('#review-list [data-rule]').count()==5,'Review tasks must be the entry point'
            assert page.locator('#review-list [data-rule]').first.bounding_box()['y']<height-80
            page.locator('[data-rule="event_exact_repeat"]').click()
            assert page.locator('#detail-title').is_visible()
            page.locator('[data-tab="impact"]').click();assert '369' in page.locator('#detail-content').inner_text()
            page.reload(wait_until='networkidle');assert page.locator('[data-tab="impact"]').get_attribute('aria-selected')=='true'
            page.locator('[data-tab="decision"]').click();assert '스냅샷' in page.locator('#detail-content').inner_text()
            if width<700:
                page.locator('#detail-back').click()
                assert page.locator(':focus').get_attribute('data-rule')=='event_exact_repeat'
            page.select_option('#rule-filter','all');page.locator('[data-rule="registration_unknown_course"]').click()
            page.locator('[data-tab="evidence"]').click()
            assert '/sql/dimensions.sql#L' in page.locator('#sql-link').get_attribute('href')
            page.locator('[data-view="analysis"]').click();page.select_option('#cohort','AAA|2014J')
            c=next(c for c in report['cohorts'] if c['module']=='AAA' and c['term']=='2014J')
            assert page.locator('#eligible').inner_text()==format(c['eligible'],',')
            assert page.locator('#content-diff').inner_text()==f"{c['content_comparison']['difference']*100:+.1f}%p"
            assert page.locator('#global-evidence').is_hidden()
            assert 'cohort=AAA.2014J' in page.url
            page.reload(wait_until='networkidle');assert page.locator('#cohort').input_value()=='AAA|2014J'
            page.locator('[data-view="runs"]').click();assert page.locator('#run-table tr').count()==3
            page.go_back(wait_until='networkidle');assert page.locator('#cohort').is_visible();assert page.locator('#cohort').input_value()=='AAA|2014J'
            page.locator('[data-view="review"]').click()
            if width<700 and page.locator('#detail-back').is_visible():page.locator('#detail-back').click()
            page.locator('#rule-search').fill('no-such-rule');assert page.locator('#review-empty').is_visible()
            page.goto(a.url+'?view=unknown&rule=wrong&cohort=wrong&tab=wrong',wait_until='networkidle')
            assert page.locator('#view-review').is_visible();assert 'unknown' not in page.url
            assert not errors,errors
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            out.append({'viewport':[width,height],'status':'pass','checks':['task entry','impact and history','exact dimension SQL','URL reload/back/fallback','scoped content + global isolation','run records','empty search','mobile focus return','overflow and JS errors']});page.close()
        b.close()
    (ROOT/f'reports/workbench-{a.label}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()

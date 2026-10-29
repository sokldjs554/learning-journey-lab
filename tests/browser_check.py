"""Run against a local or deployed HTTP URL. Browser assertions, not source-string tests."""
import argparse,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8765');ap.add_argument('--label',default='local');a=ap.parse_args()
    expected=json.loads((ROOT/'reports/report.json').read_text())
    evidence=[];out=ROOT/'reports/screenshots';out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=browser_args())
        for width,height,name in [(1440,1000,'desktop'),(390,844,'mobile')]:
            page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1,reduced_motion='reduce')
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(a.url,wait_until='networkidle');page.locator('#app:not([hidden])').wait_for()
            assert page.locator('#eligible').inner_text()=='29,671'
            assert page.locator('#w1').inner_text()=='23,522'
            assert '공개 데이터' in page.locator('#real-source').inner_text()
            page.select_option('#cohort','AAA|2013J')
            assert page.locator('#eligible').inner_text()!='29,671'
            if name=='desktop':
                for c in expected['cohorts']:
                    page.select_option('#cohort',c['module']+'|'+c['term'])
                    assert page.locator('#eligible').inner_text()==format(c['eligible'],',')
                    assert page.locator('#w1').inner_text()==format(c['w1_active'],',')
                    assert page.locator('#return-rate').inner_text()==f"{100*c['return_rate']:.1f}%"
                    assert page.locator('.day-col strong').all_text_contents()==[f"{100*d['rate']:.1f}%" if d['rate'] is not None else '비교 불가' for d in c['days']]
            page.select_option('#cohort','all')
            page.locator('#cohort-search').fill('no-such-cohort')
            assert page.locator('#cohort-empty').is_visible()
            page.locator('#cohort-search').fill('')
            page.locator('[data-stage="observed"]').click()
            assert page.locator('#lab-rate').inner_text()=='40.0%'
            assert page.locator('#lab-naive').inner_text()=='60.0%'
            page.locator('[data-stage="replay"]').click()
            assert page.locator('#lab-rate').inner_text()=='60.0%'
            assert page.locator('#lab-gate').inner_text()=='PASS'
            page.select_option('#baseline','0.5');page.select_option('#mde','0.03')
            assert '4,356' in page.locator('#sample-size').inner_text()
            page.locator('[data-stage="observed"]').click()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors,errors
            page.evaluate("document.activeElement.blur(); window.scrollTo({top:0,behavior:'instant'})");page.screenshot(path=str(out/f'{a.label}-{name}-cover.png'));page.screenshot(path=str(out/f'{a.label}-{name}.png'),full_page=True)
            evidence.append({'viewport':[width,height],'checks':['summary numbers','all 22 cohort numbers and day-chart labels (desktop)','cohort selection','empty search','fault stage changes','power scenario','no horizontal overflow','no JS exceptions'],'status':'pass'})
            page.close()
        # Keyboard navigation and loading failure use separate contexts.
        page=browser.new_page();page.goto(a.url,wait_until='networkidle');page.keyboard.press('Tab')
        assert page.locator(':focus').get_attribute('href')=='#main'
        page.keyboard.press('Enter');assert page.evaluate('document.activeElement.id')=='main'
        evidence.append({'checks':['skip link and focus transfer'],'status':'pass'})
        page.close();page=browser.new_page()
        page.route('**/data/report.json',lambda route:route.fulfill(status=500,body='unavailable'))
        page.goto(a.url);page.locator('#error:not([hidden])').wait_for()
        assert page.locator('#app').is_hidden()
        page.unroute('**/data/report.json');page.locator('#retry').click();page.locator('#app:not([hidden])').wait_for()
        evidence.append({'checks':['HTTP failure state','retry recovery'],'status':'pass'})
        browser.close()
    (ROOT/f'reports/browser-{a.label}.json').write_text(json.dumps({'url':a.url,'engine':'Chromium 141 / Playwright 1.56','results':evidence},indent=2)+'\n')
    print(json.dumps(evidence))
if __name__=='__main__':main()

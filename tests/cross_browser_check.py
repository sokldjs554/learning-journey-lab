"""Same deployed task checks across real browser engines; no participant evidence."""
import argparse,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--browser',choices=['chromium','firefox','webkit'],required=True);a.add_argument('--url',default='https://learning-journey-lab.onrender.com');a.add_argument('--output',type=Path,required=True);args=a.parse_args()
report=json.loads((ROOT/'reports/report.json').read_text());ednet=json.loads((ROOT/'reports/ednet_report.json').read_text())
result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':os.environ.get('GITHUB_SHA'),'browser':args.browser,'url':args.url,'actual_participant_test':False,'scope':'Automated desktop/mobile viewport emulation. WebKit is not Apple Safari; no physical device or screen-reader participant test.','assets':[],'checks':[],'status':'running'}
try:
 for p in sorted((ROOT/'web').rglob('*')):
  if not p.is_file():continue
  path=p.relative_to(ROOT/'web').as_posix()
  with urlopen(args.url.rstrip('/')+'/'+path,timeout=30) as response:blob=response.read();assert response.status==200
  assert blob==p.read_bytes(),f'Deployed asset differs: {path}'
  result['assets'].append({'path':path,'sha256':hashlib.sha256(blob).hexdigest(),'matches':True})
 with sync_playwright() as pw:
  browser=getattr(pw,args.browser).launch(**({'args':browser_args()} if args.browser=='chromium' else {}));result['version']=browser.version
  for width in [1440,390,320]:
   page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(10000)
   page.goto(args.url,wait_until='networkidle');page.locator('#app:not([hidden])').wait_for()
   page.locator('[data-rule="event_exact_repeat"]').click();page.locator('[data-tab="impact"]').click();assert '14,637 − 14,268 = 369' in page.locator('#policy-meaning').inner_text()
   page.locator('[data-tab="impact"]').focus();page.keyboard.press('End');assert page.locator('[data-tab="decision"]').get_attribute('aria-selected')=='true'
   page.locator('[data-view="analysis"]').click()
   for c in [report['overall'],*report['cohorts']]:
    page.select_option('#cohort','all' if 'module' not in c else c['module']+'|'+c['term'])
    text=page.locator('#return-definition').inner_text();assert f"분자 {c['w2_returned']:,}" in text and f"분모 {c['w1_active']:,}" in text
   page.select_option('#cohort','BBB|2014J');assert '-6.6' in page.locator('#content-diff').inner_text()
   page.select_option('#cohort','all');assert '9개' in page.locator('#counterevidence').inner_text()
   page.fill('#cohort-search','no-such-cohort');assert page.locator('#cohort-empty').is_visible()
   page.goto(args.url+'/?view=plan',wait_until='networkidle');assert '합성 입력 검사 통과' in page.locator('#experiment-checks').inner_text()
   page.goto(args.url+'/external.html',wait_until='networkidle');page.locator('#external-app:not([hidden])').wait_for()
   for c in [ednet['primary'],*ednet['event_definition_sensitivity']]:
    page.select_option('#event-definition',c['definition']);assert f"{c['eligible_firstweek_users']:,}" in page.locator('#external-denominator').inner_text()
    assert page.locator('#external-groups tr td:last-child').all_text_contents()==[f"{g['rate']*100:.1f}%" for g in c['groups']]
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.goto(args.url+'/operations-practice.html',wait_until='networkidle');page.locator('#workspace:not([hidden])').wait_for();assert page.locator('#start').is_disabled()
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors
   result['checks'].append({'width':width,'status':'pass','tasks':['369 policy meaning','keyboard detail tabs','23 scope formulas','negative content example','empty search','synthetic experiment provenance','3 external event definitions','practice preparation gate','overflow and page errors']});page.close()
  for path,asset,selector,retry,recovered in [('/','report.json','#error','#retry','#app:not([hidden])'),('/external.html','ednet_report.json','#external-error','#external-retry','#external-app:not([hidden])')]:
   page=browser.new_page();pattern='**/data/'+asset;page.route(pattern,lambda route:route.fulfill(status=500));page.goto(args.url+path,wait_until='networkidle');assert page.locator(selector).is_visible();page.unroute(pattern);page.locator(retry).click();page.locator(recovered).wait_for();page.close()
  result['checks'].append({'http_failure_and_retry':'pass'});browser.close()
 result['status']='pass'
except Exception as e:
 result['status']='fail';result['error']=str(e);raise
finally:
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('BROWSER_RESULT '+json.dumps(result,ensure_ascii=False))

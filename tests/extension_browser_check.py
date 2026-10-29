"""Actual extended paths + source failures; developer QA, never human feedback."""
import argparse,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--url',default='http://127.0.0.1:8767');a.add_argument('--label',default='local');a.add_argument('--axe');args=a.parse_args()
r=json.loads((ROOT/'reports/ednet_report.json').read_text());e=json.loads((ROOT/'reports/experiment-readiness.json').read_text());results=[];out=ROOT/'reports/screenshots';out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(args=browser_args())
 for width in [1440,390,320]:
  page=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');errors=[];page.on('pageerror',lambda x:errors.append(str(x)))
  page.goto(args.url+'/external.html',wait_until='networkidle');page.locator('#external-app:not([hidden])').wait_for()
  for c in [r['primary'],*r['event_definition_sensitivity']]:
   page.select_option('#event-definition',c['definition']);assert page.locator('#external-groups tr td:last-child').all_text_contents()==[f"{g['rate']*100:.1f}%" for g in c['groups']]
   assert f"{c['eligible_firstweek_users']:,}" in page.locator('#external-denominator').inner_text()
  page.select_option('#event-definition','submit');assert '173' in page.locator('#payment-summary').inner_text()
  assert '23명' in page.locator('#definition-impact').inner_text() and '14명' in page.locator('#definition-impact').inner_text()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  for selector in ['#definition','#payments','#source']:page.locator(f'a[href="{selector}"]').click();assert page.locator(selector).is_visible()
  page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/f'{args.label}-external-{width}.png'),full_page=True)
  if args.axe:
   page.add_script_tag(path=args.axe);violations=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations.map(x=>({id:x.id,nodes:x.nodes.map(n=>n.target)}))");assert not violations,violations
  page.goto(args.url+'/?view=plan',wait_until='networkidle');assert '合成' not in page.locator('#experiment-checks').inner_text();assert '합성 입력 검사 통과' in page.locator('#experiment-checks').inner_text()
  page.locator('.sample-method summary').click()
  for s in e['recruitment_scenarios']:
   page.select_option('#baseline',str(s['baseline']));page.select_option('#mde',str(s['mde']));assert f"{s['total_days_upper_bound']}일" in page.locator('#recruitment-scenarios').inner_text()
  page.select_option('#baseline','0.5');page.select_option('#mde','0.03');page.screenshot(path=str(out/f'{args.label}-plan-{width}.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors
  results.append({'width':width,'event_definitions':3,'recruitment_scenarios':18,'status':'pass'});page.close()
 for asset,view,selector in [('ednet_report.json','/external.html','#external-error'),('experiment-readiness.json','/?view=plan','#experiment-checks')]:
  page=b.new_page();pattern='**/data/'+asset;page.route(pattern,lambda route:route.fulfill(status=500));page.goto(args.url+view,wait_until='networkidle')
  assert page.locator(selector).is_visible()
  if asset.startswith('ednet'):assert page.locator('#external-app').is_hidden()
  else:assert '확인할 수 없습니다' in page.locator(selector).inner_text() and page.locator('#app').is_visible()
  page.unroute(pattern);page.locator('#external-retry' if asset.startswith('ednet') else '#experiment-checks button').click()
  page.locator('#external-app:not([hidden])' if asset.startswith('ednet') else '#experiment-checks ul').wait_for();page.close()
 # Semantic check, with checksum updated, must still reject inconsistent group count.
 bad=json.loads(json.dumps(r));bad['primary']['groups'][0]['recorded_nextweek']+=1;body=json.dumps(bad);release=json.loads((ROOT/'web/data/release.json').read_text());release['extensions']['ednet_report.json']=hashlib.sha256(body.encode()).hexdigest()
 page=b.new_page();page.route('**/data/ednet_report.json',lambda route:route.fulfill(body=body));page.route('**/data/release.json',lambda route:route.fulfill(body=json.dumps(release)));page.goto(args.url+'/external.html',wait_until='networkidle');assert page.locator('#external-error').is_visible() and page.locator('#external-app').is_hidden();page.close()
 for fault in ['groups','definitions','negative_people','fraction_people','coupon']:
  bad=json.loads(json.dumps(r))
  if fault=='groups':bad['primary']['groups'][0]['active_days']='2+'
  if fault=='definitions':bad['event_definition_sensitivity'][0]['definition']='submit'
  if fault=='negative_people':bad['payments']['paying_users']=-1
  if fault=='fraction_people':bad['payments']['refunding_users']=0.5
  if fault=='coupon':bad['payments']['coupon_users']=bad['payments']['coupon_events']+1
  body=json.dumps(bad);release['extensions']['ednet_report.json']=hashlib.sha256(body.encode()).hexdigest()
  page=b.new_page();page.route('**/data/ednet_report.json',lambda route:route.fulfill(body=body));page.route('**/data/release.json',lambda route:route.fulfill(body=json.dumps(release)));page.goto(args.url+'/external.html',wait_until='networkidle');assert page.locator('#external-error').is_visible(),fault;page.close()
 b.close()
results.append({'http_failure_retry_and_semantic_corruption':'pass'})
(ROOT/f'reports/extension-browser-{args.label}.json').write_text(json.dumps(results,indent=2)+'\n');print(results)

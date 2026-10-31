"""All public page/state templates: axe, text spacing, keyboard and reflow.
Viewport emulation is not physical-device or actual assistive-technology evidence.
"""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
SPACING='* {line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important} p {margin-bottom:2em!important}'

def practice(page,mode):
 page.select_option('#origin','developer_synthetic');page.fill('#context-notes','Automated accessibility check; not participant evidence.');page.check('#scope-confirm')
 if mode=='ready':return
 def valid():
  for j,(count,sev,status) in enumerate([(787170,'review','open'),(45,'review','open'),(0,'block','clear')]):
   if page.input_value(f'#count-{j}')=='':page.fill(f'#count-{j}',str(count));page.select_option(f'#severity-{j}',sev);page.select_option(f'#status-{j}',status)
   page.check(f'#reviewed-{j}')
 for i in range(8):
  page.click('#start')
  if i==0 and mode=='active-a':return
  if i==0 and mode=='invalid':page.click('#finish');return
  if i==1 and mode=='active-b':return
  if i==2 and mode=='paused':page.click('#pause');return
  valid();page.click('#finish')
  if i==0 and mode=='valid':return
  if i<7:page.click('#next')


def inventory():
 cases=[]
 for rule in ['event_exact_repeat','event_daily_key_repeat','event_after_withdrawal','registration_missing_date','event_unknown_site']:
  for tab in ['evidence','impact','decision']:
   cases.append((f'review-{rule}-{tab}',f'/?view=review&detail=1&rule={rule}&tab={tab}','#app',None))
 for view in ['review','analysis','runs','plan','lab']:cases.append((view,'/?view='+view,'#app',None))
 cases += [('review-empty','/?view=review','#app',lambda p:p.fill('#rule-search','no-such-rule')),
  ('analysis-table','/?view=analysis','#app',lambda p:p.click('#show-table')),
  ('analysis-BBB','/?view=analysis&cohort=BBB%7C2014J','#app',None),
  ('analysis-empty','/?view=analysis','#app',lambda p:p.fill('#cohort-search','no-such-cohort')),
  ('analysis-methods','/?view=analysis','#app',lambda p:p.locator('details').evaluate_all('(es)=>es.forEach(e=>e.open=true)')),
  ('plan-details','/?view=plan','#app',lambda p:p.locator('details').evaluate_all('(es)=>es.forEach(e=>e.open=true)')),
  ('runs-details','/?view=runs','#app',lambda p:p.locator('details').evaluate_all('(es)=>es.forEach(e=>e.open=true)'))]
 for stage in ['truth','observed','clean','late','replay']:cases.append(('lab-'+stage,'/?view=lab&stage='+stage,'#app',lambda p:p.locator('details').evaluate_all('(es)=>es.forEach(e=>e.open=true)')))
 for definition in ['submit','entry','ui']:cases.append(('external-'+definition,'/external.html','#external-app',lambda p,d=definition:p.select_option('#event-definition',d)))
 for phase in ['ready','active-a','active-b','invalid','valid','paused','complete']:cases.append(('practice-'+phase,'/operations-practice.html','#workspace',lambda p,m=phase:practice(p,m)))
 return cases

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8780');ap.add_argument('--axe',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--widths',default='1440,390,320');ap.add_argument('--extra-only',action='store_true');a=ap.parse_args();results=[];keyboard=[]
 data={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'url':a.url,'scope':'All public page/state templates; developer automation, not actual screen-reader audio or WCAG certification','axe_version':'4.11.0','results':results,'keyboard':keyboard,'status':'running','assets_sha256':{str(p.relative_to(ROOT/'web')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'web').rglob('*')) if p.is_file()}}
 try:
  with sync_playwright() as pw:
   b=pw.chromium.launch(args=browser_args());data['browser']='Chromium '+b.version
   def scan(page,name,width):
    page.add_script_tag(path=str(a.axe));r=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}})")
    before=page.evaluate('({page:document.documentElement.scrollWidth,viewport:innerWidth})');page.add_style_tag(content=SPACING);after=page.evaluate('({page:document.documentElement.scrollWidth,viewport:innerWidth})')
    results.append({'state':name,'width':width,'violations':[{'id':v['id'],'impact':v['impact'],'nodes':[n['target'] for n in v['nodes']]} for v in r['violations']],'incomplete':[{'id':v['id'],'nodes':[n['target'] for n in v['nodes']]} for v in r['incomplete']],'passed_rules':len(r['passes']),'normal_geometry':before,'text_spacing_geometry':after})
    if width==320 and name in ['plan-details','external-ui','practice-invalid']:
     path=ROOT/'work'/('a11y-spacing-'+name+'.png');page.screenshot(path=str(path),full_page=True)
   for width in map(int,a.widths.split(',')):
    for name,path,ready,action in ([] if a.extra_only else inventory()):
     page=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');page.set_default_timeout(10000);page.goto(a.url+path,wait_until='networkidle');page.locator(ready).wait_for(state='visible')
     if action:action(page)
     scan(page,name,width);page.close()
    for name,path,file,selector in [('main-http','/','report.json','#error'),('external-http','/external.html','ednet_report.json','#external-error'),('practice-http','/operations-practice.html','report.json','#load-error'),('plan-http','/?view=plan','experiment-readiness.json','#experiment-checks button')]:
     page=b.new_page(viewport={'width':width,'height':900});page.route('**/data/'+file,lambda r:r.fulfill(status=500));page.goto(a.url+path,wait_until='networkidle');page.locator(selector).wait_for(state='visible');scan(page,name,width);page.close()
    for name,path,asset,loading in [('main','/','report.json','#loading'),('external','/external.html','ednet_report.json','#external-loading'),('practice','/operations-practice.html','report.json','#loading'),('plan','/?view=plan','experiment-readiness.json','#experiment-checks')]:
     page=b.new_page(viewport={'width':width,'height':900});held=[];page.route('**/data/'+asset,lambda route:held.append(route));page.goto(a.url+path,wait_until='domcontentloaded');page.locator(loading).wait_for(state='visible');scan(page,name+'-loading',width)
     for route in held:route.abort()
     page.close()
    bad_cases=[('main-bad-json','/','report.json','#error','{bad'),('external-bad-json','/external.html','ednet_report.json','#external-error','{bad'),('practice-bad-json','/operations-practice.html','report.json','#load-error','{bad'),('plan-bad-json','/?view=plan','experiment-readiness.json','#experiment-checks button','{bad')]
    for gate in ['BLOCK','UNKNOWN']:
     raw=json.loads((ROOT/'reports/report.json').read_text());raw['quality']['gate']=gate;bad_cases.append(('main-'+gate,'/','report.json','#error',json.dumps(raw)))
    for name,path,asset,error,body in bad_cases:
     page=b.new_page(viewport={'width':width,'height':900});page.route('**/data/'+asset,lambda route,request,data=body:route.fulfill(status=200,body=data,content_type='application/json'));page.goto(a.url+path,wait_until='networkidle');page.locator(error).wait_for(state='visible');scan(page,name,width);page.close()
    print(json.dumps({'width_completed':width,'states_so_far':len(results)}),flush=True)
   # Every existing rule/tab and scope is exercised even when its HTML shares a template.
   page=b.new_page(viewport={'width':1440,'height':900});page.goto(a.url+'/?view=review');page.locator('#app').wait_for(state='visible');page.select_option('#rule-filter','all')
   ids=page.locator('[data-rule]').evaluate_all('(es)=>es.map(e=>e.dataset.rule)')
   for rule in ids:
    page.locator(f'[data-rule="{rule}"]').focus();page.keyboard.press('Enter');assert page.evaluate('document.activeElement.id')=='detail-title'
    page.locator('#tab-evidence').focus()
    for key,tab in [('End','decision'),('Home','evidence'),('ArrowRight','impact')]:
     page.keyboard.press(key);assert page.locator('#tab-'+tab).get_attribute('aria-selected')=='true';assert page.locator('#detail-content').inner_text().strip()
   keyboard.append({'task':'20 rules x detail tabs keyboard navigation','rules':len(ids),'status':'pass'})
   for route,ready in [('/?view=analysis','#app'),('/external.html','#external-app'),('/operations-practice.html','#workspace')]:
    page.goto(a.url+route);page.locator(ready).wait_for(state='visible');page.keyboard.press('Tab');assert page.evaluate('document.activeElement.classList.contains("skip")');page.keyboard.press('Enter');assert page.evaluate('document.activeElement.id')=='main'
   keyboard.append({'task':'skip link across 3 page shells','status':'pass'})
   page.goto(a.url+'/?view=analysis');page.locator('#app').wait_for(state='visible')
   options=page.locator('#cohort option').evaluate_all('(es)=>es.map(e=>e.value)')
   for opt in options:page.select_option('#cohort',opt);assert '분모' in page.locator('#return-definition').inner_text()
   page.select_option('#cohort','all');page.locator('#show-table').focus();page.keyboard.press('Enter');assert page.locator('#day-table-wrap').is_visible();page.keyboard.press('Tab');assert page.evaluate('document.activeElement.id')=='day-table-wrap'
   keyboard.append({'task':'23 cohort render contracts, chart-to-table keyboard access','scopes':len(options),'status':'pass'})
   page.close();b.close()
  data['status']='pass' if all(not r['violations'] and all(r[g]['page']<=r[g]['viewport'] for g in ['normal_geometry','text_spacing_geometry']) for r in results) else 'fail'
 except Exception as exc:data['status']='error';data['error']=str(exc);raise
 finally:
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':data['status'],'states':len(results),'problems':[r for r in results if r['violations'] or any(r[g]['page']>r[g]['viewport'] for g in ['normal_geometry','text_spacing_geometry'])]},ensure_ascii=False))
 assert data['status']=='pass'
if __name__=='__main__':main()

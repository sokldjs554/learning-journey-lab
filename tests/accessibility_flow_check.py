"""Keyboard/focus regressions, developer-driven; not actual screen-reader audio."""
import argparse,json,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from browser_support import browser_args

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8780');ap.add_argument('--baseline-ref',help='Local commit SHA for an explicit before-fix diagnostic');ap.add_argument('--output',type=Path,default=Path('work/accessibility-flows.json'));args=ap.parse_args();rows=[]
 with sync_playwright() as p:
  b=p.chromium.launch(args=browser_args())
  for path,asset,error,retry,ready,target in [('/','report.json','#error','#retry','#app','page-title'),('/external.html','ednet_report.json','#external-error','#external-retry','#external-app','external-title'),('/?view=plan','experiment-readiness.json','#experiment-checks','#experiment-checks button','#experiment-checks','experiment-checks')]:
   page=b.new_page();
   if args.baseline_ref:
    for name in ['app.js','external.js','experiment-view.js']:
     content=subprocess.check_output(['git','show',args.baseline_ref+':web/'+name],text=True)
     page.route('**/'+name,lambda route,request,body=content:route.fulfill(status=200,body=body,content_type='text/javascript'))
   pattern='**/data/'+asset;page.route(pattern,lambda route:route.fulfill(status=500));page.goto(args.url+path,wait_until='networkidle');page.locator(retry).wait_for(state='visible');failed=None
   if not args.baseline_ref:
    page.locator(retry).focus()
    with page.expect_response(pattern) as response:page.keyboard.press('Enter')
    expect(page.locator(retry)).to_be_focused();failed=True
   page.unroute(pattern);page.locator(retry).focus();page.keyboard.press('Enter');page.locator(ready).wait_for(state='visible')
   if 'experiment' in asset:page.wait_for_function("document.querySelector('#recruitment-scenarios table') !== null")
   focus=page.evaluate('document.activeElement.id');rows.append({'task':'retry_focus','path':path,'target':target,'focus':focus,'failure_retry_focus':failed,'pass':focus==target and (args.baseline_ref or failed is True)});page.close()
  for path,ready,selector in [('/?view=review','#app','#rule-search'),('/external.html','#external-app','#event-definition'),('/operations-practice.html','#workspace','#context-notes')]:
   page=b.new_page();page.goto(args.url+path);page.locator(ready).wait_for(state='visible')
   colors=page.locator(selector).evaluate('(e)=>({border:getComputedStyle(e).borderTopColor,background:getComputedStyle(e).backgroundColor})')
   def luminance(color):
    rgb=[float(x)/255 for x in color[color.index('(')+1:color.index(')')].split(',')[:3]]
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    return sum(x*y for x,y in zip(linear,[.2126,.7152,.0722]))
   values=[luminance(colors[k]) for k in ['border','background']];ratio=(max(values)+.05)/(min(values)+.05)
   rows.append({'task':'input boundary contrast','path':path,'selector':selector,'colors':colors,'ratio':ratio,'pass':ratio>=3});page.close()
  page=b.new_page();page.goto(args.url+'/?view=review&detail=1');page.locator('#app').wait_for(state='visible');page.locator('#tab-evidence').focus();page.keyboard.press('Tab')
  focused=page.evaluate('({id:document.activeElement.id,outline:getComputedStyle(document.activeElement).outlineStyle,width:getComputedStyle(document.activeElement).outlineWidth})')
  rows.append({'task':'detail panel visible keyboard focus','observed':focused,'pass':focused['id']=='detail-content' and focused['outline']!='none' and focused['width']!='0px'});page.close()
  page=b.new_page();page.goto(args.url+'/?view=lab');page.locator('#app').wait_for(state='visible');page.locator('details').evaluate_all('(es)=>es.forEach(e=>e.open=true)')
  regions=page.get_by_role('region',name='생성 로그 검증 SQL',exact=True).count();rows.append({'task':'named focusable SQL regions','count':regions,'pass':regions==6});page.close()
  b.close()
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps({'human_observation':False,'results':rows},ensure_ascii=False,indent=2)+'\n');print(json.dumps(rows,ensure_ascii=False));assert all(x['pass'] for x in rows),rows
if __name__=='__main__':main()

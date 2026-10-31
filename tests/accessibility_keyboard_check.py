"""Developer keyboard traversal, not actual VoiceOver/Safari evidence."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8780');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=[]
 with sync_playwright() as p:
  b=p.chromium.launch(args=browser_args())
  for width in [1440,320]:
   for path,ready,expanded in [(path,ready,expanded) for path,ready in [('/?view=review','#app'),('/?view=review&detail=1','#app'),('/?view=analysis','#app'),('/?view=runs','#app'),('/?view=plan','#app'),('/?view=lab','#app'),('/external.html','#external-app'),('/operations-practice.html','#workspace')] for expanded in (False,True)]:
    page=b.new_page(viewport={'width':width,'height':900});page.goto(a.url+path,wait_until='networkidle');page.locator(ready).wait_for(state='visible')
    if expanded:page.locator('details').evaluate_all('(es)=>es.forEach(e=>e.open=true)')
    expected=page.evaluate('''()=>[...document.querySelectorAll('a[href],button,input,select,textarea,summary,[tabindex]')].filter(e=>e.tabIndex>=0&&!e.matches(':disabled')&&(!e.closest('details:not([open])')||e.closest('details:not([open])').querySelector('summary').contains(e))&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden').map((e,i)=>{e.dataset.auditTab=String(i);return {id:String(i),tag:e.tagName,label:(e.getAttribute('aria-label')||e.innerText||e.id).slice(0,100)}})''')
    seen=[];invisible=[];unoutlined=[]
    for _ in range(len(expected)+5):
     page.keyboard.press('Tab')
     state=page.evaluate('''()=>{const e=document.activeElement,r=e.getBoundingClientRect(),s=getComputedStyle(e);return {id:e.dataset.auditTab,tag:e.tagName,outline:s.outlineStyle,shadow:s.boxShadow,rect:{x:r.x,y:r.y,width:r.width,height:r.height},intersects:r.bottom>0&&r.right>0&&r.top<innerHeight&&r.left<innerWidth}}''')
     if state.get('id') is None:continue
     if state['id'] in seen:break
     seen.append(state['id'])
     if not state['intersects']:invisible.append(state)
     if state['outline']=='none' and state['shadow']=='none':unoutlined.append(state)
    missing=[e for e in expected if e['id'] not in seen]
    out.append({'path':path,'expanded_details':expanded,'width':width,'expected_controls':len(expected),'reached':len(seen),'missing':missing,'offscreen':invisible,'no_indicator':unoutlined});page.close()
  b.close()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'source':'developer keyboard automation','results':out},ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False));assert not any(x['missing'] or x['offscreen'] or x['no_indicator'] for x in out)
if __name__=='__main__':main()

"""Axe every task view, detail states and error view, plus mobile overflow."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8766');ap.add_argument('--axe',type=Path,default=ROOT/'work/a11y/node_modules/axe-core/axe.min.js');ap.add_argument('--label',default='local');a=ap.parse_args();results=[]
    with sync_playwright() as p:
        b=p.chromium.launch(args=browser_args())
        for width in [1440,390,320]:
            for query in ['view=review','view=review&detail=1','view=review&detail=1&tab=impact','view=review&detail=1&tab=decision','view=analysis','view=runs','view=plan','view=lab','error']:
                page=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce')
                if query=='error':page.route('**/data/report.json',lambda route:route.fulfill(status=500))
                page.goto(a.url+'?'+query,wait_until='networkidle')
                page.locator('#error:not([hidden])' if query=='error' else '#app:not([hidden])').wait_for()
                page.add_script_tag(path=str(a.axe));r=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})")
                results.append({'width':width,'view':query,'violations':[{'id':v['id'],'impact':v['impact'],'nodes':[n['target'] for n in v['nodes']]} for v in r['violations']], 'incomplete_checks':len(r['incomplete']),'incomplete_details':[{'id':v['id'],'nodes':[n['target'] for n in v['nodes']]} for v in r['incomplete']],'passed_rules':len(r['passes'])})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,query)
                page.close()
        b.close()
    (ROOT/f'reports/accessibility-{a.label}.json').write_text(json.dumps({'engine':'axe-core 4.11.0 + Chromium','scope':'27 viewport/view combinations; automated A/AA only, not full accessibility certification','results':results},indent=2)+'\n')
    print(json.dumps([{'width':r['width'],'view':r['view'],'violations':r['violations'],'incomplete':r['incomplete_checks']} for r in results]));assert not any(r['violations'] for r in results)
if __name__=='__main__':main()

"""Requires npm install --prefix work/a11y axe-core@4.11.0 (or --axe path)."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8765');ap.add_argument('--axe',type=Path,default=ROOT/'work/a11y/node_modules/axe-core/axe.min.js');ap.add_argument('--label',default='local');a=ap.parse_args()
    results=[]
    with sync_playwright() as p:
        b=p.chromium.launch(args=['--no-sandbox'])
        for width in [1440,390,320]:
            page=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce')
            page.goto(a.url,wait_until='networkidle');page.locator('#app:not([hidden])').wait_for()
            page.add_script_tag(path=str(a.axe))
            r=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})")
            results.append({'width':width,'violations':[{'id':v['id'],'impact':v['impact'],'nodes':[n['target'] for n in v['nodes']]} for v in r['violations']], 'incomplete_checks':len(r['incomplete']), 'incomplete_details':[{'id':v['id'],'nodes':[n['target'] for n in v['nodes']]} for v in r['incomplete']], 'passed_rules':len(r['passes'])})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.close()
        b.close()
    (ROOT/f'reports/accessibility-{a.label}.json').write_text(json.dumps({'engine':'axe-core 4.11.0 + Chromium','scope':'automated WCAG A/AA checks; not full accessibility certification','results':results},indent=2)+'\n')
    print(json.dumps(results));assert not any(r['violations'] for r in results)
if __name__=='__main__':main()

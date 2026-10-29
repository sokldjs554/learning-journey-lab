"""Guard against denominator/source confusion in the guided reading path."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--url',default='http://127.0.0.1:8767');a.add_argument('--label',default='local');args=a.parse_args()
r=json.loads((ROOT/'reports/report.json').read_text());results=[]
with sync_playwright() as p:
 b=p.chromium.launch(args=browser_args())
 for width in [1440,390]:
  page=b.new_page(viewport={'width':width,'height':900});page.goto(args.url+'?view=analysis',wait_until='networkidle')
  for c in [r['overall'],*r['cohorts']]:
   value='all' if 'module' not in c else c['module']+'|'+c['term'];page.select_option('#cohort',value)
   text=page.locator('#return-definition').inner_text(timeout=1500)
   assert f"분자 {c['w2_returned']:,}" in text and f"분모 {c['w1_active']:,}" in text
   assert '첫 주 활성' in text
   assert '%p' in page.locator('#content-reading').inner_text()
  page.select_option('#cohort','all');text=page.locator('#counterevidence').inner_text();assert '9개' in text and '8개' in text
  page.goto(args.url+'?view=review&detail=1&tab=impact',wait_until='networkidle')
  assert '14,637 − 14,268 = 369' in page.locator('#policy-meaning').inner_text(timeout=1500)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  results.append({'width':width,'scope_formulas_checked':23,'status':'pass'});page.close()
 b.close()
(ROOT/f'reports/reading-{args.label}.json').write_text(json.dumps(results,indent=2)+'\n');print(results)

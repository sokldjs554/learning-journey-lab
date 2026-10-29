"""Browser-level semantic contract checks using controlled HTTP response bodies."""
import argparse,json,copy
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8765');ap.add_argument('--baseline-js',type=Path);a=ap.parse_args()
    base=json.loads((ROOT/'reports/report.json').read_text()); cases=[]
    for label,mutate in [
      ('invalid_rate',lambda r:r['overall'].update(return_rate='invalid')),
      ('wrong_fraction',lambda r:r['overall'].update(w2_returned=1)),
      ('wrong_provenance',lambda r:r.update(source_type='synthetic')),
      ('blocked',lambda r:r['quality'].update(gate='BLOCK')),
      ('empty_cohorts',lambda r:r.update(cohorts=[]))]:
        payload=copy.deepcopy(base);mutate(payload);cases.append((label,payload,False))
    payload=copy.deepcopy(base);payload['temporal'][0]['repeat_comparison']['ci']=None
    cases.append(('unavailable_interval',payload,True))
    results=[]
    with sync_playwright() as p:
        b=p.chromium.launch(args=browser_args())
        for label,payload,visible in cases:
            page=b.new_page();page.route('**/data/report.json',lambda route,request,payload=payload:route.fulfill(status=200,content_type='application/json',body=json.dumps(payload)))
            if a.baseline_js:page.route('**/app.js',lambda route:route.fulfill(status=200,content_type='application/javascript',body=a.baseline_js.read_text()))
            page.goto(a.url,wait_until='networkidle')
            ok=page.locator('#app').is_visible()==visible
            if not visible:ok=ok and page.locator('#error').is_visible()
            results.append({'case':label,'passed':ok});page.close()
        b.close()
    (ROOT/'reports/report-contract.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results));assert all(r['passed'] for r in results)
if __name__=='__main__':main()

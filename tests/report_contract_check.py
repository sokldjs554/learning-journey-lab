"""Browser-level semantic contract checks using controlled HTTP response bodies."""
import argparse,json,copy,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8766');ap.add_argument('--baseline-js',type=Path);a=ap.parse_args()
    base=json.loads((ROOT/'reports/report.json').read_text()); cases=[]
    for label,mutate in [
      ('invalid_rate',lambda r:r['overall'].update(return_rate='invalid')),
      ('wrong_fraction',lambda r:r['overall'].update(w2_returned=1)),
      ('wrong_provenance',lambda r:r.update(source_type='synthetic')),
      ('blocked',lambda r:r['quality'].update(gate='BLOCK')),
      ('empty_cohorts',lambda r:r.update(cohorts=[])),
      ('not_run',lambda r:r['quality'].update(gate='NOT_RUN'))]:
        payload=copy.deepcopy(base);mutate(payload);cases.append((label,payload,False))
    payload=copy.deepcopy(base);payload['temporal'][0]['repeat_comparison']['ci']=None
    cases.append(('unavailable_interval',payload,True))
    operations=json.loads((ROOT/'web/data/operations.json').read_text())
    op_cases=[]
    for label,mutate in [
      ('stale_issue_count',lambda o:o['rules'][0].update(count=123)),
      ('wrong_sql_source',lambda o:o['rules'][0].update(sql_file='sql/quality.sql')),
      ('stale_snapshot',lambda o:o.update(snapshot_id='a'*64)),
      ('duplicate_issue',lambda o:o['rules'].append(o['rules'][0])),
      ('wrong_benchmark_hash',lambda o:o['benchmark']['runs'][0].update(report_sha256='a'*64))]:
        payload=copy.deepcopy(operations);mutate(payload);op_cases.append((label,payload))
    results=[]
    with sync_playwright() as p:
        b=p.chromium.launch(args=browser_args())
        for label,payload,visible in cases:
            page=b.new_page();body=json.dumps(payload)
            matched=copy.deepcopy(operations);digest=hashlib.sha256(body.encode()).hexdigest();matched['report_sha256']=digest
            for run in matched['benchmark']['runs']:run['report_sha256']=digest
            page.route('**/data/report.json',lambda route,request,body=body:route.fulfill(status=200,content_type='application/json',body=body))
            page.route('**/data/operations.json',lambda route,request,matched=matched:route.fulfill(status=200,content_type='application/json',body=json.dumps(matched)))
            if a.baseline_js:page.route('**/app.js',lambda route:route.fulfill(status=200,content_type='application/javascript',body=a.baseline_js.read_text()))
            page.goto(a.url,wait_until='networkidle')
            ok=page.locator('#app').is_visible()==visible
            if not visible:
                ok=ok and page.locator('#error').is_visible()
                if label=='blocked':ok=ok and '분석 공개 보류' in page.locator('#error').inner_text()
                if label=='not_run':ok=ok and '검증 상태 미확인' in page.locator('#error').inner_text()
            results.append({'case':label,'passed':ok});page.close()
        for label,payload in op_cases:
            page=b.new_page();page.route('**/data/operations.json',lambda route,request,payload=payload:route.fulfill(status=200,content_type='application/json',body=json.dumps(payload)))
            page.goto(a.url,wait_until='networkidle')
            results.append({'case':label,'passed':page.locator('#app').is_hidden() and page.locator('#error').is_visible()});page.close()
        b.close()
    (ROOT/'reports/report-contract.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results));assert all(r['passed'] for r in results)
if __name__=='__main__':main()

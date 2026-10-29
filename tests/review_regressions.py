"""Independent reviewer reproductions: actual-byte binding, scope, focus and 0/0."""
import argparse,copy,hashlib,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:8766');ap.add_argument('--label',default='local');a=ap.parse_args()
    report=json.loads((ROOT/'reports/report.json').read_text());ops=json.loads((ROOT/'web/data/operations.json').read_text());results=[]
    with sync_playwright() as p:
        b=p.chromium.launch(args=browser_args())
        page=b.new_page();tampered=copy.deepcopy(report);tampered['click_sensitivity'][0]['raw_vs_exact_changed']=12345
        page.route('**/data/report.json',lambda route:route.fulfill(content_type='application/json',body=json.dumps(tampered)))
        page.goto(a.url,wait_until='networkidle');results.append({'case':'report_bytes_bound_to_benchmark','passed':page.locator('#app').is_hidden() and page.locator('#error').is_visible()});page.close()
        page=b.new_page(viewport={'width':390,'height':844});page.goto(a.url,wait_until='networkidle')
        page.locator('[data-rule="event_after_withdrawal"]').click();page.go_back(wait_until='networkidle')
        results.append({'case':'mobile_history_focus','passed':page.locator(':focus').get_attribute('data-rule')=='event_after_withdrawal'});page.close()
        page=b.new_page();page.goto(a.url+'?view=analysis&cohort=AAA.2014J',wait_until='networkidle');page.locator('#view-analysis > details.method summary').click()
        results.append({'case':'no_global_exclusions_in_scoped_view','passed':page.locator('#exclusions').is_hidden()});page.close()
        changed=copy.deepcopy(report);changed['strict_sensitivity'].update(w1_active=0,w2_returned=0)
        body=json.dumps(changed);matched=copy.deepcopy(ops);h=hashlib.sha256(body.encode()).hexdigest();matched['report_sha256']=h
        for run in matched['benchmark']['runs']:run['report_sha256']=h
        page=b.new_page();page.route('**/data/report.json',lambda route:route.fulfill(content_type='application/json',body=body));page.route('**/data/operations.json',lambda route:route.fulfill(content_type='application/json',body=json.dumps(matched)))
        page.goto(a.url+'?view=review&rule=event_after_withdrawal&tab=impact&detail=1',wait_until='networkidle')
        content=page.locator('#detail-content').inner_text();results.append({'case':'empty_strict_denominator','passed':page.locator('#app').is_visible() and 'NaN' not in content and '비교 불가' in content});page.close()
        b.close()
    (ROOT/f'reports/review-regressions-{a.label}.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results));assert all(x['passed'] for x in results)
if __name__=='__main__':main()

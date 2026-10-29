"""Capture actual analysis views for the evidence index; no mock data."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import browser_args
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--label',required=True);args=p.parse_args()
with sync_playwright() as pw:
    browser=pw.chromium.launch(args=browser_args())
    page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    for scope,name in [('all','overall'),('BBB|2014J','counter')]:
        page.goto(args.url+'/?view=analysis',wait_until='networkidle')
        page.locator('#app:not([hidden])').wait_for()
        page.select_option('#cohort',scope)
        if scope=='all':
            assert '분자 20,303' in page.locator('#return-definition').inner_text()
            assert '9개' in page.locator('#counterevidence').inner_text()
        else:assert '-6.6' in page.locator('#content-diff').inner_text()
        page.screenshot(path=str(ROOT/f'reports/screenshots/{args.label}-analysis-{name}.png'),full_page=True)
    browser.close()
print('Captured actual overall and counterexample analysis views.')

"""Consistency checks for the reviewable static snapshot; no network or raw CSV required."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.document import generated_blocks

def main():
    data=(ROOT/'reports/report.json').read_bytes();r=json.loads(data)
    assert data==(ROOT/'web/data/report.json').read_bytes(),'UI data drift'
    h=hashlib.sha256(data).hexdigest()
    assert json.loads((ROOT/'web/data/release.json').read_text())['report_sha256']==h
    b=json.loads((ROOT/'reports/benchmark.json').read_text())
    assert len(b['runs'])==3 and all(run['report_sha256']==h for run in b['runs']),'benchmark is from a different report'
    readme=(ROOT/'README.md').read_text();findings=(ROOT/'reports/findings.md').read_text()
    for i,block in enumerate(generated_blocks(r,b)):
        assert block in readme,'README numbers drift'
        if i==0:assert block in findings,'findings numbers drift'
    assert 'DEMO_URL_PENDING' not in readme,'Demo URL not finalized'
    for c in [r['overall'],*r['cohorts'],*r['temporal']]:
        assert c['w2_returned']<=c['w1_active']<=c['eligible']
        assert c['return_rate']==c['w2_returned']/c['w1_active']
    assert json.loads((ROOT/'reports/crosscheck.json').read_text())['mismatched_rows']==0
    assert sum(c['eligible'] for c in r['cohorts'])==r['overall']['eligible']
    print('Report, UI, README, findings, benchmark and crosscheck are consistent:',h)
if __name__=='__main__':main()

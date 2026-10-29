"""Consistency checks for the reviewable static snapshot; no network or raw CSV required."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.document import generated_blocks
from scripts.build import build_operations
from scripts.evidence_extensions import validate_all,summary_block

def main():
    data=(ROOT/'reports/report.json').read_bytes();r=json.loads(data)
    assert data==(ROOT/'web/data/report.json').read_bytes(),'UI data drift'
    h=hashlib.sha256(data).hexdigest()
    assert json.loads((ROOT/'web/data/release.json').read_text())['report_sha256']==h
    ops=(ROOT/'web/data/operations.json').read_bytes()
    assert json.loads(ops)==build_operations(ROOT,r),'Operating evidence drift'
    assert json.loads((ROOT/'web/data/release.json').read_text())['operations_sha256']==hashlib.sha256(ops).hexdigest()
    validate_all(ROOT)
    release=json.loads((ROOT/'web/data/release.json').read_text())
    for name,digest in release['extensions'].items():
        blob=(ROOT/'reports'/name).read_bytes()
        assert blob==(ROOT/'web/data'/name).read_bytes(),'Supplementary UI data drift'
        assert hashlib.sha256(blob).hexdigest()==digest,'Supplementary hash drift'
    b=json.loads((ROOT/'reports/benchmark.json').read_text())
    assert len(b['runs'])==3 and all(run['report_sha256']==h for run in b['runs']),'benchmark is from a different report'
    readme=(ROOT/'README.md').read_text();findings=(ROOT/'reports/findings.md').read_text()
    for i,block in enumerate(generated_blocks(r,b)):
        assert block in readme,'README numbers drift'
        if i==0:assert block in findings,'findings numbers drift'
    external=summary_block(json.loads((ROOT/'reports/ednet_report.json').read_text()))
    assert external in readme and external in (ROOT/'reports/external-findings.md').read_text(),'Supplementary prose drift'
    assert 'DEMO_URL_PENDING' not in readme,'Demo URL not finalized'
    for c in [r['overall'],*r['cohorts'],*r['temporal']]:
        assert c['w2_returned']<=c['w1_active']<=c['eligible']
        assert c['return_rate']==c['w2_returned']/c['w1_active']
    assert json.loads((ROOT/'reports/crosscheck.json').read_text())['mismatched_rows']==0
    assert sum(c['eligible'] for c in r['cohorts'])==r['overall']['eligible']
    print('Report, UI, README, findings, benchmark and crosscheck are consistent:',h)
if __name__=='__main__':main()

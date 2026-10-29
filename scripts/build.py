"""Validate the evidence contract before publishing static assets. stdlib only."""
from pathlib import Path
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]

def build():
    src=ROOT/'reports/report.json';r=json.loads(src.read_text())
    if r['quality']['gate']=='BLOCK':raise ValueError('Blocking data-quality findings; do not publish')
    if r['source_type']!='public' or r['fault_lab']['source_type']!='synthetic':raise ValueError('Provenance mismatch')
    s=r['overall'];assert sum(d['n'] for d in s['days'])==s['eligible']
    assert sum(d['n'] for d in s['days'] if d['days']>0)==s['w1_active']
    assert sum(d['returned'] for d in s['days'] if d['days']>0)==s['w2_returned']
    assert s['return_rate']==s['w2_returned']/s['w1_active']
    (ROOT/'web/data').mkdir(exist_ok=True)
    shutil.copyfile(src,ROOT/'web/data/report.json')
    release={'report_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_type':'static evidence snapshot'}
    (ROOT/'web/data/release.json').write_text(json.dumps(release,indent=2)+'\n')
    print('Static evidence ready:',release['report_sha256'])
if __name__=='__main__':build()

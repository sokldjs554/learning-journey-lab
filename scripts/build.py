"""Validate the evidence contract before publishing static assets. stdlib only."""
from pathlib import Path
import json,shutil,hashlib,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.evidence_extensions import publish

def build_operations(root, report):
    """Join only matching measured records; resolve SQL locations from actual sources."""
    digest=hashlib.sha256((root/'reports/report.json').read_bytes()).hexdigest()
    snapshot=report['source']['archive_sha256']
    issues=json.loads((root/'reports/issues.json').read_text())
    benchmark=json.loads((root/'reports/benchmark.json').read_text())
    checks={c['rule_id']:c for c in report['quality']['checks']}
    if len(issues)!=len(checks) or {x['rule_id'] for x in issues}!=set(checks):
        raise ValueError('Issue registry does not match report')
    sql_files={name:(root/name).read_text() for name in ['sql/dimensions.sql','sql/quality.sql']}
    locations={}
    for name,source in sql_files.items():
        for match in re.finditer(r"SELECT\s+'([a-z_]+)'",source):
            rule_id=match.group(1)
            if rule_id in locations:raise ValueError('Ambiguous SQL rule location')
            locations[rule_id]=(name,source.count('\n',0,match.start())+1)
    rules=[]
    for issue in issues:
        rule_id=issue['rule_id'];check=checks[rule_id]
        if issue['count']!=check['count'] or issue['severity']!=check['severity']:
            raise ValueError('Stale issue result')
        latest=issue['history'][-1]
        if latest['snapshot']!=snapshot or latest['count']!=issue['count']:
            raise ValueError('Stale issue history')
        if issue['status'] not in ['clear','open','resolved'] or (issue['count']>0)!=(issue['status']=='open'):
            raise ValueError('Inconsistent issue status')
        if rule_id not in locations:raise ValueError('Missing SQL rule')
        file,line=locations[rule_id]
        rules.append({**issue,'sql_file':file,'sql_line':line})
    if not benchmark['runs'] or any(run['report_sha256']!=digest for run in benchmark['runs']):
        raise ValueError('Benchmark report mismatch')
    return {'schema_version':1,'report_sha256':digest,'snapshot_id':snapshot,
            'rules':rules,'sql_files':sql_files,'benchmark':benchmark}

def build():
    src=ROOT/'reports/report.json';r=json.loads(src.read_text())
    if r['quality']['gate']=='BLOCK':raise ValueError('Blocking data-quality findings; do not publish')
    if r['source_type']!='public' or r['fault_lab']['source_type']!='synthetic':raise ValueError('Provenance mismatch')
    s=r['overall'];assert sum(d['n'] for d in s['days'])==s['eligible']
    assert sum(d['n'] for d in s['days'] if d['days']>0)==s['w1_active']
    assert sum(d['returned'] for d in s['days'] if d['days']>0)==s['w2_returned']
    assert s['return_rate']==s['w2_returned']/s['w1_active']
    operations=build_operations(ROOT,r)
    (ROOT/'web/data').mkdir(exist_ok=True)
    shutil.copyfile(src,ROOT/'web/data/report.json')
    ops=ROOT/'web/data/operations.json'
    ops.write_text(json.dumps(operations,ensure_ascii=False,indent=2)+'\n')
    release={'report_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
             'operations_sha256':hashlib.sha256(ops.read_bytes()).hexdigest(),
             'source_type':'static evidence snapshot','extensions':publish(ROOT)}
    (ROOT/'web/data/release.json').write_text(json.dumps(release,indent=2)+'\n')
    print('Static evidence ready:',release['report_sha256'])
if __name__=='__main__':build()

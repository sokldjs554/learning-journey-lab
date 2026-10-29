"""The static operating record must not combine stale or misdirected evidence."""
import json,shutil
from pathlib import Path
import pytest
from scripts import build
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def evidence(tmp_path):
    for folder in ['reports','sql']:
        (tmp_path/folder).mkdir()
    for name in ['report.json','issues.json','benchmark.json']:
        shutil.copyfile(ROOT/'reports'/name,tmp_path/'reports'/name)
    for name in ['quality.sql','dimensions.sql']:
        shutil.copyfile(ROOT/'sql'/name,tmp_path/'sql'/name)
    return tmp_path,json.loads((tmp_path/'reports/report.json').read_text())
def operation(root,r):
    assert hasattr(build,'build_operations'),'Missing operating evidence export'
    return build.build_operations(root,r)
def test_rules_resolve_actual_sql_and_issue_history(evidence):
    root,r=evidence;o=operation(root,r)
    assert len(o['rules'])==20
    dims={'registration_required_null','site_required_null','course_required_null','course_invalid_length','registration_unknown_course','site_unknown_course'}
    assert {x['rule_id'] for x in o['rules'] if x['sql_file']=='sql/dimensions.sql'}==dims
    for rule in o['rules']:
        assert rule['rule_id'] in o['sql_files'][rule['sql_file']].splitlines()[rule['sql_line']-1]
        assert rule['history'][-1]['count']==rule['count']
    assert o['snapshot_id']==r['source']['archive_sha256']
    assert operation(root,r)==o
@pytest.mark.parametrize('damage',['count','snapshot','duplicate','benchmark'])
def test_rejects_incoherent_operating_evidence(evidence,damage):
    root,r=evidence
    name='benchmark.json' if damage=='benchmark' else 'issues.json'
    p=root/'reports'/name;data=json.loads(p.read_text())
    if damage=='count':data[0]['count']+=1
    if damage=='snapshot':data[0]['history'][-1]['snapshot']='wrong'
    if damage=='duplicate':data.append(data[0])
    if damage=='benchmark':data['runs'][0]['report_sha256']='wrong'
    p.write_text(json.dumps(data))
    assert hasattr(build,'build_operations'),'Missing operating evidence export'
    with pytest.raises(ValueError):build.build_operations(root,r)

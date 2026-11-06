"""Codex-written review of applicant submission; includes a documented integrity defect."""
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

APP=Path(__file__).resolve().parents[1]/'evidence/applicant'
# Contract copied as test expectations, not obtained from update_issues logic.
REVIEWS=('registration_missing_date','event_exact_repeat','event_daily_key_repeat',
         'event_before_registration','event_after_withdrawal','event_after_course')
BLOCKS=('event_unknown_student','event_required_null','event_nonpositive_click','event_unknown_site',
        'registration_inverted_dates','registration_key_repeat','site_key_repeat','course_key_repeat',
        'registration_required_null','site_required_null','course_required_null','course_invalid_length',
        'registration_unknown_course','site_unknown_course')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_run(root,rid,counts=None,manifest='a'*64,pipeline_status=None):
    d=root/rid;d.mkdir(parents=True);counts=counts or {}
    checks=[dict(rule_id=r,severity='review',issue_count=counts.get(r,0)) for r in REVIEWS]
    checks += [dict(rule_id=r,severity='block',issue_count=counts.get(r,0)) for r in BLOCKS]
    gate='BLOCK' if any(counts.get(r,0)>0 for r in BLOCKS) else 'REVIEW' if any(counts.get(r,0)>0 for r in REVIEWS) else 'PASS'
    q=d/'quality.json';q.write_text(json.dumps({'scope':'full_quality_20','gate':gate,'checks':checks}))
    record={'schema_version':1,'run_id':rid,'status':pipeline_status or ('blocked' if gate=='BLOCK' else 'success'),
            'ended_at_utc':'2026-11-06T10:00:00+00:00','inputs':{'manifest_sha256':manifest},
            'steps':[{'name':'quality','status':'blocked' if gate=='BLOCK' else 'success','exit_code':2 if gate=='BLOCK' else 0}],
            'quality_gate':gate,'artifacts':None if gate=='BLOCK' or pipeline_status in ('error','aborted') else {'quality.json':{'path':'quality.json','sha256':digest(q)}}}
    (d/'run_record.json').write_text(json.dumps(record))
    return d


def invoke(run,history):
    inputs=[run/n for n in ('quality.json','run_record.json') if (run/n).is_file()]
    before={p:(digest(p),p.stat().st_mtime_ns) for p in inputs}
    result=subprocess.run([sys.executable,str(APP/'update_issues.py'),'--run-dir',str(run),'--history',str(history)],capture_output=True,text=True,timeout=10)
    assert before=={p:(digest(p),p.stat().st_mtime_ns) for p in inputs}
    return result


def issue(history,rid='registration_missing_date'):
    return next(i for i in json.loads(history.read_text())['issues'] if i['rule_id']==rid)


def test_open_resolved_reopened_counts_and_idempotence(tmp_path):
    h=tmp_path/'history.json'
    for rid,n in [('r1',2),('r2',0),('r3',3),('r4',3),('r5',4)]:
        d=fixture_run(tmp_path,rid,{'registration_missing_date':n})
        result=invoke(d,h);assert result.returncode==0,result.stderr
        before=h.read_bytes(),h.stat().st_mtime_ns
        repeat=invoke(d,h);assert repeat.returncode==0 and 'SKIP' in repeat.stdout
        assert before==(h.read_bytes(),h.stat().st_mtime_ns)
    i=issue(h);assert (i['issue_count'],i['status'],i['first_seen_run_id'],i['last_checked_run_id'])==(4,'open','r1','r5')
    assert [(e['run_id'],e['previous_count'],e['issue_count'],e['status']) for e in i['history']]==[
        ('r1',None,2,'open'),('r2',2,0,'resolved'),('r3',0,3,'open'),('r5',3,4,'open')]
    clear=issue(h,'event_exact_repeat');assert clear['status']=='clear' and clear['first_seen_run_id'] is None
    assert len(clear['history'])==1 and len(json.loads(h.read_text())['processed_runs'])==5


@pytest.mark.parametrize('status',['error','aborted'])
def test_valid_quality_before_later_failure_is_usable(tmp_path,status):
    d=fixture_run(tmp_path,'run',{'registration_missing_date':2},pipeline_status=status)
    h=tmp_path/'history.json';r=invoke(d,h)
    assert r.returncode==0,r.stderr
    assert issue(h)['status']=='open'


def test_block_result_can_be_recorded_without_final_artifacts(tmp_path):
    d=fixture_run(tmp_path,'blocked',{'event_unknown_student':1})
    h=tmp_path/'history.json';r=invoke(d,h);assert r.returncode==0,r.stderr
    assert issue(h,'event_unknown_student')['status']=='open'
    assert json.loads(h.read_text())['processed_runs'][0]['gate']=='BLOCK'


@pytest.mark.parametrize('case',['running','quality_error','quality_pending','exit_mismatch','missing_quality','invalid_json',
 'missing_rule','duplicate_rule','bad_severity','negative_count','boolean_count','gate_mismatch','record_gate',
 'missing_manifest','different_manifest','missing_end','duplicate_stage','duplicate_json_key','nan'])
def test_invalid_input_never_resolves_existing_issue(tmp_path,case):
    h=tmp_path/'history.json';first=fixture_run(tmp_path,'first',{'registration_missing_date':2})
    assert invoke(first,h).returncode==0
    d=fixture_run(tmp_path,'next');rp=d/'run_record.json';qp=d/'quality.json'
    record=json.loads(rp.read_text());quality=json.loads(qp.read_text())
    if case=='running':record['status']='running'
    elif case=='quality_error':record['steps'][0].update(status='error',exit_code=1)
    elif case=='quality_pending':record['steps'][0].update(status='pending',exit_code=None)
    elif case=='exit_mismatch':record['steps'][0]['exit_code']=2
    elif case=='missing_rule':quality['checks'].pop()
    elif case=='duplicate_rule':quality['checks'][1]=quality['checks'][0]
    elif case=='bad_severity':quality['checks'][0]['severity']='block'
    elif case=='negative_count':quality['checks'][0]['issue_count']=-1
    elif case=='boolean_count':quality['checks'][0]['issue_count']=False
    elif case=='gate_mismatch':quality['gate']='REVIEW'
    elif case=='record_gate':record['quality_gate']='REVIEW'
    elif case=='missing_manifest':record['inputs']={}
    elif case=='different_manifest':record['inputs']['manifest_sha256']='b'*64
    elif case=='missing_end':record['ended_at_utc']=None
    elif case=='duplicate_stage':record['steps']*=2
    qp.write_text(json.dumps(quality));rp.write_text(json.dumps(record))
    if case=='missing_quality':qp.unlink()
    elif case=='invalid_json':qp.write_text('{broken')
    elif case=='duplicate_json_key':qp.write_text('{"scope":"full_quality_20","scope":"full_quality_20"}')
    elif case=='nan':qp.write_text('{"v":NaN}')
    before=h.read_bytes(),h.stat().st_mtime_ns
    r=invoke(d,h);assert r.returncode==1,r.stdout
    assert before==(h.read_bytes(),h.stat().st_mtime_ns)
    assert issue(h)['status']=='open'


def test_same_run_id_different_quality_is_rejected(tmp_path):
    h=tmp_path/'history.json';d=fixture_run(tmp_path,'same',{'registration_missing_date':2})
    assert invoke(d,h).returncode==0
    q=d/'quality.json';s=q.read_text();q.write_text(s+' ')
    before=h.read_bytes(),h.stat().st_mtime_ns
    r=invoke(d,h);assert r.returncode==1
    assert before==(h.read_bytes(),h.stat().st_mtime_ns)


@pytest.mark.parametrize('case',['bad_json','empty_runs','missing_runs','missing_rule','bad_count','missing_first'])
def test_malformed_existing_history_is_not_replaced(tmp_path,case):
    h=tmp_path/'history.json';d=fixture_run(tmp_path,'r1',{'registration_missing_date':2})
    assert invoke(d,h).returncode==0
    history=json.loads(h.read_text())
    if case=='empty_runs':history['processed_runs']=[]
    elif case=='missing_runs':history.pop('processed_runs')
    elif case=='missing_rule':history['issues'].pop()
    elif case=='bad_count':history['issues'][0]['issue_count']=-1
    elif case=='missing_first':history['issues'][0]['first_seen_run_id']=None
    h.write_text('{bad' if case=='bad_json' else json.dumps(history))
    next_run=fixture_run(tmp_path,'r2');before=h.read_bytes(),h.stat().st_mtime_ns
    r=invoke(next_run,h);assert r.returncode==1
    assert before==(h.read_bytes(),h.stat().st_mtime_ns)


@pytest.mark.parametrize('target',['run_record.json','quality.json','symlink'])
def test_output_collision_rejected(tmp_path,target):
    d=fixture_run(tmp_path,'r');h=d/target
    if target=='symlink':h.symlink_to(d/'quality.json')
    r=invoke(d,h);assert r.returncode==1


def test_atomic_failure_keeps_old_history(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(APP));module=importlib.import_module('update_issues')
    h=tmp_path/'history.json';h.write_text('{"old":true}')
    def fail(*args):raise OSError('controlled replace failure')
    monkeypatch.setattr(module.os,'replace',fail)
    with pytest.raises(OSError):module.save_atomic(h,{'new':True})
    assert h.read_text()=='{"old":true}' and not list(tmp_path.glob('.issue_history-*.tmp'))


@pytest.mark.xfail(strict=True, reason="Open submission defect: recorded quality artifact hash is not checked; see docs/applicant-issue-history.md")
def test_recorded_quality_hash_mismatch_must_not_resolve(tmp_path):
    h=tmp_path/'history.json';d=fixture_run(tmp_path,'r1',{'registration_missing_date':2,'event_exact_repeat':1})
    assert invoke(d,h).returncode==0
    next_run=fixture_run(tmp_path,'r2',{'registration_missing_date':2,'event_exact_repeat':1})
    q=next_run/'quality.json';quality=json.loads(q.read_text())
    quality['checks'][0]['issue_count']=0;q.write_text(json.dumps(quality))
    # REVIEW gate stays unchanged, but recorded artifact hash proves this is a changed file.
    expected=json.loads((next_run/'run_record.json').read_text())['artifacts']['quality.json']['sha256']
    assert expected!=digest(q)
    before=h.read_bytes(),h.stat().st_mtime_ns
    result=invoke(next_run,h)
    assert result.returncode==1, 'Changed quality artifact was accepted and existing issue resolved'
    assert before==(h.read_bytes(),h.stat().st_mtime_ns)
    assert issue(h)['status']=='open'

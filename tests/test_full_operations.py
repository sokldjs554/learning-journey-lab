"""Developer synthetic fixtures, never human comparison observations."""
import importlib
import importlib.util
import json
from pathlib import Path
import pytest


def module():
    assert importlib.util.find_spec('scripts.full_operations') is not None, 'full operations CLI is missing'
    return importlib.import_module('scripts.full_operations')


def test_review_rejects_wrong_nan_and_boolean_numbers():
    m=module()
    for actual in ['NaN', 'Infinity', 'true', '2', 'null', '1.0']:
        with pytest.raises(ValueError):m.parse_field(actual,1)
    assert m.parse_field('1',1)==1
    assert m.parse_field('REVIEW','REVIEW')=='REVIEW'


def test_fixed_schedule_and_invalid_attempt_does_not_skip():
    m=module()
    assert m.next_slot([])==('practice',1,'A')
    rows=[{'phase':'practice','slot':1,'condition':'A','status':'aborted'}]
    assert m.next_slot(rows)==('practice',1,'A')
    rows += [{'phase':'practice','slot':1,'condition':'A','status':'complete'},
             {'phase':'practice','slot':2,'condition':'B','status':'complete'}]
    assert m.next_slot(rows)==('measured',1,'A')
    for slot,condition in enumerate('ABBAAB',1):
        assert m.next_slot(rows)==('measured',slot,condition)
        rows.append({'phase':'measured','slot':slot,'condition':condition,'status':'complete'})
    assert m.next_slot(rows) is None


def test_fixed_output_mismatch_rejected(tmp_path):
    m=module();(tmp_path/'a').write_text('changed')
    with pytest.raises(ValueError,match='digest'):m.assert_digests(tmp_path,{'a':'0'*64})


def test_stage_runner_executes_once_and_retains_failed_review(tmp_path):
    m=module();events=[];seen=[]
    runner=m.StageRecorder(tmp_path,'A',lambda kind,**kw:events.append((kind,kw)),
                           lambda stage,fields:seen.append((stage,fields)))
    runner.before('example')
    runner.after('example',{'count':1})
    assert seen==[('example',{'count':1})]
    assert json.loads((tmp_path/'stages/01-example.json').read_text())=={'count':1}
    with pytest.raises(ValueError,match='already'):runner.before('example')


def test_explicit_production_stages_are_ordered():
    m=module()
    assert m.STAGES==['source_load','quality','marts','overall','cohorts','temporal',
                      'sensitivity','fault_lab','report_issues','crosscheck','build','verify']


def test_batch_waits_for_all_stages_before_identical_review(tmp_path):
    m=module();reviewed=[]
    r=m.StageRecorder(tmp_path,'B',lambda *a,**k:None,lambda s,p:reviewed.append((s,p)))
    for stage,payload in [('one',{'n':1}),('two',{'n':2})]:
        r.before(stage);r.after(stage,payload)
    assert reviewed==[]
    r.review_batch()
    assert reviewed==[('one',{'n':1}),('two',{'n':2})]
    with pytest.raises(ValueError,match='already'):r.review_batch()


def test_stage_cannot_finish_twice_or_finish_out_of_order(tmp_path):
    m=module();r=m.StageRecorder(tmp_path,'A',lambda *a,**k:None,lambda *a:None)
    r.before('one')
    with pytest.raises(ValueError):r.before('two')
    with pytest.raises(ValueError):r.after('two',{})
    r.after('one',{})
    with pytest.raises(ValueError):r.after('one',{})


def test_pending_stage_digest_checked_before_manual_review(tmp_path):
    m=module();seen=[]
    expected={'stages/01-source_load.json':'0'*64}
    r=m.StageRecorder(tmp_path,'A',lambda *a,**k:None,lambda *a:seen.append(a),expected_stages=expected)
    r.before('source_load')
    with pytest.raises(ValueError,match='digest'):r.after('source_load',{'source_files':7})
    assert seen==[]


@pytest.mark.parametrize('bad',[
    {'schema_version':999},
    {'schema_version':1,'status':'complete','phase':'measured','slot':1,'condition':'A','elapsed_seconds':float('nan')},
    {'schema_version':1,'status':'complete','phase':'measured','slot':True,'condition':'A','elapsed_seconds':1},
    {'schema_version':1,'status':'complete','phase':'measured','slot':1,'condition':'A','elapsed_seconds':1,'review_records':[]},
])
def test_corrupt_records_cannot_advance_schedule(tmp_path,bad):
    m=module();p=tmp_path/'attempts/001/record.json';p.parent.mkdir(parents=True)
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError,match='record'):m.records(tmp_path)


def test_review_is_compact_and_shows_comparison_intervals(capsys,tmp_path):
    m=module();report=json.loads((m.ROOT/'reports/report.json').read_text())
    m.show_review('cohorts',{'cohorts':report['cohorts']},tmp_path/'stage.json')
    text=capsys.readouterr().out
    assert '95%' in text and 'stage.json' in text
    assert len(text.splitlines())<60
    assert 'AAA_2013J_eligible' in text
    assert 'bootstrap_draws' not in text


def test_init_requires_explicit_provenance_before_touching_disk(tmp_path):
    m=module()
    with pytest.raises(ValueError,match='provenance'):m.initialize(tmp_path/'study',tmp_path/'raw','invented')
    assert not (tmp_path/'study').exists()


@pytest.fixture
def synthetic_study(tmp_path,monkeypatch):
    """Stub only expensive data computation; exercise real CLI recording and files."""
    m=module();study=tmp_path/'developer_synthetic';study.mkdir()
    snapshot=study/'snapshot';(snapshot/'reports').mkdir(parents=True);(snapshot/'sql').mkdir()
    (snapshot/'data').mkdir();(snapshot/'data/manifest.json').write_text('{}')
    (snapshot/'README.md').write_text('developer_synthetic')
    raw=tmp_path/'developer_synthetic_raw';raw.mkdir()
    expected=tmp_path/'stage';m.write_json(expected,{'source_files':7,'archive_sha256':'abc'})
    m.write_json(study/'protocol.json',{'schema_version':1,'provenance':'developer_synthetic',
        'schedule':{'practice':'AB','measured':'ABBAAB'},'fingerprint':m.fingerprint(),
        'snapshot_sha256':{},'source_sha256':{},'raw_dir':str(raw),'expected_outputs':{},
        'expected_stages':{'stages/01-source_load.json':m.digest(expected)},'review_fields_total':2})
    def fake_pipeline(root,recorder):
        recorder.before('source_load');recorder.after('source_load',{'source_files':7,'archive_sha256':'abc'})
    monkeypatch.setattr(m,'pipeline',fake_pipeline)
    return m,study


def test_wrong_manual_entry_preserved_and_next_attempt_same_slot(synthetic_study,monkeypatch):
    m,study=synthetic_study
    answers=iter(['start','run','NaN']);monkeypatch.setattr('builtins.input',lambda _:next(answers))
    m.run_round(study)
    row=m.records(study)[0]
    assert row['status']=='invalid' and row['provenance']=='developer_synthetic'
    assert row['review_records'][0]['entered']['source_files']=={'raw':'NaN','correct':False}
    assert row['invalid_inputs']==1
    assert m.next_slot(m.records(study))==('practice',1,'A')
    answers=iter(['start',':abort'])
    m.run_round(study)
    rows=m.records(study)
    assert [r['status'] for r in rows]==['invalid','aborted']
    assert len(list((study/'attempts').glob('*/events.jsonl')))==2
    assert all((r['phase'],r['slot'],r['condition'])==('practice',1,'A') for r in rows)


def test_pause_before_start_excluded_from_measurement(synthetic_study,monkeypatch):
    m,study=synthetic_study
    answers=iter([':pause','','start',':abort']);monkeypatch.setattr('builtins.input',lambda _:next(answers))
    m.run_round(study)
    row=m.records(study)[0]
    assert row['status']=='aborted' and row['pause_seconds']==0
    assert row['machine_seconds']==0


def test_eof_before_start_is_preserved_without_invented_time(synthetic_study,monkeypatch):
    m,study=synthetic_study
    def eof(_):raise EOFError
    monkeypatch.setattr('builtins.input',eof)
    m.run_round(study)
    row=m.records(study)[0]
    assert row['status']=='aborted' and row['elapsed_seconds'] is None


@pytest.fixture
def completed_synthetic_schedule(synthetic_study,monkeypatch):
    m,study=synthetic_study
    monkeypatch.setattr(m,'STAGES',['source_load'])
    monkeypatch.setattr(m,'OUTPUTS',[])
    m.write_json(study/'calibration/stages/01-source_load.json',{'source_files':7,'archive_sha256':'abc'})
    for condition in 'ABABBAAB':
        answers=iter(['start','run','7','abc','reviewed'] if condition=='A' else ['start','reviewed'])
        monkeypatch.setattr('builtins.input',lambda _:next(answers))
        m.run_round(study)
    return m,study


def test_schedule_finishes_without_duplicate_continuation(completed_synthetic_schedule):
    m,study=completed_synthetic_schedule
    rows=m.records(study)
    assert len(rows)==8 and all(r['status']=='complete' for r in rows)
    assert ''.join(r['condition'] for r in rows)=='ABABBAAB'
    assert all(r['provenance']=='developer_synthetic' for r in rows)
    m.run_round(study)
    assert len(m.records(study))==8


def test_audit_checks_complete_records_and_rejects_changed_outputs(completed_synthetic_schedule):
    m,study=completed_synthetic_schedule
    assert m.audit_study(study)['completed_measured']==6
    path=next((study/'attempts').glob('*/stages/01-source_load.json'))
    path.write_text('{}')
    with pytest.raises(ValueError,match='digest'):m.audit_study(study)


def test_audit_rejects_forged_timing(completed_synthetic_schedule):
    m,study=completed_synthetic_schedule
    path=next((study/'attempts').glob('*/record.json'))
    row=json.loads(path.read_text());row['machine_seconds']=99999;m.write_json(path,row)
    with pytest.raises(ValueError,match='timing'):m.audit_study(study)


def test_orphan_setup_directory_is_preserved_and_does_not_block_retry(synthetic_study,monkeypatch):
    m,study=synthetic_study
    orphan=study/'attempts/001-practice-1-A';(orphan/'reports').mkdir(parents=True)
    answers=iter(['start',':abort']);monkeypatch.setattr('builtins.input',lambda _:next(answers))
    m.run_round(study)
    rows=m.records(study)
    assert len(rows)==2 and all(r['status']=='aborted' for r in rows)
    assert rows[0]['elapsed_seconds'] is None and (orphan/'events.jsonl').is_file()
    assert rows[1]['attempt']==2


def test_prestart_crash_without_event_log_can_be_recovered(synthetic_study,monkeypatch):
    m,study=synthetic_study
    root=study/'attempts/001-practice-1-A';root.mkdir(parents=True)
    m.write_json(root/'record.json',{'schema_version':1,'provenance':'developer_synthetic',
        'protocol_sha256':m.digest(study/'protocol.json'),'attempt':1,'phase':'practice',
        'slot':1,'condition':'A','status':'running','review_records':[],'invalid_inputs':0})
    answers=iter(['start',':abort']);monkeypatch.setattr('builtins.input',lambda _:next(answers))
    m.run_round(study)
    assert (root/'events.jsonl').is_file()
    row=m.records(study)[0]
    assert row['status']=='aborted' and row['elapsed_seconds'] is None


def test_audit_rejects_nonfinite_event_elapsed(completed_synthetic_schedule):
    m,study=completed_synthetic_schedule
    path=next((study/'attempts').glob('*/events.jsonl'))
    events=[json.loads(line) for line in path.read_text().splitlines()]
    events[-1]['elapsed_seconds']=float('nan')
    path.write_text(''.join(json.dumps(e)+'\n' for e in events))
    with pytest.raises(ValueError,match='timing'):m.audit_study(study)

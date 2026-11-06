"""Codex review: submitted orchestrator unchanged; generated fixtures and controlled failures."""
import csv
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'evidence/applicant'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(raw, path):
    path.write_text(json.dumps({'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)}
                                              for p in sorted(raw.glob('*.csv'))}}))


def inputs(folder):
    raw = folder / "raw folder's name"
    raw.mkdir(parents=True)
    data = {
        'courses': (['code_module','code_presentation','module_presentation_length'], [('AAA','2014J',30)]),
        'vle': (['code_module','code_presentation','id_site','activity_type'], [('AAA','2014J',10,'resource')]),
        'studentRegistration': (['code_module','code_presentation','id_student','date_registration','date_unregistration'],
                                [('AAA','2014J',1,0,6),('AAA','2014J',2,0,None),('AAA','2014J',3,0,None)]),
        'studentVle': (['code_module','code_presentation','id_student','id_site','date','sum_click'],
                       [('AAA','2014J',i,10,d,1) for i,d in [(1,0),(2,0),(2,1),(2,8),(3,8)]]),
    }
    for name in ('assessments','studentAssessment','studentInfo'):
        data[name] = (['id','value'], [(1,2)])
    for name,(header,rows) in data.items():
        with (raw / (name+'.csv')).open('w', newline='') as f:
            writer=csv.writer(f); writer.writerow(header); writer.writerows(rows)
    manifest=folder/'manifest.json'; write_manifest(raw,manifest)
    return manifest,raw,folder/'output folder'


def invoke(args, script=APP/'run_pipeline.py', cwd=None):
    manifest,raw,out=args
    return subprocess.run([sys.executable,str(script),'--manifest',str(manifest),
                           '--raw-dir',str(raw),'--output-dir',str(out)],
                          cwd=cwd,capture_output=True,text=True,timeout=60)


def records(output):
    return [json.loads(p.read_text()) for p in sorted((output/'runs').glob('*/run_record.json'))]


@pytest.fixture(scope='module')
def healthy(tmp_path_factory):
    folder=tmp_path_factory.mktemp('pipeline fixture')
    args=inputs(folder)
    before={p:(sha(p),p.stat().st_mtime_ns) for p in [args[0],*args[1].glob('*.csv')]}
    result=invoke(args,cwd=folder)
    assert result.returncode==0,result.stderr
    assert before=={p:(sha(p),p.stat().st_mtime_ns) for p in before}
    run=next((args[2]/'runs').iterdir())
    return args,run


def test_real_subprocesses_hand_check_and_repeat(healthy):
    args,run=healthy
    first=json.loads((run/'run_record.json').read_text())
    assert first['status']=='success' and first['quality_gate']=='PASS'
    assert first['overall']=={'eligible':3,'w1_active':2,'w2_returned':1}
    assert len(first['steps'])==7 and all(s['exit_code']==0 and s['status']=='success' for s in first['steps'])
    assert first['elapsed_seconds']>=sum(s['elapsed_seconds'] for s in first['steps'])
    assert len(first['inputs']['source_csv_from_manifest'])==7
    for name,meta in first['artifacts'].items(): assert sha(run/meta['path'])==meta['sha256']
    for s in first['steps']:
        assert (run/s['stdout_log']).is_file() and (run/s['stderr_log']).is_file()
    original={p:(sha(p),p.stat().st_mtime_ns) for p in run.rglob('*') if p.is_file()}
    repeat=invoke(args,cwd=args[0].parent)
    assert repeat.returncode==0,repeat.stderr
    assert len(records(args[2]))==2
    assert original=={p:(sha(p),p.stat().st_mtime_ns) for p in original}
    second=next(p for p in (args[2]/'runs').iterdir() if p!=run)
    for name in ('quality.json','activity-groups.json'):
        assert json.loads((second/name).read_text())==json.loads((run/name).read_text())
    a=json.loads((run/'statistics.json').read_text()); b=json.loads((second/'statistics.json').read_text())
    a.pop('input_sha256');b.pop('input_sha256'); assert a==b


@pytest.mark.parametrize('mode', ['review','block','manifest','missing_raw','bad_csv_hash'])
def test_real_failure_and_review_routing(tmp_path,mode):
    args=inputs(tmp_path);manifest,raw,out=args
    if mode in ('review','block'):
        with (raw/'studentVle.csv').open('a', newline='') as f:
            csv.writer(f).writerow(('AAA','2014J',1 if mode=='review' else 999,10,0,1))
        write_manifest(raw,manifest)
    elif mode=='manifest':manifest.write_text('{broken')
    elif mode=='missing_raw':shutil.rmtree(raw)
    else:(raw/'courses.csv').write_text('corrupt')
    result=invoke(args);rec=records(out)[0]
    expected=0 if mode=='review' else 2 if mode=='block' else 1
    assert result.returncode==expected,result.stderr
    if mode=='review': assert rec['status']=='success' and rec['quality_gate']=='REVIEW'
    elif mode=='block':
        assert rec['status']=='blocked' and rec['failed_step']=='quality'
        assert all(s['status']=='pending' for s in rec['steps'][3:])
        d=out/'runs'/rec['run_id'];assert (d/'quality.json').is_file() and not (d/'enrollment_mart.csv').exists()
    elif mode=='manifest':
        assert rec['status']=='error' and rec['steps'][0]['exit_code']==2
        assert all(s['status']=='pending' for s in rec['steps'][1:])
    else:assert rec['status']=='error'


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    return importlib.import_module('run_pipeline')


@pytest.fixture
def sandbox(tmp_path,module,monkeypatch,healthy):
    code=tmp_path/'code folder';code.mkdir()
    for n in module.SCRIPTS_AND_SQL:shutil.copy2(APP/n,code/n)
    monkeypatch.setattr(module,'__file__',str(code/'run_pipeline.py'))
    args=inputs(tmp_path)
    return module,args,code,healthy[1]


def stub(sandbox,monkeypatch,fail_stage=None,mode=None):
    module,args,code,template=sandbox;called=[]
    def child(argv,stdout,stderr,cwd,check):
        assert argv[0]==sys.executable and Path(cwd)==code and check is False
        index=len(called);name=module.STAGES[index];called.append(name)
        destination=Path(argv[argv.index('--db')+1]).parent if '--db' in argv else None
        if destination is None and '--output' in argv:destination=Path(argv[argv.index('--output')+1]).parent
        if destination:
            for n in module.ARTIFACT_NAMES:shutil.copy2(template/n,destination/n)
        stdout.write(b'controlled child output\n');stderr.write(b'controlled stderr\n')
        if name==fail_stage:
            if mode=='interrupt':raise KeyboardInterrupt
            if mode=='oserror':raise OSError('controlled launch error')
            if mode=='missing':(destination/'activity-groups.json').unlink()
            elif mode=='invalid_json':(destination/'quality.json').write_text('{bad')
            elif mode=='bad_gate':
                p=destination/'quality.json';r=json.loads(p.read_text());r['gate']='BLOCK';p.write_text(json.dumps(r))
            else:return subprocess.CompletedProcess(argv,int(mode))
        return subprocess.CompletedProcess(argv,0)
    monkeypatch.setattr(module.subprocess,'run',child)
    return called


@pytest.mark.parametrize('stage,mode,exit_code,status',[
    ('load_sources','3',1,'error'),('validate_sources','2',1,'error'),
    ('quality','2',1,'error'), # PASS report paired with BLOCK code must be rejected
    ('mart_base','2',2,'blocked'),('mart_strict','2',2,'blocked'),
    ('aggregate','missing',1,'error'),('quality','invalid_json',1,'error'),
    ('quality','bad_gate',1,'error'),('statistics','1',1,'error'),
    ('load_sources','oserror',1,'error'),('load_sources','interrupt',130,'aborted'),
])
def test_controlled_child_failure_stops_later_steps(sandbox,monkeypatch,stage,mode,exit_code,status):
    module,args,_,_=sandbox;called=stub(sandbox,monkeypatch,stage,mode)
    assert module.run(*args)==exit_code
    rec=records(args[2])[0]; assert rec['status']==status and rec['failed_step']==stage
    assert called==list(module.STAGES[:module.STAGES.index(stage)+1])
    assert all(s['status']=='pending' and s['exit_code'] is None for s in rec['steps'][len(called):])
    assert rec['ended_at_utc'] and rec['elapsed_seconds']>=0 and rec['overall'] is None
    if mode in ('interrupt','oserror'):assert rec['steps'][len(called)-1]['exit_code'] is None


def test_missing_dependency_before_child(sandbox,monkeypatch):
    module,args,code,_=sandbox;(code/'learning_stats.py').unlink()
    called=stub(sandbox,monkeypatch)
    assert module.run(*args)==1 and not called
    assert records(args[2])[0]['failed_step']=='preflight'


@pytest.mark.parametrize('placement',['raw','under_raw','manifest','script','runs_symlink_raw'])
def test_output_collision_preserves_inputs(sandbox,placement):
    module,args,code,_=sandbox;manifest,raw,out=args
    if placement=='raw':out=raw
    elif placement=='under_raw':out=raw/'nested'
    elif placement=='manifest':out=manifest
    elif placement=='script':out=code/'run_pipeline.py'
    else:out.mkdir();(out/'runs').symlink_to(raw,target_is_directory=True)
    before={p:sha(p) for p in [manifest,*raw.iterdir(),code/'run_pipeline.py']}
    with pytest.raises(module.PipelineError):module.run(manifest,raw,out)
    assert before=={p:sha(p) for p in before}


@pytest.mark.parametrize('mutation',['counts','ratio','percent','aggregate_hash','stats_hash','section','group','nonfinite','manifest','code','artifact_symlink'])
def test_final_reconciliation_rejects_bad_artifact(sandbox,mutation):
    module,args,code,template=sandbox;d=args[0].parent/'artifacts';shutil.copytree(template,d)
    manifest_hash,code_hashes=module.input_inventory(args[0],code)
    name='statistics.json';p=d/name;s=json.loads(p.read_text())
    if mutation=='counts':s['overall']['eligible']+=1
    elif mutation=='ratio':s['overall']['return_rate']=50
    elif mutation=='stats_hash':s['input_sha256']['mart']='0'*64
    elif mutation=='section':s.pop('temporal')
    elif mutation=='nonfinite':s['overall']['return_rate']=float('nan')
    elif mutation in ('percent','aggregate_hash','group'):
        p=d/'activity-groups.json';s=json.loads(p.read_text())
        if mutation=='percent':s['overall']['return_rate_pct']=.5
        elif mutation=='aggregate_hash':s['input_sha256']='0'*64
        else:s['rows'][0]['denominator']+=1
    elif mutation=='manifest':args[0].write_text(args[0].read_text()+' ')
    elif mutation=='code':(code/'aggregate.sql').write_text('-- changed')
    elif mutation=='artifact_symlink':
        (d/'oulad.duckdb').unlink();(d/'oulad.duckdb').symlink_to(template/'oulad.duckdb')
    p.write_text(json.dumps(s))
    with pytest.raises(module.PipelineError):module.validate_final(d,args[0],manifest_hash,code,code_hashes,'PASS')


def test_atomic_record_failure_preserves_previous(module,tmp_path,monkeypatch):
    p=tmp_path/'record.json';p.write_text('{"old":true}')
    def fail(*args):raise OSError('controlled disk replace failure')
    monkeypatch.setattr(module.os,'replace',fail)
    with pytest.raises(OSError):module.atomic_record(p,{'new':True})
    assert json.loads(p.read_text())=={'old':True}
    assert not list(tmp_path.glob('*.tmp'))


def test_record_write_error_never_reports_success(sandbox,monkeypatch,capsys):
    module,args,_,_=sandbox
    def fail(*args):raise OSError('controlled disk write failure')
    monkeypatch.setattr(module,'atomic_record',fail)
    assert module.run(*args)==1
    text=capsys.readouterr();assert 'SUCCESS' not in text.out and '기록하지 못했습니다' in text.err


def test_argument_errors_exit_one():
    result=subprocess.run([sys.executable,str(APP/'run_pipeline.py')],capture_output=True,text=True)
    assert result.returncode==1

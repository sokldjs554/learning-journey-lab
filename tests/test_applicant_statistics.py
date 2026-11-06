"""Codex-authored independent fixtures and failure checks for submitted statistics."""
import csv
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import duckdb
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
APPLICANT=ROOT/'evidence/applicant'
COLS=['code_module','code_presentation','id_student','w1_days','w2_active','later_active',
      'first_day','date_unregistration','first_content','first_clicks_raw','first_clicks_exact','first_clicks_max']


def record(student,days,w2,module='AAA',term='2014J',first_day=None,withdrawal=None,content=0,clicks=(1,1,1),later=0):
    return [module,term,student,days,w2,later,(0 if first_day is None else first_day) if days else None,
            withdrawal,content if days else 0,*(clicks if days else (0,0,0))]


def frame(records):return pd.DataFrame(records,columns=COLS)


def write_csv(path,records):
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(COLS);w.writerows(records)


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(APPLICANT))
    return importlib.import_module('learning_stats'),importlib.import_module('run_statistics')


def cluster_frame():
    f=frame([record(10,1,0),record(10,2,1,module='BBB'),record(20,1,1),record(30,2,0)])
    f['exposure']=(f.w1_days>=2).astype(int)
    return f


def test_bootstrap_repeated_learner_weight_and_invalid_draw(modules,monkeypatch):
    stats,_=modules;calls=[]
    class RNG:
        draws=iter([np.array([0,0,1]),np.array([1,1,1])])
        def integers(self,low,high,size):
            assert (low,high,size)==(0,3,3)
            return next(self.draws)
    def rng(seed):calls.append(seed);return RNG()
    monkeypatch.setattr(stats.np.random,'default_rng',rng)
    result=stats.compare(cluster_frame(),'exposure',2)
    assert calls==[101] and result['difference']==0 and result['clusters']==3
    assert result['control']=={'n':2,'returned':1,'rate':.5}
    assert result['exposed']=={'n':2,'returned':1,'rate':.5}
    assert result['valid_draws']==1 and result['ci']==pytest.approx([2/3,2/3])


def test_bootstrap_against_literal_row_resampling_and_permutation(modules):
    stats,_=modules;f=cluster_frame();ids=sorted(f.id_student.unique());rng=np.random.default_rng(101)
    points=[]
    for _ in range(50):
        sampled=[r for idx in rng.integers(0,len(ids),len(ids)) for r in f.itertuples() if r.id_student==ids[idx]]
        a=[r.w2_active for r in sampled if r.exposure==0];b=[r.w2_active for r in sampled if r.exposure==1]
        if a and b:points.append(sum(b)/len(b)-sum(a)/len(a))
    expected=np.quantile(points,[.025,.975],method='linear')
    actual=stats.compare(f,'exposure',50)
    assert actual['valid_draws']==len(points)<50
    assert actual['ci']==pytest.approx(expected,abs=1e-12)
    assert stats.compare(f.iloc[::-1],'exposure',50)==actual
    assert stats.compare(f,'exposure',50)==actual


@pytest.mark.parametrize('mode',['empty','one_side','one_learner_side','all_invalid'])
def test_insufficient_comparisons(modules,monkeypatch,mode):
    stats,_=modules;f=cluster_frame()
    if mode=='empty':f=f.iloc[:0]
    elif mode=='one_side':f=f[f.exposure==0]
    elif mode=='one_learner_side':f=f[f.id_student!=20]
    else:
        class RNG:
            def integers(self,low,high,size):return np.array([1,1,1])
        monkeypatch.setattr(stats.np.random,'default_rng',lambda seed:RNG())
    actual=stats.compare(f,'exposure',4)
    assert actual['ci'] is None and actual['valid_draws']==0
    if mode in ('empty','one_side'):assert actual['difference'] is None
    else:assert actual['difference'] is not None


def test_summary_zero_day_exclusion_and_empty_day_groups(modules):
    stats,_=modules
    f=frame([record(1,0,1),record(2,1,0),record(2,2,1,module='BBB')])
    before=f.copy(deep=True);summary=stats.summarize(f,10)
    assert (summary['eligible'],summary['unique_learners'],summary['w1_active'],summary['w2_returned'])==(3,2,2,1)
    assert summary['return_rate']==.5 and len(summary['days'])==8
    assert summary['days'][0]=={'days':0,'n':1,'returned':1,'rate':1.0}
    assert summary['days'][7]=={'days':7,'n':0,'returned':0,'rate':None}
    pd.testing.assert_frame_equal(f,before)


def test_first_day_six_no_second_group(modules):
    stats,_=modules;actual=stats.first_day_summaries(frame([record(1,1,1,first_day=6),record(2,0,1)]))
    assert len(actual)==1 and actual[0]['first_day']==6
    c=actual[0]['comparison'];assert c['exposed']['n']==0 and c['difference'] is None and c['bootstrap_draws']==500


def test_click_threshold_inclusive_and_policy_change(modules):
    stats,_=modules
    f=frame([record(1,1,1,clicks=(10,9,9)),record(2,2,0,clicks=(20,20,19)),record(3,3,1,clicks=(50,49,48)),record(4,0,1)])
    actual=stats.click_sensitivities(f)
    assert actual==[
      dict(threshold=10,raw_qualified=3,exact_qualified=2,max_qualified=2,raw_vs_exact_changed=1,raw_vs_max_changed=1),
      dict(threshold=20,raw_qualified=2,exact_qualified=2,max_qualified=1,raw_vs_exact_changed=0,raw_vs_max_changed=1),
      dict(threshold=50,raw_qualified=1,exact_qualified=0,max_qualified=0,raw_vs_exact_changed=1,raw_vs_max_changed=1)]


def test_transitions_and_zero_cells(modules):
    stats,_=modules;actual=stats.transitions(frame([record(1,0,0,later=1),record(2,0,1),record(3,2,1,later=1)]))
    assert actual==[dict(w1=0,w2=0,n=1,later_active=1),dict(w1=0,w2=1,n=1,later_active=0),
                    dict(w1=1,w2=0,n=0,later_active=0),dict(w1=1,w2=1,n=1,later_active=1)]


def test_strict_key_alignment_and_days_value_not_presence(modules):
    stats,_=modules;base=frame([record(1,2,1),record(2,3,1),record(3,0,0)])
    strict=frame([record(3,0,0),record(1,1,1),record(2,1,0)])
    assert stats.strict_sensitivity(base,strict)==dict(w1_active=2,w2_returned=1,changed_w1_enrollments=2,changed_w2_enrollments=1)


@pytest.fixture
def paths(tmp_path):
    base,strict,db,out=[tmp_path/n for n in ['base.csv','strict.csv','source.duckdb','stats.json']]
    rows=[record(10,1,0),record(20,2,1)]
    write_csv(base,rows);write_csv(strict,rows)
    with duckdb.connect(str(db)) as con:
        con.execute('CREATE TABLE studentRegistration(code_module VARCHAR,code_presentation VARCHAR,id_student BIGINT,date_registration BIGINT,date_unregistration BIGINT)')
        con.executemany('INSERT INTO studentRegistration VALUES (?,?,?,?,?)',[(r[0],r[1],r[2],0,r[7]) for r in rows])
    return base,strict,db,out


def invoke(paths):
    base,strict,db,out=paths
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in [base,strict,db] if p.is_file()}
    result=subprocess.run([sys.executable,str(APPLICANT/'run_statistics.py'),'--mart',str(base),'--strict-mart',str(strict),
                           '--db',str(db),'--output',str(out)],capture_output=True,text=True,timeout=40)
    assert before=={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in before}
    assert not list(out.parent.glob('*.tmp'))
    return result


def test_cli_empty_input(paths):
    base,strict,db,out=paths;write_csv(base,[]);write_csv(strict,[])
    result=invoke(paths);assert result.returncode==0,result.stderr
    report=json.loads(out.read_text());assert report['overall']['eligible']==0 and report['overall']['return_rate'] is None
    assert len(report['overall']['days'])==8 and report['cohorts']==[] and report['first_day_strata']==[]
    assert len(report['temporal'])==2 and len(report['transition'])==4 and len(report['click_sensitivity'])==3
    assert all(t['eligible']==0 for t in report['temporal'])
    assert all(v==0 for v in report['strict_sensitivity'].values())


def test_cli_repeat_sorted_scopes_hashes_and_no_person_ids(paths):
    base,strict,db,out=paths;write_csv(strict,[record(20,2,1),record(10,1,0)])
    assert invoke(paths).returncode==0
    r=json.loads(out.read_text());assert r['scope']=='observational_statistics'
    assert r['overall']['eligible']==2 and r['overall']['return_rate']==.5
    assert r['input_sha256']=={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in zip(['mart','strict_mart','db'],paths[:3])}
    assert 'id_student' not in out.read_text()
    first=out.read_bytes();assert invoke(paths).returncode==0 and out.read_bytes()==first


def test_cli_ineligible_2013_registration_excluded_from_2014(paths):
    base,strict,db,out=paths
    rows=[record(10,1,0),record(20,2,1),record(30,1,1,term='2013J'),
          record(30,2,0),record(40,1,1),record(50,2,1,term='2015J')]
    write_csv(base,rows);write_csv(strict,rows)
    with duckdb.connect(str(db)) as con:
        con.execute('DELETE FROM studentRegistration')
        registrations=[(r[0],r[1],r[2],0,None) for r in rows]
        registrations += [('AAA','2013J',10,None,None),('AAA','2013J',20,5,None)]
        con.executemany('INSERT INTO studentRegistration VALUES (?,?,?,?,?)',registrations)
    result=invoke(paths);assert result.returncode==0,result.stderr
    r=json.loads(out.read_text());assert r['overall']['eligible']==6
    discovery,holdout=r['temporal'];assert discovery['eligible']==1 and holdout['eligible']==1
    assert holdout['w1_active']==1 and holdout['w2_returned']==1
    assert [(c['module'],c['term']) for c in r['cohorts']]==[('AAA','2013J'),('AAA','2014J'),('AAA','2015J')]


@pytest.mark.parametrize('mode',['missing_key','duplicate_registration','null_registration','wrong_id_type','missing_table','missing_column'])
def test_cli_invalid_registration(paths,mode):
    base,strict,db,out=paths;out.write_text('old result')
    with duckdb.connect(str(db)) as con:
        if mode=='missing_key':con.execute('DELETE FROM studentRegistration WHERE id_student=10')
        elif mode=='duplicate_registration':con.execute('INSERT INTO studentRegistration SELECT * FROM studentRegistration LIMIT 1')
        elif mode=='null_registration':con.execute('UPDATE studentRegistration SET id_student=NULL WHERE id_student=10')
        elif mode=='wrong_id_type':con.execute('ALTER TABLE studentRegistration ALTER id_student TYPE VARCHAR')
        elif mode=='missing_table':con.execute('DROP TABLE studentRegistration')
        else:con.execute('ALTER TABLE studentRegistration DROP COLUMN code_module')
    result=invoke(paths);assert result.returncode==1 and out.read_text()=='old result'


@pytest.mark.parametrize('mode',['missing_key','duplicate','withdrawal_diff','null_withdrawal_diff','bad_value','bad_header','missing_file','missing_db'])
def test_cli_invalid_inputs(paths,mode):
    base,strict,db,out=paths;out.write_text('old result');rows=[record(10,1,0),record(20,2,1)]
    if mode=='missing_key':write_csv(strict,rows[:1])
    elif mode=='duplicate':write_csv(strict,rows+[rows[0]])
    elif mode=='withdrawal_diff':
        rows[0][7]=7;write_csv(base,rows);rows[0][7]=8;write_csv(strict,rows)
    elif mode=='null_withdrawal_diff':rows[0][7]=7;write_csv(strict,rows)
    elif mode=='bad_value':rows[0][4]=2;write_csv(base,rows)
    elif mode=='bad_header':base.write_text('')
    elif mode=='missing_file':strict.unlink()
    elif mode=='missing_db':db.unlink()
    result=invoke(paths);assert result.returncode==1 and out.read_text()=='old result'
    if mode=='missing_db':assert not db.exists()


@pytest.mark.parametrize('target',['base','strict','db','symlink','hardlink'])
def test_output_aliases(paths,tmp_path,target):
    base,strict,db,out=paths
    if target in ('symlink','hardlink'):
        out=tmp_path/'alias'
        if target=='symlink':out.symlink_to(db)
        else:os.link(db,out)
    else:out={'base':base,'strict':strict,'db':db}[target]
    assert invoke((base,strict,db,out)).returncode==1


def test_output_failure_cleanup(paths):
    paths[3].mkdir();assert invoke(paths).returncode==1 and paths[3].is_dir()


@pytest.mark.parametrize('mode',['changed_input','nan_result','calculation_error'])
def test_runtime_errors_preserve_report(modules,monkeypatch,paths,mode):
    _,runner=modules;base,strict,db,out=paths;out.write_text('old result')
    if mode=='changed_input':
        hashes=iter(['a','b','c','changed','b','c']);monkeypatch.setattr(runner,'sha256_file',lambda p:next(hashes))
    elif mode=='nan_result':monkeypatch.setattr(runner,'calculate_statistics',lambda *args:{'bad':float('nan')})
    else:
        def fail(*args):raise ValueError('calculation failure')
        monkeypatch.setattr(runner,'calculate_statistics',fail)
    expected_error=runner.QualityRunError if mode=='changed_input' else ValueError
    with pytest.raises(expected_error):runner.run(base,strict,db,out)
    assert out.read_text()=='old result'


def test_import_has_no_analysis_io(tmp_path):
    code='import sys; sys.path.insert(0, '+repr(str(APPLICANT))+'); import learning_stats; import run_statistics'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-c',code],cwd=tmp_path,env=env,capture_output=True,text=True)
    assert result.returncode==0 and result.stdout=='' and result.stderr=='' and list(tmp_path.iterdir())==[]


def test_cli_missing_arguments():
    result=subprocess.run([sys.executable,str(APPLICANT/'run_statistics.py')],capture_output=True,text=True)
    assert result.returncode==1

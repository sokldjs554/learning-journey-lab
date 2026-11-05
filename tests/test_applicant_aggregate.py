"""Codex-authored review of unchanged applicant activity aggregation files."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import duckdb
import pytest

ROOT=Path(__file__).resolve().parents[1]
APPLICANT=ROOT/'evidence/applicant'
SQL=(APPLICANT/'aggregate.sql').read_text()
COLUMNS=('code_module','code_presentation','id_student','w1_days','w2_active',
         'later_active','first_day','date_unregistration','first_content',
         'first_clicks_raw','first_clicks_exact','first_clicks_max')


def row(student,days,returned,module='AAA',term='2014J'):
    return [module,term,student,days,returned,0,0 if days else None,None,0,
            1 if days else 0,1 if days else 0,1 if days else 0]


def eight():
    # Applicant's previously hand-checked example; extra mart fields supplied by Codex.
    return [row(i,d,y) for i,(d,y) in enumerate([(0,0),(1,0),(1,1),(2,0),(2,1),(3,1),(4,1),(5,0)],1)]


def write_csv(path,rows,header=COLUMNS):
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)


def module(monkeypatch):
    monkeypatch.syspath_prepend(str(APPLICANT))
    spec=importlib.util.spec_from_file_location('submitted_aggregate',APPLICANT/'run_aggregate.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def sql_query(rows):
    with duckdb.connect() as con:
        con.execute('CREATE TABLE mart(code_module VARCHAR,code_presentation VARCHAR,id_student BIGINT,w1_days INTEGER,w2_active INTEGER)')
        if rows:con.executemany('INSERT INTO mart VALUES (?,?,?,?,?)',[r[:5] for r in rows])
        return con.execute(SQL).fetchall()


def test_eight_hand_calculation_sql():
    counts=[('1일',2,1,50.0),('2일',2,1,50.0),('3일 이상',3,2,66.7)]
    expected=[('overall',None,None,*r) for r in counts]+[('cohort','AAA','2014J',*r) for r in counts]
    assert sql_query(eight())==expected


def test_empty_and_inactive_cohort_sql():
    groups=['1일','2일','3일 이상']
    overall=[('overall',None,None,g,0,0,None) for g in groups]
    assert sql_query([])==overall
    assert sql_query([row(1,0,1)])==overall+[('cohort','AAA','2014J',g,0,0,None) for g in groups]


def test_full_cohort_keys_same_student_and_zero_day_exclusion():
    result=sql_query([row(1,1,1),row(1,2,0,term='2013J'),row(1,3,1,module='BBB'),row(2,0,1,module='CCC')])
    assert len(result)==15
    assert result[:3]==[('overall',None,None,'1일',1,1,100.0),('overall',None,None,'2일',1,0,0.0),('overall',None,None,'3일 이상',1,1,100.0)]
    assert result[3]==('cohort','AAA','2013J','1일',0,0,None)
    assert result[4]==('cohort','AAA','2013J','2일',1,0,0.0)
    assert result[-3:]==[('cohort','CCC','2014J',g,0,0,None) for g in ['1일','2일','3일 이상']]


@pytest.mark.parametrize('numerator,expected',[(1,6.3),(3,18.8)])
def test_half_up_rounding_sql(numerator,expected):
    result=sql_query([row(i,1,int(i<numerator)) for i in range(16)])
    assert result[0][-1]==expected and result[3][-1]==expected


@pytest.fixture
def files(tmp_path):
    csv_path,sql,out=tmp_path/'mart.csv',tmp_path/'aggregate.sql',tmp_path/'out.json'
    write_csv(csv_path,eight());sql.write_text(SQL)
    return csv_path,sql,out


def invoke(files):
    csv_path,sql,out=files
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in [csv_path,sql] if p.is_file()}
    r=subprocess.run([sys.executable,str(APPLICANT/'run_aggregate.py'),'--mart',str(csv_path),
                      '--sql',str(sql),'--output',str(out)],capture_output=True,text=True,timeout=40)
    assert before=={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in before}
    assert not list(out.parent.glob('*.tmp'))
    return r


def test_cli_eight_repeat_hash_and_unsorted_input(files):
    csv_path,sql,out=files
    assert invoke(files).returncode==0
    report=json.loads(out.read_text())
    assert set(report)=={'schema_version','scope','input_sha256','overall','rows'}
    assert report['scope']=='descriptive_activity_groups' and report['schema_version']==1
    assert report['overall']==dict(eligible=8,w1_active=7,w2_returned=4,return_rate_pct=57.1)
    assert report['input_sha256']==hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert 'id_student' not in out.read_text() and len(report['rows'])==6
    before=out.read_bytes();assert invoke(files).returncode==0 and out.read_bytes()==before
    write_csv(csv_path,list(reversed(eight())))
    assert invoke(files).returncode==0
    shuffled=json.loads(out.read_text())
    assert shuffled['rows']==report['rows'] and shuffled['overall']==report['overall']
    # File hash, intentionally, changes with input serialization/order.
    assert shuffled['input_sha256']!=report['input_sha256']


@pytest.mark.parametrize('rows,eligible', [([],0),([row(1,0,1)],1)])
def test_cli_header_only_and_zero_activity(files,rows,eligible):
    csv_path,sql,out=files;write_csv(csv_path,rows)
    assert invoke(files).returncode==0
    report=json.loads(out.read_text())
    assert report['overall']==dict(eligible=eligible,w1_active=0,w2_returned=0,return_rate_pct=None)
    assert len(report['rows'])==(3 if eligible==0 else 6)
    assert all(r['return_rate_pct'] is None for r in report['rows'])


@pytest.mark.parametrize('kind',['duplicate','blank_module','blank_student','fractional_integer',
    'days_negative','days_eight','w2_two','later_two','bad_content','inactive_first_day',
    'inactive_clicks','first_day_impossible','negative_withdrawal','wrong_click_order',
    'negative_clicks','wrong_columns','missing_header','bad_header','empty_required'])
def test_invalid_csv_preserves_old_output(files,kind):
    csv_path,sql,out=files;out.write_text('old result');rows=eight()
    mutations={'blank_module':(0,''),'blank_student':(2,''),'fractional_integer':(3,'1.0'),
        'days_negative':(3,-1),'days_eight':(3,8),'w2_two':(4,2),'later_two':(5,2),
        'bad_content':(8,2),'first_day_impossible':(6,7),'negative_withdrawal':(7,-1),
        'wrong_click_order':(10,2),'negative_clicks':(9,-1),'empty_required':(4,'')}
    if kind in mutations:
        col,value=mutations[kind];rows[1][col]=value
    elif kind=='duplicate':rows.append(rows[0].copy())
    elif kind=='inactive_first_day':rows[0][6]=0
    elif kind=='inactive_clicks':rows[0][9]=1
    elif kind=='wrong_columns':rows[0].pop()
    write_csv(csv_path,rows, COLUMNS if kind!='bad_header' else COLUMNS[:-1])
    if kind=='missing_header':csv_path.write_text('')
    result=invoke(files)
    assert result.returncode==1 and 'ERROR:' in result.stderr
    assert out.read_text()=='old result'


@pytest.mark.parametrize('failure',['missing_mart','missing_sql','empty_sql','invalid_sql','wrong_result','directory_output'])
def test_cli_errors(files,failure):
    csv_path,sql,out=files;out.write_text('old result')
    if failure=='missing_mart':csv_path.unlink()
    elif failure=='missing_sql':sql.unlink()
    elif failure=='empty_sql':sql.write_text('')
    elif failure=='invalid_sql':sql.write_text('not SQL')
    elif failure=='wrong_result':sql.write_text('SELECT 1 AS wrong')
    elif failure=='directory_output':out.unlink();out.mkdir()
    assert invoke(files).returncode==1
    assert out.is_dir() if failure=='directory_output' else out.read_text()=='old result'


@pytest.mark.parametrize('target',['csv','sql','symlink'])
def test_input_output_aliases(files,tmp_path,target):
    csv_path,sql,out=files
    out=csv_path if target=='csv' else sql
    if target=='symlink':out=tmp_path/'alias';out.symlink_to(csv_path)
    assert invoke((csv_path,sql,out)).returncode==1


class Cursor:
    def __init__(self,columns,rows): self.description=[(x,) for x in columns];self.rows=rows
    def fetchall(self):return self.rows


@pytest.mark.parametrize('mutation',['missing','extra','duplicate_key','wrong_scope','wrong_group','wrong_cohort',
    'negative','fractional','boolean_count','swapped_counts','bad_rate','nan_rate','boolean_rate','zero_rate_instead_of_null'])
def test_sql_result_contract(monkeypatch,mutation):
    m=module(monkeypatch)
    keys=[('overall',None,None,g) for g in m.GROUPS]+[('cohort','AAA','2014J',g) for g in m.GROUPS]
    counts={keys[i]:[2,1] for i in [0,1,3,4]}
    overall=dict(eligible=4,w1_active=4,w2_returned=2,return_rate_pct=50.0)
    rows=[[*key,*(counts.get(key,[0,0])),50.0 if key in counts else None] for key in keys]
    if mutation=='missing':rows.pop()
    elif mutation=='extra':rows.append(rows[0])
    elif mutation=='duplicate_key':rows[1]=rows[0]
    elif mutation=='wrong_scope':rows[0][0]='wrong'
    elif mutation=='wrong_group':rows[0][3]='0일'
    elif mutation=='wrong_cohort':rows[3][2]='2013J'
    elif mutation=='negative':rows[0][4]=-1
    elif mutation=='fractional':rows[0][4]=2.0
    elif mutation=='boolean_count':rows[0][5]=True
    elif mutation=='swapped_counts':rows[0][5]=0;rows[1][5]=2 # same grand totals, wrong groups
    elif mutation=='bad_rate':rows[0][6]=49.9
    elif mutation=='nan_rate':rows[0][6]=float('nan')
    elif mutation=='boolean_rate':rows[0][6]=True
    elif mutation=='zero_rate_instead_of_null':rows[2][6]=0
    with pytest.raises(m.QualityRunError):m.validate_sql_result(Cursor(m.OUTPUT_COLUMNS,rows),keys,counts,overall)


def test_input_changed_during_run_preserves_output(monkeypatch,files):
    m=module(monkeypatch);csv_path,sql,out=files;out.write_text('old result')
    hashes=iter(['before','after'])
    monkeypatch.setattr(m,'sha256_file',lambda p:next(hashes))
    with pytest.raises(m.QualityRunError,match='변경'):m.run(csv_path,sql,out)
    assert out.read_text()=='old result'


def test_cli_missing_arguments():
    result=subprocess.run([sys.executable,str(APPLICANT/'run_aggregate.py')],capture_output=True,text=True)
    assert result.returncode==1

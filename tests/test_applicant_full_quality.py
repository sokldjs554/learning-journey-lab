"""Codex-authored, hand-checkable tests of uploaded SQL and full runner."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / 'evidence/applicant/quality_full.sql'
RUNNER = ROOT / 'evidence/applicant/run_quality_full.py'
SQL = SQL_PATH.read_text()
REVIEWS = ('registration_missing_date', 'event_exact_repeat', 'event_daily_key_repeat',
           'event_before_registration', 'event_after_withdrawal', 'event_after_course')
# Six review rules: five are positive in the actual OULAD snapshot.
BLOCKS = ('event_unknown_student', 'event_required_null', 'event_nonpositive_click',
          'event_unknown_site', 'registration_inverted_dates', 'registration_key_repeat',
          'site_key_repeat', 'course_key_repeat', 'registration_required_null',
          'site_required_null', 'course_required_null', 'course_invalid_length',
          'registration_unknown_course', 'site_unknown_course')
SEVERITIES = {**dict.fromkeys(REVIEWS, 'review'), **dict.fromkeys(BLOCKS, 'block')}
SCHEMAS = {
    'studentRegistration': 'code_module VARCHAR, code_presentation VARCHAR, id_student BIGINT, date_registration BIGINT, date_unregistration BIGINT',
    'studentVle': 'code_module VARCHAR, code_presentation VARCHAR, id_student BIGINT, id_site BIGINT, date BIGINT, sum_click BIGINT',
    'courses': 'code_module VARCHAR, code_presentation VARCHAR, module_presentation_length BIGINT',
    'vle': 'code_module VARCHAR, code_presentation VARCHAR, id_site BIGINT, activity_type VARCHAR',
}
BASE = {
    'studentRegistration': [('AAA','2014J',1,0,None)],
    'studentVle': [('AAA','2014J',1,10,0,1)],
    'courses': [('AAA','2014J',14)],
    'vle': [('AAA','2014J',10,'resource')],
}


def populate(con, overrides):
    for table, schema in SCHEMAS.items():
        con.execute(f'CREATE TABLE {table}({schema})')
        rows = overrides.get(table, BASE[table])
        if rows:
            con.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in rows[0])})', rows)


def query(overrides, positive):
    with duckdb.connect(':memory:') as con:
        populate(con, overrides)
        before = {t: con.execute(f'SELECT * FROM {t}').fetchall() for t in SCHEMAS}
        cursor = con.execute(SQL)
        assert [c[0] for c in cursor.description] == ['rule_id', 'severity', 'issue_count']
        rows = cursor.fetchall()
        assert len(rows) == 20 and dict((r,s) for r,s,n in rows) == SEVERITIES
        assert dict((r,n) for r,s,n in rows) == {r: positive.get(r,0) for r in SEVERITIES}
        assert con.execute(SQL).fetchall() == rows
        assert before == {t: con.execute(f'SELECT * FROM {t}').fetchall() for t in SCHEMAS}


def test_empty_and_healthy():
    query(dict.fromkeys(SCHEMAS, []), {})
    query({}, {})


@pytest.mark.parametrize('day,before,after,outside', [(-1,1,0,0),(0,0,0,0),(6,0,0,0),(7,0,1,0),(13,0,1,0),(14,0,1,1)])
def test_time_boundaries(day,before,after,outside):
    query({'studentRegistration':[('AAA','2014J',1,0,6)],
           'studentVle':[('AAA','2014J',1,10,day,1)]},
          {'event_before_registration':before,'event_after_withdrawal':after,'event_after_course':outside})


def test_null_date_not_imputed():
    query({'studentRegistration':[('AAA','2014J',1,None,None)],
           'studentVle':[('AAA','2014J',1,10,None,1)]},
          {'registration_missing_date':1,'event_required_null':1})


def test_repeated_reference_rows_do_not_multiply_time_counts():
    query({'studentRegistration':[('AAA','2014J',1,0,6)]*3,
           'courses':[('AAA','2014J',14)]*3, 'vle':BASE['vle']*2,
           'studentVle':[('AAA','2014J',1,10,d,1) for d in [-1,7,14]]},
          {'registration_key_repeat':2,'course_key_repeat':2,'site_key_repeat':1,
           'event_before_registration':1,'event_after_withdrawal':2,'event_after_course':1})


def test_exact_and_daily_repeat_have_different_keys():
    query({'studentVle':BASE['studentVle']*3+[('AAA','2014J',1,10,0,2)]},
          {'event_exact_repeat':2,'event_daily_key_repeat':3})


def test_all_null_event_fields_count_rows_not_cells():
    query({'studentVle':[(None,)*6]*2},
          {'event_required_null':2,'event_exact_repeat':1,'event_daily_key_repeat':1})


def test_unknown_student_and_site_count_each_event():
    query({'studentVle':[('AAA','2014J',2,11,0,1)]*2},
          {'event_unknown_student':2,'event_unknown_site':2,'event_exact_repeat':1,'event_daily_key_repeat':1})


@pytest.mark.parametrize('module,term', [('BBB','2014J'),('AAA','2014B')])
def test_relations_use_full_composite_key(module,term):
    query({'studentVle':[(module,term,1,10,20,1)]},
          {'event_unknown_student':1,'event_unknown_site':1})


@pytest.mark.parametrize('clicks',[0,-1])
def test_nonpositive_clicks(clicks):
    query({'studentVle':[('AAA','2014J',1,10,0,clicks)]},{'event_nonpositive_click':1})


@pytest.mark.parametrize('length',[None,0,-1])
def test_invalid_course_lengths(length):
    query({'courses':[('AAA','2014J',length)],'studentVle':[]},{'course_invalid_length':1})


def test_required_dimension_nulls_and_repeat_null_keys():
    query({'studentRegistration':[(None,None,None,None,None)]*2,
           'vle':[(None,None,None,None)]*2, 'courses':[(None,None,None)]*2,'studentVle':[]},
          {'registration_required_null':2,'registration_missing_date':2,'registration_key_repeat':1,
           'site_required_null':2,'site_key_repeat':1,'course_required_null':2,
           'course_invalid_length':2,'course_key_repeat':1})


def test_unknown_courses_without_missing_keys():
    query({'courses':[],'studentVle':[]},{'registration_unknown_course':1,'site_unknown_course':1})


@pytest.mark.parametrize('registered,withdrawn,count',[(7,6,1),(6,6,0),(None,6,0),(6,None,0)])
def test_registration_date_order(registered,withdrawn,count):
    query({'studentRegistration':[('AAA','2014J',1,registered,withdrawn)],'studentVle':[]},
          {'registration_inverted_dates':count,'registration_missing_date':int(registered is None)})


def runner_module():
    spec=importlib.util.spec_from_file_location('submitted_full_quality', RUNNER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def valid_rows():
    return [(r,s,0) for r,s in SEVERITIES.items()]


@pytest.mark.parametrize('mutation',['missing','extra','duplicate','unknown','wrong_severity','null_severity','negative','null','boolean','decimal','string','null_rule'])
def test_runner_rejects_invalid_contract(mutation):
    module=runner_module(); rows=valid_rows()
    r,s,n=rows[0]
    if mutation=='missing': rows.pop()
    elif mutation=='extra': rows.append(('extra','block',0))
    elif mutation=='duplicate':rows[1]=rows[0]
    elif mutation=='unknown':rows[0]=('unknown',s,n)
    elif mutation=='wrong_severity':rows[0]=(r,'block',n)
    elif mutation=='null_severity':rows[0]=(r,None,n)
    elif mutation=='null_rule':rows[0]=(None,s,n)
    else:
        value={'negative':-1,'null':None,'boolean':False,'decimal':0.5,'string':'0'}[mutation]
        rows[0]=(r,s,value)
    with pytest.raises(module.QualityRunError):
        module.validate_results([(c,) for c in ['rule_id','severity','issue_count']],rows)


def test_runner_normalizes_order_and_rejects_columns():
    module=runner_module(); description=[(c,) for c in ['rule_id','severity','issue_count']]
    assert module.validate_results(description,valid_rows())==module.validate_results(description,list(reversed(valid_rows())))
    with pytest.raises(module.QualityRunError):module.validate_results([('rule_id',),('issue_count',)],valid_rows())


@pytest.fixture
def paths(tmp_path):
    db=tmp_path/'in.duckdb';sql=tmp_path/'quality.sql';output=tmp_path/'result.json'
    with duckdb.connect(str(db)) as con:populate(con,{})
    sql.write_bytes(SQL_PATH.read_bytes())
    return db,sql,output


def invoke(paths):
    db,sql,out=paths
    snapshots={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in [db,sql] if p.is_file()}
    result=subprocess.run([sys.executable,str(RUNNER),'--db',str(db),'--sql',str(sql),'--output',str(out)],capture_output=True,text=True,timeout=30)
    assert snapshots=={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in snapshots}
    assert not list(out.parent.glob('.quality-full-*.tmp'))
    return result


@pytest.mark.parametrize('mode,gate,code',[('healthy','PASS',0),('review','REVIEW',0),('block','BLOCK',2)])
def test_runner_cli_gate_save_and_repeat(paths,mode,gate,code):
    db,sql,out=paths
    with duckdb.connect(str(db)) as con:
        if mode in ('review','block'):con.execute('UPDATE studentRegistration SET date_registration=NULL')
        if mode=='block':con.execute('UPDATE studentVle SET id_student=9')
    assert invoke(paths).returncode==code
    report=json.loads(out.read_text());assert report['scope']=='full_quality_20' and report['gate']==gate
    assert len(report['checks'])==20
    before=out.read_bytes();assert invoke(paths).returncode==code;assert out.read_bytes()==before


@pytest.mark.parametrize('failure',['missing_db','missing_sql','empty_sql','write_sql','severity_swap','bad_output'])
def test_cli_errors_preserve_inputs_and_old_report(paths,failure):
    db,sql,out=paths
    out.write_text('{"old_report":true}');before=(out.read_bytes(),out.stat().st_mtime_ns)
    if failure=='missing_db':db.unlink()
    elif failure=='missing_sql':sql.unlink()
    elif failure=='empty_sql':sql.write_text('')
    elif failure=='write_sql':sql.write_text('DELETE FROM studentVle')
    elif failure=='severity_swap':
        sql.write_text(SQL.replace("'event_required_null', 'block'", "'event_required_null', 'review'"))
    else:
        out.unlink();out.mkdir();before=None
    result=invoke(paths);assert result.returncode==1 and 'ERROR:' in result.stderr
    if before is not None:assert (out.read_bytes(),out.stat().st_mtime_ns)==before
    else:assert out.is_dir()
    if failure=='missing_db':assert not db.exists()


@pytest.mark.parametrize('target',['db','sql','symlink'])
def test_output_aliases_are_rejected(paths,target,tmp_path):
    db,sql,out=paths
    out=db if target=='db' else sql
    if target=='symlink':out=tmp_path/'alias';out.symlink_to(db)
    assert invoke((db,sql,out)).returncode==1


def test_cli_argument_error_not_block():
    result=subprocess.run([sys.executable,str(RUNNER)],capture_output=True,text=True)
    assert result.returncode==1

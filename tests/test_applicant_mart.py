"""Codex-authored checks of unchanged applicant mart submissions."""
import csv
import importlib.util
from pathlib import Path
import subprocess
import sys

import duckdb
import pytest
from test_applicant_full_quality import populate

ROOT = Path(__file__).resolve().parents[1]
APPLICANT = ROOT / 'evidence/applicant'
SQL = (APPLICANT / 'build_mart.sql').read_text()
COLUMNS = ['code_module','code_presentation','id_student','w1_days','w2_active',
           'later_active','first_day','date_unregistration','first_content',
           'first_clicks_raw','first_clicks_exact','first_clicks_max']


def setup(con, overrides=None):
    data = {'courses':[('AAA','2014J',28)]}
    data.update(overrides or {})
    populate(con, data)


def query(overrides=None, strict=False):
    with duckdb.connect() as con:
        setup(con, overrides)
        result = con.execute(SQL, {'strict':strict})
        assert [d[0] for d in result.description] == COLUMNS
        return result.fetchall()


@pytest.mark.parametrize('day,expected', [(-1,(0,0,0,None)),(0,(1,0,0,0)),
    (6,(1,0,0,6)),(7,(0,1,0,None)),(13,(0,1,0,None)),
    (14,(0,0,1,None)),(27,(0,0,1,None)),(28,(0,0,0,None))])
def test_inclusive_week_boundaries(day, expected):
    row = query({'studentVle':[('AAA','2014J',1,10,day,1)]})[0]
    assert row[3:7] == expected
    if expected[0] == 0: assert row[8:] == (0,0,0,0)


def test_eligibility_no_activity_and_sorted_keys():
    rows = query({'studentRegistration':[
        ('AAA','2014J',8,-5,None), ('AAA','2014J',2,0,0),
        ('AAA','2014J',3,None,None), ('AAA','2014J',4,1,None),
        ('AAA','2014J',5,-5,-1), ('BBB','2014J',6,0,None),
        ('CCC','2014J',7,0,None)],
        'courses':[('AAA','2014J',28),('BBB','2014J',27)], 'studentVle':[]})
    assert rows == [('AAA','2014J',2,0,0,0,None,0,0,0,0,0),
                    ('AAA','2014J',8,0,0,0,None,None,0,0,0,0)]


def test_empty_input():
    assert query(dict.fromkeys(['studentRegistration','courses','vle','studentVle'],[])) == []


def test_repeats_first_day_clicks_per_site_and_content():
    events = [('AAA','2014J',1,10,2,n) for n in (4,4,2)]
    events += [('AAA','2014J',1,11,2,4), ('AAA','2014J',1,10,6,100)]
    row = query({'studentVle':events,'vle':[('AAA','2014J',10,'forum'),('AAA','2014J',11,'page')]})[0]
    assert row[3:] == (2,0,0,2,None,1,14,10,8)


@pytest.mark.parametrize('kind,content', [('oucontent',1),('resource',1),('subpage',1),('page',1),('forum',0),(None,0)])
def test_first_content_types(kind, content):
    assert query({'vle':[('AAA','2014J',10,kind)]})[0][8] == content


def test_full_composite_keys_positive_clicks_and_first_day_only():
    # Same site/student IDs in another presentation or module must not leak in.
    events = [('BBB','2014J',1,10,0,9),('AAA','2013J',1,10,0,9),
              ('AAA','2014J',2,10,0,9),('AAA','2014J',1,99,0,9),
              ('AAA','2014J',1,10,0,0),('AAA','2014J',1,10,0,-1),
              ('AAA','2014J',1,10,0,None),('AAA','2014J',1,10,None,9),
              ('AAA','2014J',1,10,1,3),('AAA','2014J',1,11,2,7)]
    row = query({'studentVle':events,'vle':[('AAA','2014J',10,'forum'),
         ('AAA','2014J',11,'resource'),('BBB','2014J',99,'resource')]})[0]
    assert row[3:] == (2,0,0,1,None,0,3,3,3)


def test_strict_filters_activity_not_denominator_includes_withdrawal_day():
    data = {'studentRegistration':[('AAA','2014J',1,-2,6),('AAA','2014J',2,0,0)],
       'studentVle':[('AAA','2014J',1,10,d,1) for d in [0,6,7,14]]+
                    [('AAA','2014J',2,10,1,1)]}
    base, strict = query(data), query(data,True)
    assert [r[:3] for r in base] == [r[:3] for r in strict]
    assert base[0][3:7] == (2,1,1,0)
    assert strict[0][3:7] == (2,0,0,0)
    assert base[1][3] == 1 and strict[1][3:] == (0,0,0,None,0,0,0,0,0)


@pytest.fixture
def files(tmp_path):
    db = tmp_path/'data.duckdb'
    with duckdb.connect(str(db)) as con: setup(con)
    quality, mart = tmp_path/'quality.sql', tmp_path/'mart.sql'
    quality.write_bytes((APPLICANT/'quality_full.sql').read_bytes())
    mart.write_text(SQL)
    return db, quality, mart, tmp_path/'mart.csv'


def invoke(files, strict=False):
    db,quality,mart,out = files
    before = {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in files[:3] if p.is_file()}
    result = subprocess.run([sys.executable,str(APPLICANT/'build_mart.py'),
        '--db',str(db),'--quality-sql',str(quality),'--mart-sql',str(mart),'--output',str(out)]
        + (['--strict'] if strict else []),capture_output=True,text=True,timeout=30)
    assert before == {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in before}
    assert not list(out.parent.glob('.mart-*.csv.tmp'))
    return result


@pytest.mark.parametrize('strict',[False,True])
def test_cli_review_repeat_and_strict_binding(files,strict):
    db,quality,mart,out = files
    with duckdb.connect(str(db)) as con:
        con.execute('UPDATE studentRegistration SET date_unregistration=0')
        con.execute('INSERT INTO studentVle VALUES (\'AAA\',\'2014J\',1,10,7,1)')
    result = invoke(files,strict)
    assert result.returncode == 0 and 'quality_gate=REVIEW' in result.stdout
    assert f'strict={strict}' in result.stdout
    rows = list(csv.reader(out.open()))
    assert rows[0] == COLUMNS and len(rows) == 2
    assert rows[1][4] == ('0' if strict else '1')
    assert 'eligible_enrollments=1' in result.stdout
    first = out.read_bytes()
    assert invoke(files,strict).returncode == 0 and out.read_bytes() == first


def test_cli_pass(files):
    result = invoke(files)
    assert result.returncode == 0 and 'quality_gate=PASS' in result.stdout


@pytest.mark.parametrize('keep_old',[False,True])
@pytest.mark.parametrize('table',['courses','studentRegistration','vle'])
def test_fresh_block_stops_before_bad_mart_and_preserves_output(files,keep_old,table):
    db,quality,mart,out = files
    # First run succeeds. A later dimension duplicate must block even with stale output.
    assert invoke(files).returncode == 0
    old = out.read_bytes()
    if not keep_old: out.unlink()
    with duckdb.connect(str(db)) as con: con.execute(f'INSERT INTO {table} SELECT * FROM {table}')
    mart.write_text('not valid SQL')
    result = invoke(files)
    assert result.returncode == 2 and 'quality_gate=BLOCK' in result.stdout
    assert out.read_bytes() == old if keep_old else not out.exists()


@pytest.mark.parametrize('failure',['missing_db','missing_quality','missing_mart','empty_sql','invalid_sql',
    'write_sql','bad_quality_contract','bad_columns','bad_output'])
def test_errors_preserve_old_csv_and_inputs(files,failure):
    db,quality,mart,out = files
    out.write_text('old result')
    if failure=='missing_db': db.unlink()
    elif failure=='missing_quality': quality.unlink()
    elif failure=='missing_mart': mart.unlink()
    elif failure=='empty_sql': mart.write_text('')
    elif failure=='invalid_sql': mart.write_text('not SQL')
    elif failure=='write_sql': mart.write_text('DELETE FROM studentRegistration WHERE $strict OR NOT $strict')
    elif failure=='bad_quality_contract': quality.write_text('SELECT 0 AS issue_count')
    elif failure=='bad_columns': mart.write_text('SELECT $strict AS wrong_column')
    elif failure=='bad_output': out.unlink(); out.mkdir()
    result = invoke(files)
    assert result.returncode == 1 and 'ERROR:' in result.stderr
    assert out.is_dir() if failure=='bad_output' else out.read_text() == 'old result'
    if failure=='missing_db': assert not db.exists()


@pytest.mark.parametrize('target',[0,1,2,'symlink'])
def test_output_input_aliases(files,target,tmp_path):
    out = files[target] if isinstance(target,int) else tmp_path/'alias'
    if target=='symlink': out.symlink_to(files[0])
    assert invoke((*files[:3],out)).returncode == 1


def test_invalid_result_row_cleans_partial_csv(files):
    db,quality,mart,out = files
    out.write_text('old result')
    # Duplicate a valid SELECT: column shape is valid, second row violates key uniqueness.
    original = SQL.rstrip().rstrip(';')
    mart.write_text(f'SELECT * FROM ({original}) UNION ALL SELECT * FROM ({original})')
    result = invoke(files)
    assert result.returncode == 1 and out.read_text() == 'old result'


def test_cli_missing_arguments():
    result = subprocess.run([sys.executable,str(APPLICANT/'build_mart.py')],capture_output=True,text=True)
    assert result.returncode == 1

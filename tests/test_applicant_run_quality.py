"""Codex-written behavior checks for the unchanged applicant runner."""
import json
from pathlib import Path
import subprocess
import sys

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'evidence/applicant/run_quality.py'
QUALITY_SQL = ROOT / 'evidence/applicant/quality.sql'
RULES = ('registration_missing_date', 'event_exact_repeat', 'event_unknown_student')


@pytest.fixture
def inputs(tmp_path):
    db = tmp_path / 'input.duckdb'
    with duckdb.connect(str(db)) as con:
        con.execute('CREATE TABLE studentRegistration(code_module VARCHAR, code_presentation VARCHAR, id_student BIGINT, date_registration BIGINT)')
        con.execute('CREATE TABLE studentVle(code_module VARCHAR, code_presentation VARCHAR, id_student BIGINT, id_site BIGINT, date BIGINT, sum_click BIGINT)')
    sql = tmp_path / 'quality.sql'
    sql.write_bytes(QUALITY_SQL.read_bytes())
    return db, sql, tmp_path / 'output' / 'result.json'


def invoke(inputs):
    db, sql, output = inputs
    paths = [p for p in [db, sql] if p.is_file()]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    result = subprocess.run([sys.executable, str(SCRIPT), '--db', str(db), '--sql', str(sql),
                             '--output', str(output)], capture_output=True, text=True, timeout=30)
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    assert not list(output.parent.glob('.quality-*.tmp'))
    return result


@pytest.mark.parametrize('scenario,expected_counts,gate,code', [
    ('empty', (0, 0, 0), 'PASS', 0),
    ('date', (1, 0, 0), 'REVIEW', 0),
    ('repeat', (0, 1, 0), 'REVIEW', 0),
    ('unknown', (0, 0, 1), 'BLOCK', 2),
    ('both', (1, 1, 2), 'BLOCK', 2),
])
def test_real_sql_gate_and_exit_contract(inputs, scenario, expected_counts, gate, code):
    db, _, output = inputs
    with duckdb.connect(str(db)) as con:
        if scenario == 'date':
            con.execute("INSERT INTO studentRegistration VALUES ('AAA','2014J',1,NULL)")
        elif scenario == 'repeat':
            con.execute("INSERT INTO studentRegistration VALUES ('AAA','2014J',1,0)")
            con.execute("INSERT INTO studentVle VALUES ('AAA','2014J',1,10,0,2),('AAA','2014J',1,10,0,2)")
        elif scenario == 'unknown':
            con.execute("INSERT INTO studentVle VALUES ('AAA','2014J',1,10,0,2)")
        elif scenario == 'both':
            con.execute("INSERT INTO studentRegistration VALUES ('AAA','2014J',2,NULL)")
            con.execute("INSERT INTO studentVle VALUES ('AAA','2014J',1,10,0,2),('AAA','2014J',1,10,0,2)")
    result = invoke(inputs)
    assert result.returncode == code, result.stderr
    report = json.loads(output.read_text())
    assert report == {'scope': 'first_three_rules', 'gate': gate,
                      'checks': [{'rule_id': name, 'issue_count': count}
                                 for name, count in zip(RULES, expected_counts)]}
    assert f'gate={gate}' in result.stdout
    before = output.read_bytes()
    assert invoke(inputs).returncode == code
    assert output.read_bytes() == before


@pytest.mark.parametrize('bad_sql', [
    "SELECT 'registration_missing_date' AS rule_id, 0 AS wrong_column",
    "SELECT 'registration_missing_date' AS rule_id, 0 AS issue_count",
    "SELECT * FROM (VALUES ('registration_missing_date',0),('registration_missing_date',0),('event_unknown_student',0)) AS t(rule_id,issue_count)",
    "SELECT * FROM (VALUES ('registration_missing_date',0),('event_exact_repeat',0),('unexpected',0)) AS t(rule_id,issue_count)",
    *[f"SELECT * FROM (VALUES ('registration_missing_date',{value}),('event_exact_repeat',0),('event_unknown_student',0)) AS t(rule_id,issue_count)"
      for value in ('-1', 'NULL', '0.5', "'zero'")],
    "SELECT * FROM (VALUES ('registration_missing_date',false),('event_exact_repeat',false),('event_unknown_student',false)) AS t(rule_id,issue_count)",
    "SELECT NULL AS rule_id, 0 AS issue_count UNION ALL SELECT 'event_exact_repeat',0 UNION ALL SELECT 'event_unknown_student',0",
    'SELECT * FROM table_that_does_not_exist',
    '',
    'DELETE FROM studentRegistration',
])
def test_bad_sql_or_result_does_not_replace_report(inputs, bad_sql):
    _, sql, output = inputs
    sql.write_text(bad_sql)
    output.parent.mkdir()
    output.write_text('{"old_report": true}')
    old = (output.read_bytes(), output.stat().st_mtime_ns)
    result = invoke(inputs)
    assert result.returncode == 1
    assert 'ERROR:' in result.stderr
    assert 'JSON 저장:' not in result.stdout
    assert (output.read_bytes(), output.stat().st_mtime_ns) == old


@pytest.mark.parametrize('missing', ['db', 'sql'])
def test_missing_input_not_created(inputs, missing):
    target = inputs[0 if missing == 'db' else 1]
    target.unlink()
    result = invoke(inputs)
    assert result.returncode == 1
    assert not target.exists() and not inputs[2].exists()


@pytest.mark.parametrize('target', ['db', 'sql', 'symlink_to_db'])
def test_output_cannot_overwrite_inputs(inputs, target, tmp_path):
    db, sql, _ = inputs
    output = db if target == 'db' else sql
    if target == 'symlink_to_db':
        output = tmp_path / 'alias.duckdb'
        output.symlink_to(db)
    result = invoke((db, sql, output))
    assert result.returncode == 1
    assert '다른 파일' in result.stderr


def test_output_replacement_failure_is_error_and_cleans_temporary_file(inputs):
    db, sql, output = inputs
    output.mkdir(parents=True)
    result = invoke(inputs)
    assert result.returncode == 1
    assert output.is_dir()
    assert 'JSON 저장:' not in result.stdout


def test_missing_arguments_are_error_one_not_block_two():
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 1 and '인자 오류' in result.stderr

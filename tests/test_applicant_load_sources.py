"""Codex-written review of the uploaded loader, without changing its code."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import duckdb
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'evidence/applicant/load_sources.py'
NAMES = ('assessments', 'courses', 'studentAssessment', 'studentInfo',
         'studentRegistration', 'studentVle', 'vle')


@pytest.fixture
def inputs(tmp_path):
    raw = tmp_path / "raw folder's name"
    raw.mkdir()
    for name in NAMES:
        (raw / f'{name}.csv').write_bytes(b'id,value\n1,10\n2,?\n3,\n')
    manifest = tmp_path / 'manifest.json'
    rewrite_manifest(raw, manifest)
    return manifest, raw, tmp_path / "output's database.duckdb"


def rewrite_manifest(raw, manifest):
    manifest.write_text(json.dumps({'files': {
        f'{name}.csv': {'sha256': hashlib.sha256((raw / f'{name}.csv').read_bytes()).hexdigest(),
                       'bytes': (raw / f'{name}.csv').stat().st_size}
        for name in NAMES
    }}))


def invoke(inputs):
    manifest, raw, database = inputs
    paths = [manifest] + [p for p in raw.glob('*.csv') if p.is_file()]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    result = subprocess.run([sys.executable, str(SCRIPT), '--manifest', str(manifest),
                             '--csv-dir', str(raw), '--db', str(database)],
                            capture_output=True, text=True, timeout=60)
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    return result


def test_all_tables_rows_and_nulls(inputs):
    result = invoke(inputs)
    assert result.returncode == 0, result.stderr
    assert '총 7개 테이블 적재 성공' in result.stdout
    with duckdb.connect(str(inputs[2]), read_only=True) as connection:
        assert {r[0] for r in connection.execute('SHOW TABLES').fetchall()} == set(NAMES)
        for name in NAMES:
            assert f'{name}: 3행' in result.stdout
            assert connection.execute(f'SELECT * FROM "{name}" ORDER BY id').fetchall() == [
                (1, 10), (2, None), (3, None)]


@pytest.mark.parametrize('existing_database', [False, True])
@pytest.mark.parametrize('failure', ['missing_csv', 'hash_mismatch', 'invalid_manifest'])
def test_validation_failure_never_opens_database(inputs, existing_database, failure):
    manifest, raw, database = inputs
    if existing_database:
        with duckdb.connect(str(database)) as connection:
            connection.execute('CREATE TABLE keep AS SELECT 42 AS answer')
        before = (database.read_bytes(), database.stat().st_mtime_ns)
    if failure == 'missing_csv':
        (raw / 'courses.csv').unlink()
    elif failure == 'hash_mismatch':
        (raw / 'courses.csv').write_bytes(b'id,value\n1,20\n2,?\n3,\n')
    else:
        manifest.write_text('{broken')
    result = invoke(inputs)
    assert result.returncode == (2 if failure == 'invalid_manifest' else 1)
    assert 'DuckDB 적재 완료' not in result.stdout
    if existing_database:
        assert (database.read_bytes(), database.stat().st_mtime_ns) == before
    else:
        assert not database.exists()


def test_repeat_replaces_instead_of_appending_and_preserves_unrelated_table(inputs):
    assert invoke(inputs).returncode == 0
    with duckdb.connect(str(inputs[2])) as connection:
        connection.execute('CREATE TABLE keep AS SELECT 42 AS answer')
    assert invoke(inputs).returncode == 0
    with duckdb.connect(str(inputs[2]), read_only=True) as connection:
        for name in NAMES:
            assert connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] == 3
        assert connection.execute('SELECT answer FROM keep').fetchone() == (42,)


@pytest.mark.parametrize('existing_tables', [False, True])
def test_parse_failure_rolls_back_all_table_changes(inputs, existing_tables):
    manifest, raw, database = inputs
    # The last file passes the hash gate but cannot be parsed as UTF-8 CSV.
    (raw / 'vle.csv').write_bytes(b'id,value\n1,\xff\xfe\n')
    rewrite_manifest(raw, manifest)
    if existing_tables:
        with duckdb.connect(str(database)) as connection:
            for name in NAMES:
                connection.execute(f'CREATE TABLE "{name}" AS SELECT 42 AS old_value')
            connection.execute('CREATE TABLE keep AS SELECT 99 AS marker')
    result = invoke(inputs)
    assert result.returncode == 3
    assert '검사 완료: 성공 7건 / 실패 0건' in result.stdout
    assert 'DuckDB 적재 실패' in result.stderr
    assert '총 7개 테이블 적재 성공' not in result.stdout
    with duckdb.connect(str(database), read_only=True) as connection:
        tables = {r[0] for r in connection.execute('SHOW TABLES').fetchall()}
        if existing_tables:
            assert tables == set(NAMES) | {'keep'}
            for name in NAMES:
                assert connection.execute(f'SELECT old_value FROM "{name}"').fetchall() == [(42,)]
            assert connection.execute('SELECT marker FROM keep').fetchone() == (99,)
        else:
            assert tables == set()


def test_connection_failure_reports_nonzero(inputs, tmp_path):
    result = invoke((inputs[0], inputs[1], tmp_path / 'no-parent' / 'out.duckdb'))
    assert result.returncode == 3
    assert 'DuckDB 적재 실패' in result.stderr
    assert '적재 성공' not in result.stdout

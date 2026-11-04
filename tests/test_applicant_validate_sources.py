"""Codex review cases for the unchanged applicant submission; synthetic inputs only."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'evidence/applicant/validate_sources.py'
NAMES = ('assessments.csv', 'courses.csv', 'studentAssessment.csv',
         'studentInfo.csv', 'studentRegistration.csv', 'studentVle.csv', 'vle.csv')
# Published SHA-256 test vector for the three bytes b'abc'.
ABC_SHA256 = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'


@pytest.fixture
def inputs(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    for name in NAMES:
        (raw / name).write_bytes(b'abc')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'files': {
        name: {'sha256': ABC_SHA256, 'bytes': 3} for name in NAMES
    }}))
    return manifest, raw


def invoke(inputs):
    manifest, raw = inputs
    # Observe both file bytes and metadata before and after every subprocess.
    paths = [manifest] + [p for p in raw.glob('*') if p.is_file()]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    result = subprocess.run([sys.executable, str(SCRIPT), '--manifest', str(manifest),
                             '--csv-dir', str(raw)], capture_output=True, text=True)
    assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
    return result


def test_seven_valid_files(inputs):
    result = invoke(inputs)
    assert result.returncode == 0
    assert result.stdout.count('OK   ') == 7
    assert '성공 7건 / 실패 0건' in result.stdout


def test_missing_csv(inputs):
    (inputs[1] / 'courses.csv').unlink()
    result = invoke(inputs)
    assert result.returncode == 1
    assert 'FAIL courses.csv: 파일이 없습니다' in result.stdout
    assert '성공 6건 / 실패 1건' in result.stdout


def test_same_size_corruption(inputs):
    (inputs[1] / 'courses.csv').write_bytes(b'abd')
    result = invoke(inputs)
    assert result.returncode == 1
    assert 'FAIL courses.csv: SHA-256 불일치' in result.stdout
    assert '크기 불일치' not in result.stdout


def test_wrong_declared_size(inputs):
    manifest, _ = inputs
    data = json.loads(manifest.read_text())
    data['files']['courses.csv']['bytes'] = 4
    manifest.write_text(json.dumps(data))
    result = invoke(inputs)
    assert result.returncode == 1
    assert '크기 불일치' in result.stdout and 'SHA-256 불일치' not in result.stdout


def test_csv_path_is_directory(inputs):
    path = inputs[1] / 'courses.csv'
    path.unlink()
    path.mkdir()
    result = invoke(inputs)
    assert result.returncode == 1
    assert 'FAIL courses.csv: 일반 파일이 아닙니다' in result.stdout


def test_missing_raw_directory(inputs, tmp_path):
    result = invoke((inputs[0], tmp_path / 'not-present'))
    assert result.returncode == 1
    assert '폴더가 없거나 디렉터리가 아닙니다' in result.stderr


@pytest.mark.parametrize('mutation', ['missing_file', 'extra_file', 'bad_sha', 'boolean_size', 'negative_size', 'no_files'])
def test_invalid_manifest_contract(inputs, mutation):
    manifest, _ = inputs
    data = json.loads(manifest.read_text())
    if mutation == 'missing_file':
        del data['files']['courses.csv']
    elif mutation == 'extra_file':
        data['files']['extra.csv'] = {'sha256': ABC_SHA256, 'bytes': 3}
    elif mutation == 'bad_sha':
        data['files']['courses.csv']['sha256'] = 'invalid'
    elif mutation == 'boolean_size':
        data['files']['courses.csv']['bytes'] = True
    elif mutation == 'negative_size':
        data['files']['courses.csv']['bytes'] = -1
    elif mutation == 'no_files':
        data = []
    manifest.write_text(json.dumps(data))
    result = invoke(inputs)
    assert result.returncode == 2
    assert 'manifest 읽기/형식 오류' in result.stderr
    assert 'OK   ' not in result.stdout


def test_malformed_json(inputs):
    inputs[0].write_text('{broken')
    result = invoke(inputs)
    assert result.returncode == 2
    assert 'manifest 읽기/형식 오류' in result.stderr


def test_uppercase_sha_is_accepted(inputs):
    manifest, _ = inputs
    data = json.loads(manifest.read_text())
    for entry in data['files'].values():
        entry['sha256'] = entry['sha256'].upper()
    manifest.write_text(json.dumps(data))
    assert invoke(inputs).returncode == 0


def test_bounded_reads():
    spec = importlib.util.spec_from_file_location('submitted_source_validator', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class Reader:
        def __init__(self):
            self.requests = []
            self.parts = iter([b'a', b'b', b'c', b''])
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size=-1):
            self.requests.append(size)
            assert 0 < size <= 1024 * 1024
            return next(self.parts)
    reader = Reader()
    class Source:
        def open(self, mode):
            assert mode == 'rb'
            return reader
    assert module.hash_file(Source()) == (ABC_SHA256, 3)
    assert len(reader.requests) == 4

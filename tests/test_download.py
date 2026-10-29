import hashlib
import io
import zipfile
import pytest
from scripts import download


def archive(name='courses.csv', body=b'a,b\n1,2\n'):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        z.writestr(name, body)
    return b.getvalue()


def test_hash_mismatch_never_extracts(tmp_path):
    p=tmp_path/'x.zip'; p.write_bytes(archive())
    with pytest.raises(ValueError, match='SHA256'):
        download.extract_verified(p, tmp_path/'raw', '0'*64)
    assert not (tmp_path/'raw').exists()


def test_path_escape_rejected(tmp_path):
    p=tmp_path/'x.zip'; p.write_bytes(archive('../escape'))
    with pytest.raises(ValueError, match='path'):
        download.extract_verified(p,tmp_path/'raw',hashlib.sha256(p.read_bytes()).hexdigest())
    assert not (tmp_path/'escape').exists()


def test_existing_conflicting_file_not_overwritten(tmp_path):
    p=tmp_path/'x.zip'; p.write_bytes(archive())
    d=tmp_path/'raw'; d.mkdir(); (d/'courses.csv').write_text('keep')
    with pytest.raises(ValueError, match='existing'):
        download.extract_verified(p,d,hashlib.sha256(p.read_bytes()).hexdigest())
    assert (d/'courses.csv').read_text()=='keep'

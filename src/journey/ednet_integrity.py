"""Pinned EdNet snapshot verification shared by download and analysis.

Operational timestamps and transfer counts stay in local audit manifests. Public
aggregate metadata uses an allowlist and contains no source-user filenames.
"""
import hashlib
import json
from pathlib import Path
import re
import zlib

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[2] / 'data' / 'ednet_snapshot.json'
PIN_KEYS = (
    'dataset', 'seed', 'sample_users', 'archive_bytes', 'population_user_files',
    'zip_index_sha256', 'selected_members_sha256', 'sample_content_sha256',
    'sample_uncompressed_bytes', 'contents_zip_bytes', 'contents_zip_sha256',
)
PUBLIC_KEYS = PIN_KEYS + (
    'source', 'source_archive_url', 'contents_archive_url', 'license',
    'archive_sha256', 'archive_sha256_note', 'sampling',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def public_manifest(manifest):
    manifest = dict(manifest)
    # Original cached download predates the explicit index field. Its largest
    # recorded request is the 27.7 MB central-directory read (verified by pin).
    if 'zip_index_sha256' not in manifest and manifest.get('range_records'):
        manifest['zip_index_sha256'] = max(
            manifest['range_records'], key=lambda r: r['end'] - r['start'])['sha256']
    return {key: manifest[key] for key in PUBLIC_KEYS if key in manifest}


def read_snapshot(path=DEFAULT_SNAPSHOT):
    snapshot = json.loads(Path(path).read_text())
    missing = set(PIN_KEYS) - set(snapshot)
    if missing:
        raise ValueError(f'published snapshot missing required fields: {sorted(missing)}')
    return snapshot


def assert_snapshot(manifest, expected):
    for key in PIN_KEYS:
        if manifest.get(key) != expected[key]:
            raise ValueError(f'published snapshot mismatch: {key}')


def verify_cache(raw_dir, expected_manifest=DEFAULT_SNAPSHOT):
    raw_dir = Path(raw_dir)
    expected = read_snapshot(expected_manifest)
    local_path = raw_dir / 'download_manifest.local.json'
    public_path = raw_dir / 'download_manifest.json'
    if not local_path.is_file() or not public_path.is_file():
        raise ValueError('incomplete existing cache; preserve it and use a new empty output directory')
    local = json.loads(local_path.read_text())
    public = json.loads(public_path.read_text())
    stable = public_manifest(local)
    assert_snapshot(stable, expected)
    # Older public cache manifests have no explicit ZIP-index key; the local
    # audit range above must still agree with the checked-in index fingerprint.
    for key in PIN_KEYS:
        if key == 'zip_index_sha256' and key not in public:
            continue
        if public.get(key) != expected[key]:
            raise ValueError(f'public cache/published snapshot mismatch: {key}')
    names, records = [], []
    for record in local.get('member_records', []):
        name = record['member']
        if not re.fullmatch(r'KT4/u[0-9]+\.csv', name):
            raise ValueError('invalid cache member path')
        path = raw_dir / Path(name).name
        if not path.is_file():
            raise ValueError('incomplete cache: selected member missing')
        blob = path.read_bytes()
        actual = {'member': name, 'sha256': digest(blob), 'bytes': len(blob),
                  'crc32': f'{zlib.crc32(blob):08x}'}
        if actual != record:
            raise ValueError('cached member checksum/size/CRC mismatch; refusing overwrite')
        names.append(name)
        records.append(actual)
    if len(names) != len(set(names)) or len(names) != expected['sample_users']:
        raise ValueError('cache sample count or duplicate member mismatch')
    selected_hash = digest(('\n'.join(sorted(names)) + '\n').encode())
    content_hash = digest(json.dumps(sorted(records, key=lambda r:r['member']),
                                    sort_keys=True, separators=(',', ':')).encode())
    if selected_hash != expected['selected_members_sha256']:
        raise ValueError('published snapshot mismatch: selected_members_sha256')
    if content_hash != expected['sample_content_sha256']:
        raise ValueError('published snapshot mismatch: sample_content_sha256')
    if sum(r['bytes'] for r in records) != expected['sample_uncompressed_bytes']:
        raise ValueError('published snapshot mismatch: sample_uncompressed_bytes')
    contents = raw_dir / 'contents.zip'
    if not contents.is_file():
        raise ValueError('incomplete cache: contents archive missing')
    blob = contents.read_bytes()
    if len(blob) != expected['contents_zip_bytes'] or digest(blob) != expected['contents_zip_sha256']:
        raise ValueError('contents archive checksum/size mismatch against published snapshot')
    return stable

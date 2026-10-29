import io
import zipfile
import pytest
from scripts import download_ednet as d


def fixture_zip():
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('KT4/', '')
        z.writestr('KT4/u1.csv', 'timestamp,action_type\n1,enter\n')
        z.writestr('KT4/u2.csv', 'timestamp,action_type\n2,pay\n')
        z.writestr('../escape.csv', 'bad')
    return out.getvalue()


def test_selection_uses_filename_only_is_order_invariant():
    names = ['KT4/u1.csv', 'KT4/u2.csv', '../escape.csv', 'KT4/']
    assert d.select_members(names, 1, 'seed') == d.select_members(names[::-1], 1, 'seed')
    assert set(d.select_members(names, 2, 'seed')) == {'KT4/u1.csv', 'KT4/u2.csv'}
    with pytest.raises(ValueError):
        d.select_members(names, 3, 'seed')


def test_range_zip_recovers_exact_csv_and_checks_crc():
    blob = fixture_zip()
    fetch = lambda start, end: blob[start:end + 1]
    infos = d.read_index(fetch, len(blob))
    info = next(i for i in infos if i.filename == 'KT4/u1.csv')
    chunk = blob[info.header_offset:info.header_offset + 30 + len(info.filename.encode()) + len(info.extra) + info.compress_size + 1024]
    assert d.extract_member(info, chunk) == b'timestamp,action_type\n1,enter\n'
    info.CRC ^= 1
    with pytest.raises(ValueError, match='CRC'):
        d.extract_member(info, chunk)


def test_group_ranges_do_not_drop_or_overlap_members():
    blob = fixture_zip()
    infos = [i for i in d.read_index(lambda s,e: blob[s:e+1], len(blob)) if i.filename.startswith('KT4/u')]
    groups = d.group_ranges(infos, len(blob))
    assert sorted(i.filename for _, _, members in groups for i in members) == ['KT4/u1.csv', 'KT4/u2.csv']
    for start, end, members in groups:
        for info in members:
            raw = d.extract_member(info, blob[info.header_offset:end+1])
            assert raw.startswith(b'timestamp')


def pinned_cache(tmp_path):
    import json, zlib
    raw = b'timestamp,action_type\n1,enter\n'
    record = {'member': 'KT4/u1.csv', 'sha256': d.digest(raw), 'bytes': len(raw), 'crc32': f'{zlib.crc32(raw):08x}'}
    contents = b'fixture catalog bytes'
    manifest = {'dataset': 'EdNet-KT4', 'seed': d.SEED, 'sample_users': 1,
        'archive_bytes': 1000, 'population_user_files': 10, 'zip_index_sha256': 'a'*64,
        'selected_members_sha256': d.digest(b'KT4/u1.csv\n'),
        'sample_content_sha256': d.digest(json.dumps([record],sort_keys=True,separators=(',',':')).encode()),
        'sample_uncompressed_bytes': len(raw), 'contents_zip_bytes': len(contents),
        'contents_zip_sha256': d.digest(contents), 'retrieved_at_utc': '2020-01-01T00:00:00Z',
        'kt4_transferred_bytes': 2000, 'member_records': [record], 'range_records': []}
    cache = tmp_path / 'raw'; cache.mkdir()
    (cache/'u1.csv').write_bytes(raw); (cache/'contents.zip').write_bytes(contents)
    (cache/'download_manifest.local.json').write_text(json.dumps(manifest))
    public = {k:v for k,v in manifest.items() if k not in ['member_records','range_records']}
    (cache/'download_manifest.json').write_text(json.dumps(public))
    pinned = {k:v for k,v in public.items() if k not in ['retrieved_at_utc','kt4_transferred_bytes']}
    expected = tmp_path/'snapshot.json'; expected.write_text(json.dumps(pinned))
    return cache, expected


def test_verified_cache_reused_without_network(tmp_path, monkeypatch):
    cache, expected = pinned_cache(tmp_path)
    before = {p.name:p.read_bytes() for p in cache.iterdir()}
    def network_forbidden(*args, **kwargs):
        pytest.fail('verified cache must not access network')
    monkeypatch.setattr(d, 'get_range', network_forbidden)
    result = d.download_sample(cache, n=1, expected_manifest=expected)
    assert result['sample_users'] == 1
    assert 'retrieved_at_utc' not in result
    assert {p.name:p.read_bytes() for p in cache.iterdir()} == before


def test_tampered_cache_fails_without_overwriting(tmp_path):
    cache, expected = pinned_cache(tmp_path)
    path = cache/'u1.csv'; path.write_bytes(b'changed original')
    with pytest.raises(ValueError, match='checksum'):
        d.download_sample(cache, n=1, expected_manifest=expected)
    assert path.read_bytes() == b'changed original'


def test_local_self_hash_cannot_override_published_snapshot(tmp_path):
    import json
    cache, expected = pinned_cache(tmp_path)
    pinned = json.loads(expected.read_text()); pinned['sample_content_sha256'] = '0'*64
    expected.write_text(json.dumps(pinned))
    with pytest.raises(ValueError, match='snapshot.*sample_content_sha256'):
        d.download_sample(cache, n=1, expected_manifest=expected)


def test_incomplete_cache_is_never_overwritten(tmp_path):
    cache, expected = pinned_cache(tmp_path)
    (cache/'download_manifest.local.json').unlink()
    with pytest.raises(ValueError, match='incomplete'):
        d.download_sample(cache, n=1, expected_manifest=expected)
    assert (cache/'u1.csv').read_bytes().startswith(b'timestamp')


def test_fresh_download_pins_bytes_and_publishes_only_verified_cache(tmp_path, monkeypatch):
    import json, zlib
    blob = fixture_zip()
    seen = []
    def index_fetch(start, end):
        seen.append(blob[start:end+1])
        return blob[start:end+1]
    infos = d.read_index(index_fetch, len(blob))
    name = d.select_members([i.filename for i in infos], 1)[0]
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        raw = archive.read(name)
    contents_out = io.BytesIO()
    with zipfile.ZipFile(contents_out, 'w') as archive:
        archive.writestr('contents/payments.csv', 'payment_item_id,type,duaration\np1,pass,1000\n')
    contents = contents_out.getvalue()
    record = {'member': name, 'sha256': d.digest(raw), 'bytes': len(raw), 'crc32': f'{zlib.crc32(raw):08x}'}
    expected = {'dataset':'EdNet-KT4','seed':d.SEED,'sample_users':1,'archive_bytes':len(blob),
        'population_user_files':2,'zip_index_sha256':d.digest(max(seen,key=len)),
        'selected_members_sha256':d.digest((name+'\n').encode()),
        'sample_content_sha256':d.digest(json.dumps([record],sort_keys=True,separators=(',',':')).encode()),
        'sample_uncompressed_bytes':len(raw),'contents_zip_bytes':len(contents),'contents_zip_sha256':d.digest(contents)}
    pin=tmp_path/'snapshot.json'; pin.write_text(json.dumps(expected))
    def fetch(url,start,end,size=None):
        source = blob if url == d.KT4_URL else contents
        return source[start:end+1],len(source)
    monkeypatch.setattr(d,'get_range',fetch)
    output = tmp_path/'fresh'
    public = d.download_sample(output,n=1,expected_manifest=pin)
    assert (output/name.split('/')[-1]).read_bytes() == raw
    assert 'retrieved_at_utc' not in public and 'member_records' not in public
    assert 'retrieved_at_utc' in json.loads((output/'download_manifest.local.json').read_text())
    assert name not in (output/'download_manifest.json').read_text()
    expected['sample_content_sha256']='0'*64; pin.write_text(json.dumps(expected))
    rejected = tmp_path/'rejected'
    with pytest.raises(ValueError,match='snapshot.*sample_content_sha256'):
        d.download_sample(rejected,n=1,expected_manifest=pin)
    assert not rejected.exists()  # bad bytes never installed as cache


def test_legacy_and_fresh_cache_manifest_serialize_identically():
    import json
    base={'dataset':'EdNet-KT4','seed':d.SEED,'sample_users':2048,'source':'official',
          'range_records':[{'start':10,'end':100,'sha256':'a'*64}]}
    fresh={**base,'zip_index_sha256':'a'*64,'retrieved_at_utc':'2030-01-01'}
    assert json.dumps(d.public_manifest(base)) == json.dumps(d.public_manifest(fresh))

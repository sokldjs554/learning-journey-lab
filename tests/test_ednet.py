"""Hand-calculated boundaries and malformed-input checks; no network or real IDs."""
from pathlib import Path
import pandas as pd
import pytest
from src.journey import ednet

DAY = 86_400_000


def events_fixture():
    def event(user, t, action='submit', item='b1'):
        return {'user_id': user, 'timestamp': 1000 + t, 'action_type': action,
                'item_id': item, 'cursor_time': '', 'source': 'sprint',
                'user_answer': '', 'platform': 'mobile'}
    rows = [event('u1', 0), event('u1', DAY-1), event('u1', DAY-1),
            event('u1', DAY, 'pay', 'p1'), event('u1', 7*DAY), event('u1', 14*DAY),
            event('u2', 0), event('u2', DAY), event('u2', 14*DAY-1),
            event('u3', 0), event('u3', DAY), event('u3', 14*DAY),
            event('u4', 0, 'pay', 'p1'), event('u4', 7*DAY)]
    return pd.DataFrame(rows)


def test_exact_week_boundaries_and_zero_activity_denominator():
    features = ednet.sql_features(events_fixture()).set_index('user_id')
    assert features.loc['u1', 'w1_submit_days'] == 1
    assert features.loc['u1', 'w2_submit'] == 1
    assert features.loc['u2', 'w1_submit_days'] == 2
    assert features.loc['u2', 'w2_submit'] == 1
    assert features.loc['u3', 'w2_submit'] == 0  # exactly day 14 excluded
    assert features.loc['u4', 'w1_submit_days'] == 0
    result = ednet.compare(features.reset_index(), 'submit', draws=100)
    assert result['eligible_firstweek_users'] == 3
    assert [(g['n'], g['recorded_nextweek']) for g in result['groups']] == [(1, 1), (2, 1)]
    assert result['difference'] == -0.5


def test_independent_pandas_matches_sql_and_duplicate_rows_do_not_add_days():
    events = events_fixture()
    pd.testing.assert_frame_equal(ednet.sql_features(events), ednet.pandas_features(events), check_dtype=False)
    raw = ednet.sql_features(events)
    dedup = ednet.sql_features(events.drop_duplicates())
    for col in ['w1_submit_days', 'w2_submit', 'w1_ui_days', 'w2_ui']:
        assert raw[col].tolist() == dedup[col].tolist()
    assert raw.set_index('user_id').loc['u1', 'w1_ui_days'] == 2


@pytest.mark.parametrize('column,bad', [('timestamp', None), ('timestamp', 'broken'),
    ('timestamp', 1.5), ('user_id', '../u2'), ('action_type', '')])
def test_invalid_required_fields_stop_analysis(column, bad):
    data = events_fixture().astype(object)
    data.loc[0, column] = bad
    with pytest.raises(ValueError):
        ednet.validate_events(data)


def test_empty_sample_stops_and_empty_comparison_is_explicit():
    with pytest.raises(ValueError, match='empty'):
        ednet.validate_events(events_fixture().iloc[:0])
    features = ednet.sql_features(events_fixture())
    result = ednet.compare(features, 'entry', draws=20)
    assert result['eligible_firstweek_users'] == 0
    assert result['difference'] is None
    assert all(g['rate'] is None for g in result['groups'])


def test_payment_unknown_keys_reported_not_invented_as_subscription():
    frame = events_fixture()
    frame.loc[len(frame)] = ['u1', 5000, 'pay', 'p999', '', '', '', 'mobile']
    catalog = pd.DataFrame([{'payment_item_id': 'p1', 'payment_type': 'pass', 'duration': 1000, 'number_of_questions': -1}])
    result = ednet.payment_summary(frame, catalog)
    assert result['pay_events'] == 3
    assert result['paying_users'] == 2
    assert result['unknown_payment_key_events'] == 1
    assert 'revenue' in result['cannot_measure']


def test_actual_official_catalog_typo_is_explicitly_normalized():
    # The downloaded official file uses type and the misspelling duaration.
    catalog = pd.DataFrame([{'payment_item_id': 'p1', 'type': 'pass', 'duaration': 1000, 'number_of_questions': -1}])
    result = ednet.payment_summary(events_fixture(), catalog)
    assert result['pay_events'] == 2
    assert result['unknown_payment_key_events'] == 0
    assert result['catalog_source_fields'] == ['payment_item_id', 'type', 'duaration', 'number_of_questions']


def test_source_payment_null_platform_is_reported_separately_from_invalid_value():
    frame = events_fixture()
    frame.loc[frame.action_type == 'pay', 'platform'] = ''
    frame.loc[0, 'platform'] = 'unexpected-device'
    result = ednet.platform_quality(frame)
    assert result['missing_platform_rows'] == 2
    assert result['missing_platform_by_action'] == {'pay': 2}
    assert result['unknown_nonempty_platform_rows'] == 1


def test_catalog_duplicate_join_keys_stop_instead_of_multiplying_money_events():
    catalog = pd.DataFrame([{'payment_item_id': 'p1', 'payment_type': 'pass', 'duration': 1000}] * 2)
    with pytest.raises(ValueError, match='unique'):
        ednet.payment_summary(events_fixture(), catalog)


def write_raw_fixture(tmp_path, extra_column=False):
    import hashlib, json
    frame = events_fixture().query("user_id == 'u1'").drop(columns='user_id')
    if extra_column:
        frame['unexpected'] = 'do not silently discard schema drift'
    path = tmp_path / 'u1.csv'
    frame.to_csv(path, index=False)
    record = {'member': 'KT4/u1.csv', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (tmp_path / 'download_manifest.local.json').write_text(json.dumps({'sample_users': 1, 'member_records': [record]}))
    return path


def test_raw_tampering_is_detected_before_analysis(tmp_path):
    path = write_raw_fixture(tmp_path)
    assert len(ednet.load_events(tmp_path)) == 6
    path.write_bytes(path.read_bytes() + b'corruption')
    with pytest.raises(ValueError, match='checksum'):
        ednet.load_events(tmp_path)


def test_unexpected_source_column_is_not_silently_dropped(tmp_path):
    write_raw_fixture(tmp_path, extra_column=True)
    with pytest.raises(ValueError, match='schema'):
        ednet.load_events(tmp_path)


def test_catalog_archive_checksum_is_verified(tmp_path):
    import hashlib, io, json, zipfile
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        archive.writestr('contents/payments.csv', 'payment_item_id,type,duaration,number_of_questions\np1,pass,1000,-1\n')
    blob = out.getvalue()
    path = tmp_path / 'contents.zip'
    path.write_bytes(blob)
    (tmp_path / 'download_manifest.json').write_text(json.dumps({'contents_zip_sha256': hashlib.sha256(blob).hexdigest()}))
    assert ednet.load_catalog(tmp_path).iloc[0]['payment_item_id'] == 'p1'
    path.write_bytes(blob + b'changed archive')
    with pytest.raises(ValueError, match='checksum'):
        ednet.load_catalog(tmp_path)


def test_report_bytes_are_independent_of_download_audit_timestamp(tmp_path):
    import hashlib, io, json, zipfile, zlib
    records=[]
    for user, group in events_fixture().groupby('user_id'):
        path=tmp_path/(user+'.csv')
        group.drop(columns='user_id').to_csv(path,index=False)
        blob=path.read_bytes()
        records.append({'member':'KT4/'+path.name,'sha256':hashlib.sha256(blob).hexdigest(),
                        'bytes':len(blob),'crc32':f'{zlib.crc32(blob):08x}'})
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        archive.writestr('contents/payments.csv','payment_item_id,type,duaration,number_of_questions\np1,pass,1000,-1\n')
    contents=out.getvalue(); (tmp_path/'contents.zip').write_bytes(contents)
    digest=lambda value:hashlib.sha256(value).hexdigest()
    expected={'dataset':'EdNet-KT4','seed':'fixture','sample_users':4,'archive_bytes':1000,
        'population_user_files':4,'zip_index_sha256':'a'*64,
        'selected_members_sha256':digest(('\n'.join(r['member'] for r in records)+'\n').encode()),
        'sample_content_sha256':digest(json.dumps(records,sort_keys=True,separators=(',',':')).encode()),
        'sample_uncompressed_bytes':sum(r['bytes'] for r in records),'contents_zip_bytes':len(contents),
        'contents_zip_sha256':digest(contents)}
    pin=tmp_path/'snapshot.json';pin.write_text(json.dumps(expected))
    results=[]
    for timestamp in ['2020-01-01T00:00:00Z','2030-12-31T23:59:59Z']:
        local={**expected,'member_records':records,'retrieved_at_utc':timestamp,'kt4_transferred_bytes':9999}
        (tmp_path/'download_manifest.local.json').write_text(json.dumps(local))
        (tmp_path/'download_manifest.json').write_text(json.dumps({**expected,'retrieved_at_utc':timestamp}))
        results.append(ednet.build_report(tmp_path,expected_manifest=pin))
    assert results[0] == results[1]
    assert 'retrieved_at_utc' not in results[0]['manifest']
    assert 'kt4_transferred_bytes' not in results[0]['manifest']

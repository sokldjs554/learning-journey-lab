"""Supplementary EdNet observational analysis; never mutates the OULAD pipeline."""
from __future__ import annotations
import argparse
import hashlib
import json
import io
import zipfile
from pathlib import Path
import re
import duckdb
import numpy as np
import pandas as pd
from .ednet_integrity import DEFAULT_SNAPSHOT, verify_cache

DAY = 86_400_000
COLUMNS = ['user_id', 'timestamp', 'action_type', 'item_id', 'cursor_time', 'source', 'user_answer', 'platform']
KNOWN_ACTIONS = {'enter', 'respond', 'submit', 'quit', 'erase_choice', 'undo_erase_choice',
                 'play_audio', 'pause_audio', 'play_video', 'pause_video', 'pay', 'refund', 'enroll_coupon'}


def validate_events(events):
    if events.empty:
        raise ValueError('empty event sample')
    if set(events.columns) != set(COLUMNS):
        raise ValueError('event schema differs from EdNet KT4')
    for column, pattern in [('timestamp', r'[0-9]+'), ('user_id', r'u[0-9]+'), ('action_type', r'[a-z_]+')]:
        if not events[column].astype(str).str.fullmatch(pattern).all():
            raise ValueError(f'invalid required {column}')
    timestamps = pd.to_numeric(events.timestamp, errors='raise')
    if (timestamps <= 0).any() or (timestamps > np.iinfo(np.int64).max).any():
        raise ValueError('timestamp outside positive int64 range')


def load_events(raw_dir):
    raw_dir = Path(raw_dir)
    local = json.loads((raw_dir / 'download_manifest.local.json').read_text())
    frames = []
    for record in local['member_records']:
        name = Path(record['member']).name
        if not re.fullmatch(r'u[0-9]+\.csv', name):
            raise ValueError('invalid raw member filename')
        path = raw_dir / name
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError(f'raw file checksum mismatch: {name}')
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        frame['user_id'] = path.stem
        if set(frame.columns) != set(COLUMNS):
            raise ValueError(f'event schema mismatch: {name}')
        frames.append(frame)
    if len(frames) != local['sample_users']:
        raise ValueError('sample user count differs from manifest')
    events = pd.concat(frames, ignore_index=True)[COLUMNS]
    validate_events(events)
    events['timestamp'] = events.timestamp.astype('int64')
    return events


def sql_features(events):
    validate_events(events)
    events = events.copy()
    events['timestamp'] = events.timestamp.astype('int64')
    query = (Path(__file__).resolve().parents[2] / 'sql' / 'ednet.sql').read_text()
    with duckdb.connect() as con:
        con.register('events', events)
        return con.execute(query).df()


def pandas_features(events):
    """Independent per-user implementation, with no SQL-derived intermediate data."""
    rows = []
    for user_id, group in events.groupby('user_id', sort=True):
        t = group.timestamp.astype('int64')
        days = (t - int(t.min())) // DAY
        first = (days >= 0) & (days <= 6)
        second = (days >= 7) & (days <= 13)
        masks = {
            'submit': (group.action_type == 'submit') & group.item_id.str.fullmatch(r'b\d+'),
            'entry': (group.action_type == 'enter') & group.item_id.str.fullmatch(r'[bel]\d+'),
            'ui': pd.Series(True, index=group.index),
        }
        row = {'user_id': user_id}
        for key, mask in masks.items():
            row[f'w1_{key}_days'] = int(days[first & mask].nunique())
            row[f'w2_{key}'] = int((second & mask).any())
        row['last_event_elapsed_day'] = int(days.max())
        row['rows'] = len(group)
        rows.append(row)
    return pd.DataFrame(rows)


def wilson(y, n):
    if not n:
        return None
    z = 1.959963984540054
    p = y / n
    center = (p + z*z/(2*n)) / (1+z*z/n)
    width = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return [max(0.0, float(center-width)), min(1.0, float(center+width))]


def compare(features, definition='submit', draws=2000):
    days, outcome = f'w1_{definition}_days', f'w2_{definition}'
    active = features.loc[features[days] > 0].copy()
    groups = []
    for label, mask in [('1', active[days] == 1), ('2+', active[days] >= 2)]:
        subset = active[mask]
        n, y = len(subset), int(subset[outcome].sum())
        groups.append({'active_days': label, 'n': n, 'recorded_nextweek': y,
                       'rate': y/n if n else None, 'ci95': wilson(y, n)})
    difference = None
    interval = None
    valid_draws = 0
    if all(group['n'] for group in groups):
        difference = groups[1]['rate'] - groups[0]['rate']
        values = active[[days, outcome]].to_numpy(dtype=int)
        rng = np.random.default_rng(101)
        deltas = []
        for _ in range(draws):
            resample = values[rng.integers(0, len(values), size=len(values))]
            low, high = resample[:, 0] == 1, resample[:, 0] >= 2
            if low.any() and high.any():
                deltas.append(resample[high, 1].mean() - resample[low, 1].mean())
        valid_draws = len(deltas)
        if deltas:
            interval = np.quantile(deltas, [0.025, 0.975]).tolist()
    return {'definition': definition, 'eligible_firstweek_users': len(active),
            'excluded_zero_firstweek_users': len(features) - len(active),
            'groups': groups, 'difference': difference, 'ci95': interval,
            'bootstrap_draws': draws, 'valid_draws': valid_draws, 'bootstrap_seed': 101}


def payment_summary(events, catalog):
    source_fields = catalog.columns.tolist()
    catalog = catalog.rename(columns={'type': 'payment_type', 'duaration': 'duration'})
    required = {'payment_item_id', 'payment_type', 'duration'}
    if not required <= set(catalog.columns):
        raise ValueError('payment catalog schema mismatch')
    if catalog.payment_item_id.duplicated().any() or catalog.payment_item_id.isna().any():
        raise ValueError('payment catalog keys must be unique and nonmissing')
    payments = events[events.action_type.isin(['pay', 'refund'])]
    joined = payments.merge(catalog, how='left', left_on='item_id', right_on='payment_item_id', validate='many_to_one')
    counts = joined.assign(payment_type=joined.payment_type.fillna('unknown')).groupby(['action_type','payment_type']).size()
    return {
        'pay_events': int((events.action_type == 'pay').sum()),
        'paying_users': int(events.loc[events.action_type == 'pay', 'user_id'].nunique()),
        'refund_events': int((events.action_type == 'refund').sum()),
        'refunding_users': int(events.loc[events.action_type == 'refund', 'user_id'].nunique()),
        'coupon_events': int((events.action_type == 'enroll_coupon').sum()),
        'coupon_users': int(events.loc[events.action_type == 'enroll_coupon', 'user_id'].nunique()),
        'unknown_payment_key_events': int(joined.payment_item_id.isna().sum()),
        'by_type': [{'action_type': action, 'payment_type': kind, 'events': int(n)} for (action,kind), n in counts.items()],
        'catalog_rows': len(catalog), 'catalog_types': sorted(catalog.payment_type.unique().tolist()),
        'catalog_unknown_type_rows': int((~catalog.payment_type.isin(['pass', 'paygo'])).sum()),
        'catalog_fields': catalog.columns.tolist(), 'catalog_source_fields': source_fields,
        'catalog_normalization': {'type': 'payment_type', 'duaration': 'duration'},
        'can_measure': ['recorded purchases', 'recorded refunds', 'recorded coupon enrollment'],
        'cannot_measure': ['revenue', 'renewals', 'subscription churn', 'net revenue', 'causal conversion lift'],
        'unit_note': 'Event records across each sampled complete history; no transaction ID, price/currency or verified entitlement state. Repeated pay records are not assumed to be renewals.',
    }


def build_report(raw_dir, expected_manifest=DEFAULT_SNAPSHOT):
    raw_dir = Path(raw_dir)
    manifest = verify_cache(raw_dir, expected_manifest)
    events = load_events(raw_dir)
    features = sql_features(events)
    independent = pandas_features(events)
    pd.testing.assert_frame_equal(features, independent, check_dtype=False)
    repeated = sql_features(events)
    pd.testing.assert_frame_equal(features, repeated, check_dtype=False)
    dedup = sql_features(events.drop_duplicates())
    comparison_columns = [c for c in features if c.startswith('w1_') or c.startswith('w2_')]
    changed = (features[comparison_columns] != dedup[comparison_columns]).any(axis=1)
    catalog = load_catalog(raw_dir)
    unknown_actions = events.loc[~events.action_type.isin(KNOWN_ACTIONS), 'action_type'].value_counts().to_dict()
    has_future = features.last_event_elapsed_day >= 14
    primary = compare(features, 'submit')
    payments = payment_summary(events, catalog)
    pay_user_ids = set(events.loc[events.action_type == 'pay', 'user_id'])
    quality = {
        'raw_rows': len(events), 'exact_duplicate_rows': int(events.duplicated().sum()),
        'deduplicated_rows': len(events.drop_duplicates()),
        'raw_vs_dedup_changed_users': int(changed.sum()),
        'invalid_required_fields': 0,
        'nonmonotonic_timestamp_users': int(events.groupby('user_id').timestamp.apply(lambda t: not t.is_monotonic_increasing).sum()),
        'unknown_action_counts': {k:int(v) for k,v in unknown_actions.items()},
        'unknown_platform_rows': int((~events.platform.isin(['mobile', 'web'])).sum()),
        **platform_quality(events),
        'missing_item_rows': int(events.item_id.eq('').sum()),
        'invalid_respond_answer_rows': int((events.action_type.eq('respond') & ~events.user_answer.isin(['a','b','c','d'])).sum()),
        'action_counts': {k:int(v) for k,v in events.action_type.value_counts().sort_index().items()},
        'firstweek_activity_group_changed_submit_vs_all_ui': int(((features.w1_submit_days >= 2) != (features.w1_ui_days >= 2)).sum()),
        'nextweek_flag_changed_submit_vs_all_ui': int((features.w2_submit != features.w2_ui).sum()),
        'exact_duplicate_policy': 'Retained in primary. No unique event or transaction ID, so equality alone does not prove logging error. Deduplication is a sensitivity check.',
    }
    return {
        'schema_version': 1, 'analysis_type': 'observational_public_data',
        'manifest': manifest,
        'definition': {
            'anchor': 'First recorded event per sampled user; not signup or first-ever learning.',
            'first_window': '[0, 7 × 24 hours)', 'next_window': '[7 × 24 hours, 14 × 24 hours)',
            'activity': 'submit of a question bundle (item_id b + digits)',
            'event_unit': 'Bundle final-answer submission; not OULAD click sum, individual question, lesson completion, or payment.',
            'active_day': 'floor((timestamp − first recorded timestamp) / 86,400,000); elapsed 24-hour bin, not calendar day',
            'denominator': 'Sample users with ≥1 qualifying submission in the first window; split into exactly 1 vs ≥2 active bins.',
            'outcome': 'At least one recorded qualifying submission in the next window.',
            'censoring': 'Per-user observation-end/coverage metadata unavailable; shifted timestamps cannot establish shared calendar end. No recorded next-week action is not proven churn. No future-activity requirement in primary denominator.',
            'ci_method': 'Wilson 95% for group recorded-event proportions; 2,000 user bootstrap draws, seed 101, for difference. Does not cover censoring, confounding or service transfer.',
        },
        'sample': {'users': int(events.user_id.nunique()), 'raw_rows': len(events),
                   'users_with_event_at_or_after_day14': int(has_future.sum()),
                   'users_without_event_at_or_after_day14': int((~has_future).sum()),
                   'histories_with_recorded_pay_fraction': len(pay_user_ids) / len(features)},
        'primary': primary,
        'event_definition_sensitivity': [compare(features, kind) for kind in ['entry', 'ui']],
        'censoring_sensitivity': {
            'status': 'not_identifiable',
            'diagnostic_only_future_selected': compare(features[has_future], 'submit'),
            'diagnostic_note': 'Restricted to histories with some event at/after day 14. Selection uses future behavior and induces survivor bias; NOT a corrected retention estimate, NOT an eligibility rule.',
        },
        'quality': quality, 'payments': payments,
        'limitations': [
            'Historical Santa TOEIC tutoring data, not CLASS101 internal data or current subscription behavior.',
            'Additively shifted timestamps preserve within-user gaps; real calendar dates and cross-user cohorts are not established.',
            'The first recorded event is not verified signup; left truncation and right censoring remain unresolved.',
            'A hash-selected sample supports reproducible exploratory descriptions, not whole-service rate claims.',
            'Observed activity association is not causal: motivation, prior skill, entitlement, recommendations and time availability are not randomized.',
            'No screen treatment, assignment, real participant recruitment or CLASS101 production experiment was performed.',
            'Payment/refund/coupon events exist, but price, currency, transaction identity, entitlement ledger and auto-renewal state do not.',
        ],
        'decision': 'Keep OULAD unchanged and add EdNet KT4 as supplementary evidence about event definitions and recorded learning activity. Use only to refine measurement and experiment hypotheses; hold causal retention/revenue claims.',
        'validation': {'sql_pandas_equal': True, 'repeat_feature_equal': True,
                       'compared_user_rows': len(features), 'compared_columns': features.columns.tolist(),
                       'raw_file_sha256_verified': True, 'download_member_crc_verified': True,
                       'contents_archive_sha256_verified': True, 'pinned_snapshot_verified': True,
                       'published_user_ids': False},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=Path('data/raw/ednet'))
    parser.add_argument('--output', type=Path, default=Path('reports/ednet_report.json'))
    parser.add_argument('--expected-manifest', type=Path, default=DEFAULT_SNAPSHOT)
    args = parser.parse_args()
    report = build_report(args.raw, args.expected_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(f'Wrote {args.output}: {report["sample"]["users"]:,} users, {report["sample"]["raw_rows"]:,} rows; SQL/pandas and repeat features match')


def platform_quality(events):
    missing = events.platform.eq('') | events.platform.isna()
    return {
        'missing_platform_rows': int(missing.sum()),
        'missing_platform_by_action': {k:int(v) for k,v in events.loc[missing, 'action_type'].value_counts().sort_index().items()},
        'unknown_nonempty_platform_rows': int((~missing & ~events.platform.isin(['mobile', 'web'])).sum()),
    }


def load_catalog(raw_dir):
    raw_dir = Path(raw_dir)
    manifest = json.loads((raw_dir / 'download_manifest.json').read_text())
    blob = (raw_dir / 'contents.zip').read_bytes()
    if hashlib.sha256(blob).hexdigest() != manifest['contents_zip_sha256']:
        raise ValueError('contents archive checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        data = archive.read('contents/payments.csv')
    return pd.read_csv(io.BytesIO(data))


if __name__ == '__main__':
    main()

"""Offline experiment contract checks, not a randomizer or causal effect estimator.

Inputs must come from a reconciled assignment ledger and a complete event source.
Passing these checks cannot establish that unobserved events were not lost.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from math import ceil, comb, erfc, isfinite, sqrt

ARMS = ('control', 'treatment')
KINDS = ('learning', 'exposure', 'playback_error', 'refund')
DAY = timedelta(days=1)


def _timestamp(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _key(value):
    return isinstance(value, str) and bool(value.strip())


def recruitment_days(per_arm, daily_eligible, late_buffer_days=1):
    """Hypothetical recruitment upper bound with complete weekly cycles."""
    if any(not isinstance(v, int) or isinstance(v, bool) for v in (per_arm, daily_eligible, late_buffer_days)):
        raise ValueError('Inputs must be integer counts/days')
    if per_arm <= 0 or daily_eligible <= 0 or late_buffer_days < 0:
        raise ValueError('Positive sample/inflow and nonnegative buffer required')
    raw = ceil(2 * per_arm / daily_eligible)
    recruitment = max(7, 7 * ceil(raw / 7))
    return dict(raw_recruitment_days=raw, recruitment_days=recruitment,
                maturation_days=14, late_buffer_days=late_buffer_days,
                total_days_upper_bound=recruitment + 14 + late_buffer_days)


def evaluate(*, assignments, events, experiment_id, enrollment_start, enrollment_end,
             as_of, watermark, late_buffer, target_per_arm, checkpoint,
             srm_alpha, guardrail_max_increase):
    """Evaluate one prespecified final snapshot or interim quality-only snapshot.

    T0 is assignment time; D7–13 is elapsed UTC [T0+7d, T0+14d).
    watermark is an externally attested event-occurrence completeness boundary.
    All timestamps are timezone-aware. 1:1 SRM uses Pearson chi-square (df=1),
    at one final checkpoint only (exact binomial when N<10).
    Guardrail differences are descriptive operational thresholds, not tests.
    """
    times = (enrollment_start, enrollment_end, as_of, watermark)
    if (not all(_timestamp(t) for t in times) or not _key(experiment_id)
            or not enrollment_start < enrollment_end <= as_of or watermark > as_of
            or not isinstance(late_buffer, timedelta) or late_buffer < timedelta(0)
            or not isinstance(target_per_arm, int) or isinstance(target_per_arm, bool) or target_per_arm < 1
            or checkpoint not in ('interim', 'final')
            or not isinstance(srm_alpha, (int, float)) or not 0 < srm_alpha < 1
            or not guardrail_max_increase):
        raise ValueError('Invalid experiment contract/configuration')
    for kind, threshold in guardrail_max_increase.items():
        if (kind not in ('playback_error', 'refund') or not isinstance(threshold, (int, float))
                or not isfinite(threshold) or not 0 <= threshold <= 1):
            raise ValueError('Invalid guardrail contract')
    enrollment_start, enrollment_end, as_of, watermark = (t.astimezone(timezone.utc) for t in times)
    result = dict(status='hold', reasons=[], arms=None, difference=None,
                  srm_p=None, srm_method='Pearson chi-square df=1; 1:1; one final checkpoint',
                  guardrails={}, duplicate_events=0,
                  interpretation='Readiness/descriptive check only; not evidence of product impact')
    reasons = result['reasons']
    by_id, users = {}, set()
    for row in assignments:
        if (not isinstance(row, dict)
                or not all(_key(row.get(k)) for k in ('assignment_id', 'user_id', 'experiment_id'))
                or row.get('experiment_id') != experiment_id or row.get('variant') not in ARMS
                or not _timestamp(row.get('assigned_at'))):
            reasons.append('invalid_assignment')
            continue
        row = row | {'assigned_at': row['assigned_at'].astimezone(timezone.utc)}
        if not enrollment_start <= row['assigned_at'] < enrollment_end:
            reasons.append('assignment_outside_enrollment')
        if row['assignment_id'] in by_id or row['user_id'] in users:
            reasons.append('duplicate_or_cross_variant_assignment')
        by_id[row['assignment_id']] = row
        users.add(row['user_id'])
    if reasons:
        result['reasons'] = sorted(set(reasons))
        return result  # No plausible-looking counts from a corrupted assignment ledger.

    matured = {a for a, r in by_id.items() if r['assigned_at'] + 14 * DAY <= watermark}
    counts = Counter(r['variant'] for r in by_id.values())
    if len(matured) != len(by_id):
        reasons.append('immature_assignments')
    latest = max((r['assigned_at'] for r in by_id.values()), default=enrollment_start)
    if as_of < latest + 14 * DAY + late_buffer:
        reasons.append('late_buffer_not_elapsed')
    if watermark < latest + 14 * DAY:
        reasons.append('observation_not_closed')
    if any(counts[arm] < target_per_arm for arm in ARMS):
        reasons.append('insufficient_sample')

    seen, returned = {}, set()
    affected = {kind: set() for kind in guardrail_max_increase}
    for row in events:
        if (not isinstance(row, dict)
                or not all(_key(row.get(k)) for k in ('event_id', 'assignment_id', 'user_id', 'experiment_id'))
                or not all(_timestamp(row.get(k)) for k in ('occurred_at', 'ingested_at'))
                or row.get('kind') not in KINDS):
            reasons.append('invalid_event')
            continue
        eid = row['event_id']
        if eid in seen:
            if row != seen[eid]:
                reasons.append('conflicting_event_id')
            else:
                result['duplicate_events'] += 1
            continue
        seen[eid] = row
        a = by_id.get(row['assignment_id'])
        if a is None or any(row.get(k) != a[k] for k in ('user_id', 'variant', 'experiment_id')):
            reasons.append('event_assignment_mismatch')
            continue
        occurred, ingested = (row[k].astimezone(timezone.utc) for k in ('occurred_at', 'ingested_at'))
        if occurred < a['assigned_at'] or ingested < occurred:
            reasons.append('invalid_event_time')
            continue
        if ingested > as_of:
            if occurred < watermark:
                reasons.append('watermark_contradicted')
            continue
        if ingested - occurred > late_buffer:
            reasons.append('late_arrival')
        aid = row['assignment_id']
        if aid not in matured:
            continue
        elapsed = occurred - a['assigned_at']
        if row['kind'] == 'learning' and 7 * DAY <= elapsed < 14 * DAY:
            returned.add(aid)
        if row['kind'] in affected and timedelta(0) <= elapsed < 14 * DAY:
            affected[row['kind']].add(aid)
    result['arms'] = {}
    for arm in ARMS:
        n = sum(by_id[a]['variant'] == arm for a in matured)
        y = sum(by_id[a]['variant'] == arm for a in returned)
        result['arms'][arm] = dict(assigned=counts[arm], matured=n, returned=y, rate=y / n if n else None)
    for kind, ids in affected.items():
        rates = {}
        for arm in ARMS:
            n = result['arms'][arm]['matured']
            rates[arm] = sum(by_id[a]['variant'] == arm for a in ids) / n if n else None
        increase = rates['treatment'] - rates['control'] if all(v is not None for v in rates.values()) else None
        result['guardrails'][kind] = dict(rates=rates, increase=increase, max_increase=guardrail_max_increase[kind])
        if increase is not None and increase > guardrail_max_increase[kind]:
            reasons.append('guardrail:' + kind)
    if checkpoint == 'interim':
        reasons.append('not_final_checkpoint')
    elif len(by_id) >= 10:
        # chi-square=(n_control-n_treatment)^2/N; df=1 survival=erfc(sqrt(x/2)).
        statistic = (counts['control'] - counts['treatment']) ** 2 / len(by_id)
        result['srm_p'] = erfc(sqrt(statistic / 2))
        if result['srm_p'] < srm_alpha:
            reasons.append('srm')
    elif by_id:
        n = len(by_id)
        tail = min(counts[arm] for arm in ARMS)
        result['srm_p'] = min(1., 2 * sum(comb(n, k) for k in range(tail + 1)) / 2 ** n)
        result['srm_method'] = 'Two-sided exact binomial; 1:1; one final checkpoint; N<10'
        if result['srm_p'] < srm_alpha:
            reasons.append('srm')
    result['reasons'] = sorted(set(reasons))
    if not reasons and all(result['arms'][arm]['rate'] is not None for arm in ARMS):
        result['status'] = 'ready_for_review'
        result['difference'] = result['arms']['treatment']['rate'] - result['arms']['control']['rate']
    return result

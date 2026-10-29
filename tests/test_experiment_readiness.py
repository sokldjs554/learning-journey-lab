"""Synthetic contract tests; these are not user experiments or observed effects."""
from datetime import datetime, timedelta, timezone
import pytest
from journey.experiment_readiness import evaluate, recruitment_days

T0 = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)

def assignment(i, variant='control', day=0):
    return dict(assignment_id=f'a{i}', user_id=f'u{i}', experiment_id='resume-v1',
                variant=variant, assigned_at=T0+timedelta(days=day))

def event(i, a, day=7, kind='learning', **changes):
    row=dict(event_id=f'e{i}', assignment_id=a['assignment_id'], user_id=a['user_id'],
             experiment_id=a['experiment_id'], variant=a['variant'], kind=kind,
             occurred_at=a['assigned_at']+timedelta(days=day),
             ingested_at=a['assigned_at']+timedelta(days=day, hours=1))
    return row | changes

def run(assignments=None, events=None, **changes):
    args=dict(assignments=assignments if assignments is not None else [assignment(0), assignment(1, 'treatment')],
              events=events or [], experiment_id='resume-v1',
              enrollment_start=T0, enrollment_end=T0+timedelta(days=7),
              as_of=T0+timedelta(days=23), watermark=T0+timedelta(days=22),
              late_buffer=timedelta(days=1), target_per_arm=1,
              checkpoint='final', srm_alpha=.001,
              guardrail_max_increase={'playback_error': .01, 'refund': .01})
    return evaluate(**(args | changes))

def test_itt_keeps_unexposed_and_deduplicates_learning_events():
    a=[assignment(0), assignment(1), assignment(2,'treatment'), assignment(3,'treatment')]
    e=event(0,a[0])
    result=run(a,[e,e,event(1,a[2])])
    assert result['status']=='ready_for_review'
    assert result['arms']['control']==dict(assigned=2,matured=2,returned=1,rate=.5)
    assert result['difference']==0
    assert result['duplicate_events']==1

@pytest.mark.parametrize('day,expected', [(7-1/86400,0),(7,1),(14-1/86400,1),(14,0)])
def test_elapsed_window_boundaries(day,expected):
    a=assignment(0)
    assert run(events=[event(0,a,day)])['arms']['control']['returned']==expected

@pytest.mark.parametrize('mutate', [
    lambda a: a+[a[0]],
    lambda a: a+[assignment(0,'treatment')|{'assignment_id':'other'}],
    lambda a: [a[0]|{'user_id':None},a[1]],
    lambda a: [a[0]|{'experiment_id':'wrong'},a[1]],
    lambda a: [a[0]|{'variant':'other'},a[1]],
    lambda a: [a[0]|{'assigned_at':T0.replace(tzinfo=None)},a[1]],
    lambda a: [a[0]|{'assigned_at':T0+timedelta(days=7)},a[1]],
])
def test_bad_assignment_blocks_effect_and_counts(mutate):
    r=run(mutate([assignment(0),assignment(1,'treatment')]))
    assert r['status']=='hold' and r['difference'] is None and r['arms'] is None

@pytest.mark.parametrize('changes', [{'assignment_id':'unknown'},{'user_id':'wrong'},
    {'experiment_id':'wrong'},{'variant':'treatment'},{'event_id':None},
    {'occurred_at':None},{'kind':'uncontracted'}, {'ingested_at':T0}])
def test_wrong_event_keys_and_nulls_hold(changes):
    r=run(events=[event(0,assignment(0),**changes)])
    assert r['status']=='hold' and r['difference'] is None

def test_conflicting_replay_holds():
    e=event(0,assignment(0))
    r=run(events=[e,e|{'occurred_at':T0+timedelta(days=8)}])
    assert 'conflicting_event_id' in r['reasons']

def test_nonmatured_assignments_never_become_failures():
    r=run([assignment(0),assignment(1,'treatment',6)],watermark=T0+timedelta(days=19))
    assert r['arms']['treatment']==dict(assigned=1,matured=0,returned=0,rate=None)
    assert r['difference'] is None and 'immature_assignments' in r['reasons']

def test_maturation_exact_boundary_and_buffer():
    r=run(watermark=T0+timedelta(days=14))
    assert r['arms']['control']['matured']==1
    assert 'observation_not_closed' not in r['reasons']
    r=run(as_of=T0+timedelta(days=14),watermark=T0+timedelta(days=14))
    assert r['difference'] is None
    assert 'late_buffer_not_elapsed' in r['reasons']

def test_late_observed_event_holds():
    e=event(0,assignment(0),ingested_at=T0+timedelta(days=10))
    assert 'late_arrival' in run(events=[e])['reasons']

def test_future_ingestion_does_not_change_numerator_but_contradicts_watermark():
    e=event(0,assignment(0),ingested_at=T0+timedelta(days=24))
    r=run(events=[e])
    assert r['arms']['control']['returned']==0
    assert 'watermark_contradicted' in r['reasons']

def test_interim_never_computes_srm_or_effect():
    r=run(checkpoint='interim')
    assert r['srm_p'] is None and r['difference'] is None

def test_srm_all_assigned_fixed_checkpoint():
    a=[assignment(i) for i in range(99)]+[assignment(99,'treatment')]
    r=run(a)
    assert r['srm_p']<.001 and 'srm' in r['reasons'] and r['difference'] is None

def test_missing_arm_empty_and_insufficient_sample_hold():
    for r in [run([]),run([assignment(0)]),run(target_per_arm=2)]:
        assert r['difference'] is None and r['status']=='hold'

def test_guardrail_at_threshold_passes_and_over_holds():
    e=event(0,assignment(1,'treatment'),day=2,kind='refund')
    r=run(events=[e],guardrail_max_increase={'refund':1.0})
    assert r['status']=='ready_for_review'
    r=run(events=[e],guardrail_max_increase={'refund':.01})
    assert r['guardrails']['refund']['increase']==1
    assert 'guardrail:refund' in r['reasons'] and r['difference'] is None

@pytest.mark.parametrize('kwargs',[{'srm_alpha':0},{'target_per_arm':0},
    {'late_buffer':timedelta(days=-1)}, {'guardrail_max_increase':{}},
    {'watermark':T0+timedelta(days=99)},{'checkpoint':'daily'}])
def test_invalid_config_is_explicit(kwargs):
    with pytest.raises(ValueError): run(**kwargs)

def test_recruitment_weekly_rounding_and_maturation():
    assert recruitment_days(4356,100,1)==dict(raw_recruitment_days=88,recruitment_days=91,
        maturation_days=14,late_buffer_days=1,total_days_upper_bound=106)
    with pytest.raises(ValueError): recruitment_days(4356,0,1)

def test_dst_offsets_are_elapsed_hours_not_calendar_days():
    from zoneinfo import ZoneInfo
    # DST transition March 8: local wall-clock +7 days is only 167 hours.
    start=datetime(2026,3,1,12,tzinfo=ZoneInfo('America/New_York'))
    a=assignment(0)|{'assigned_at':start}
    b=assignment(1,'treatment')|{'assigned_at':start}
    e=event(0,a,7)
    r=run([a,b],[e],enrollment_start=start,enrollment_end=start+timedelta(days=7),
          as_of=start+timedelta(days=23),watermark=start+timedelta(days=22))
    assert r['arms']['control']['returned']==0

def test_small_sample_srm_reports_exact_check_instead_of_skipping():
    r=run()
    assert r['srm_p']==1.0
    assert 'exact binomial' in r['srm_method']

"""Hand-checkable synthetic contract tests, not company subscription outcomes."""
import copy
import importlib
import json
import pytest


def module():
    return importlib.import_module('journey.subscription_bridge')


def test_generated_ledger_hand_counts_and_payer_grain():
    m=module();result=m.analyze(m.fixture())
    assert result['provenance']=='100_percent_synthetic'
    assert result['mature_cycles']==7 and result['renewed_cycles']==3
    rows={r['cycle_id']:r for r in result['cycles']}
    assert rows['c1']['outcome']=='renewed'
    assert rows['c2']['outcome']=='payment_failed'
    assert rows['c3']['outcome']=='fully_refunded'
    assert rows['c4']['outcome']=='pending' and rows['c4']['renewed'] is None
    assert rows['c5']['learner_count']==2 and rows['c5']['learning_days']==2
    assert rows['c5']['renewed']==1  # two members + retransmission still one renewal
    assert rows['c6']['outcome']=='renewed'  # cancellation request is not expiry
    assert rows['c7']['outcome']=='no_settlement_in_window'
    assert rows['c8']['outcome']=='no_settlement_in_window'  # late settlement


def test_duplicate_ids_conflict_and_unknown_keys_fail_closed():
    m=module();data=m.fixture()
    bad=copy.deepcopy(data);row=copy.deepcopy(bad['billing'][0]);row['kind']='failed';bad['billing'].append(row)
    with pytest.raises(ValueError,match='conflicting'):m.analyze(bad)
    bad=copy.deepcopy(data);bad['learning'][0]['learner_id']='unknown'
    with pytest.raises(ValueError,match='membership'):m.analyze(bad)
    bad=copy.deepcopy(data);bad['cycles'].append(copy.deepcopy(bad['cycles'][0]))
    with pytest.raises(ValueError,match='cycle'):m.analyze(bad)


def test_observation_maturity_and_no_future_receipt_leak():
    m=module();data=m.fixture()
    data['as_of']=data['watermark']='2025-01-07T23:59:59+00:00'
    result=m.analyze(data)
    assert result['mature_cycles']==0 and result['renewal_rate'] is None
    data=m.fixture();data['billing'][0]['ingested_at']='2025-01-11T00:00:00+00:00'
    with pytest.raises(ValueError,match='watermark'):m.analyze(data)


def test_boundary_learning_membership_and_renewal_window():
    m=module();data=m.fixture()
    event=copy.deepcopy(data['learning'][0]);event['event_id']='at_w1_end'
    event['occurred_at']=event['ingested_at']='2024-01-08T00:00:00+00:00'
    data['learning'].append(event)
    first=next(r for r in m.analyze(data)['cycles'] if r['cycle_id']=='c1')
    assert first['learning_days']==2
    data=m.fixture();data['members'][0]['valid_to']='2024-01-02T00:00:00+00:00'
    with pytest.raises(ValueError,match='membership'):m.analyze(data)
    data=m.fixture();data['billing'][0]['occurred_at']=data['billing'][0]['ingested_at']='2025-01-08T00:00:00+00:00'
    assert next(r for r in m.analyze(data)['cycles'] if r['cycle_id']=='c1')['renewed']==0


def test_refund_requires_settlement_and_transaction_cannot_cross_cycles():
    m=module();data=m.fixture()
    data['billing']=[r for r in data['billing'] if r['event_id']!='pay3']
    with pytest.raises(ValueError,match='refund'):m.analyze(data)
    data=m.fixture();data['billing'][1]['transaction_id']=data['billing'][0]['transaction_id']
    with pytest.raises(ValueError,match='transaction'):m.analyze(data)


def test_naive_time_and_false_watermark_rejected():
    m=module();data=m.fixture();data['as_of']='2025-01-10'
    with pytest.raises(ValueError,match='timezone'):m.analyze(data)
    data=m.fixture();data['watermark']='2025-01-11T00:00:00+00:00'
    with pytest.raises(ValueError,match='watermark'):m.analyze(data)


def test_same_subscription_due_date_cannot_double_count_denominator():
    m=module();data=m.fixture();row=copy.deepcopy(data['cycles'][0]);row['cycle_id']='duplicate'
    data['cycles'].append(row)
    with pytest.raises(ValueError,match='cycle'):m.analyze(data)


def test_empty_billing_is_not_zero_denominator_and_empty_input_is_defined():
    m=module();data=m.fixture();data['billing']=[]
    assert m.analyze(data)['mature_cycles']==7
    assert m.analyze(data)['renewed_cycles']==0
    for table in ['cycles','members','learning','billing']:data[table]=[]
    assert m.analyze(data)['renewal_rate'] is None


def test_published_fixture_and_report_match_current_calculation():
    m=module()
    saved=json.loads((m.ROOT/'data/synthetic/subscription_bridge.json').read_text())
    assert saved==m.fixture()
    assert json.loads((m.ROOT/'reports/subscription-bridge.json').read_text())==m.analyze(saved)

from journey.faults import fault_lab


def test_known_loss_duplicate_cancellation_and_replay():
    r=fault_lab()
    s={x['id']:x for x in r['stages']}
    assert s['truth']['w1']==10 and s['truth']['w2']==6 and s['truth']['rate']==.6
    assert s['observed']['naive_rate']==.6  # duplicate rows mask missing learners
    assert s['observed']['rate']==.4
    assert s['clean']['rate']==.4 and s['clean']['gate']=='BLOCK'
    assert s['late']['rate']==.5 and s['late']['missing_events']==2
    assert s['replay']['rate']==.6 and s['replay']['gate']=='PASS'


def test_rules_distinguish_ingestion_order_from_event_order():
    r=fault_lab()
    q={x['rule_id']:x['count'] for x in r['issues']}
    assert q['duplicate_id']==2
    assert q['null_user']==1
    assert q['unknown_user']==1
    assert q['semantic_order']==1
    assert q['arrival_order']>=1
    assert q['missing_manifest_events']==4


def test_fault_lab_is_idempotent():
    assert fault_lab()==fault_lab()

from journey.tracker import update_issues


def test_repeat_snapshot_does_not_duplicate_issue_history():
    c=[{'rule_id':'missing_key','severity':'block','count':2}]
    first=update_issues([],c,'a')
    assert update_issues(first,c,'a')==first
    assert first[0]['status']=='open' and len(first[0]['history'])==1


def test_resolution_preserves_first_seen_and_prior_count():
    c=[{'rule_id':'missing_key','severity':'block','count':2}]
    first=update_issues([],c,'a')
    final=update_issues(first,[{**c[0],'count':0}],'b')[0]
    assert final['first_seen']=='a' and final['status']=='resolved'
    assert [s['count'] for s in final['history']]==[2,0]
    assert first[0]['status']=='open'

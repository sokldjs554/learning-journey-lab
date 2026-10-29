import pytest
from journey.pipeline import build_marts, quality


def test_days_denominator_and_nonpositive_clicks(db):
    build_marts(db)
    rows=db.sql('select id_student,w1_days,w2_active,later_active from mart order by id_student').fetchall()
    assert rows==[(1,2,1,0),(2,1,1,0),(6,0,0,1)]


def test_duplicate_presence_robust_but_volume_ambiguous(db):
    build_marts(db)
    assert db.sql('select first_clicks_raw,first_clicks_exact,first_clicks_max from mart where id_student=1').fetchone()==(10,5,5)


def test_future_withdrawal_does_not_remove_denominator(db):
    build_marts(db,strict=True)
    assert db.sql('select id_student,w2_active from mart order by id_student').fetchall()==[(1,1),(2,0),(6,0)]


def test_missing_key_duplicates_and_temporal_warnings(db):
    q={r['rule_id']:r['count'] for r in quality(db)}
    assert q['event_exact_repeat']==1
    assert q['event_required_null']==1
    assert q['event_unknown_student']==1
    assert q['event_unknown_site']==1
    assert q['event_nonpositive_click']==1
    assert q['registration_missing_date']==1
    assert q['event_after_withdrawal']==1
    assert q['event_after_course']==1


def test_duplicate_dimension_fails_before_join(db):
    db.execute('insert into vle select * from vle limit 1')
    with pytest.raises(ValueError,match='dimension'):
        build_marts(db)


def test_first_day_content_not_sequence(db):
    build_marts(db)
    assert db.sql('select first_day,first_content from mart where id_student=1').fetchone()==(0,1)
    assert db.sql('select first_day,first_content from mart where id_student=2').fetchone()==(0,0)


@pytest.mark.parametrize('mutation,rule',[
    ("insert into studentRegistration values ('ZZZ','2013J',88,0,null)",'registration_unknown_course'),
    ("insert into studentRegistration values ('AAA','2013J',null,0,null)",'registration_required_null'),
    ("insert into vle values (99,'ZZZ','2013J','oucontent',null,null)",'site_unknown_course'),
    ("update courses set module_presentation_length=0",'course_invalid_length'),
    ("update vle set id_site=null where id_site=10",'site_required_null'),
    ("update courses set code_module=null",'course_required_null'),
])
def test_invalid_dimensions_block_before_silent_join(db,mutation,rule):
    db.execute(mutation)
    checks={x['rule_id']:x['count'] for x in quality(db)}
    assert checks.get(rule,0)>0
    with pytest.raises(ValueError,match='dimension'):
        build_marts(db)

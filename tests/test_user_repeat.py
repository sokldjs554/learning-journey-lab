from journey.pipeline import quality


def test_three_identical_rows_count_two_excess(db):
    db.execute("INSERT INTO studentVle VALUES ('AAA','2013J',1,10,0,5)")
    checks = {row["rule_id"]: row["count"] for row in quality(db)}
    assert checks["event_exact_repeat"] == 2

"""Codex-written hand-checkable cases for the applicant's unchanged SQL."""
from pathlib import Path
import duckdb
import pytest

SQL = (Path(__file__).resolve().parents[1] / 'evidence/applicant/quality.sql').read_text()
RULES = ['registration_missing_date', 'event_exact_repeat', 'event_unknown_student']
BASE = ('AAA', '2014J', 1, 10, 0, 2)


def query(registrations=(), events=()):
    with duckdb.connect(':memory:') as connection:
        connection.execute('CREATE TABLE studentRegistration(code_module VARCHAR, code_presentation VARCHAR, id_student BIGINT, date_registration BIGINT)')
        connection.execute('CREATE TABLE studentVle(code_module VARCHAR, code_presentation VARCHAR, id_student BIGINT, id_site BIGINT, date BIGINT, sum_click BIGINT)')
        if registrations:
            connection.executemany('INSERT INTO studentRegistration VALUES (?, ?, ?, ?)', registrations)
        if events:
            connection.executemany('INSERT INTO studentVle VALUES (?, ?, ?, ?, ?, ?)', events)
        before = [connection.execute('SELECT * FROM ' + table).fetchall()
                  for table in ['studentRegistration', 'studentVle']]
        first = connection.execute(SQL)
        assert [col[0] for col in first.description] == ['rule_id', 'issue_count']
        rows = first.fetchall()
        assert [row[0] for row in rows] == RULES
        assert connection.execute(SQL).fetchall() == rows
        assert before == [connection.execute('SELECT * FROM ' + table).fetchall()
                          for table in ['studentRegistration', 'studentVle']]
        return tuple(row[1] for row in rows)


def test_empty_tables_return_three_zero_counts():
    assert query() == (0, 0, 0)


@pytest.mark.parametrize('copies', [1, 2, 3, 5])
def test_repeat_counts_only_excess(copies):
    assert query([('AAA', '2014J', 1, 0)], [BASE] * copies) == (0, copies - 1, 0)


@pytest.mark.parametrize('column,new_value', [(0, 'BBB'), (1, '2014B'), (2, 2), (3, 11), (4, 1), (5, 3)])
def test_all_six_columns_define_exact_repeat(column, new_value):
    other = list(BASE)
    other[column] = new_value
    expected_unknown = int(column in (0, 1, 2))
    assert query([('AAA', '2014J', 1, 0)], [BASE, tuple(other)]) == (0, 0, expected_unknown)


def test_duplicate_registration_does_not_multiply_or_hide_events():
    registrations = [('AAA', '2014J', 1, 0), ('AAA', '2014J', 1, None)]
    unknown = ('AAA', '2014J', 2, 10, 0, 2)
    assert query(registrations, [BASE, unknown, unknown]) == (1, 1, 2)


def test_registration_date_zero_is_not_missing():
    registrations = [('AAA', '2014J', 1, None), ('AAA', '2014J', 2, 0), ('AAA', '2014J', 3, -5)]
    assert query(registrations) == (1, 0, 0)


def test_null_student_ids_ignored_for_unknown_but_not_exact_repeat():
    event = ('AAA', '2014J', None, 10, 0, 2)
    assert query([], [event, event]) == (0, 1, 0)


def test_null_course_key_cannot_match_with_equality():
    assert query([(None, '2014J', 1, 0)], [(None, '2014J', 1, 10, 0, 2)]) == (0, 0, 1)


def test_multiple_repeat_groups_are_summed():
    other = ('AAA', '2014J', 1, 11, 0, 2)
    assert query([('AAA', '2014J', 1, 0)], [BASE] * 3 + [other] * 2) == (0, 3, 0)

#!/usr/bin/env python3
"""Aggregate enrollment-mart CSV into deterministic overall/cohort JSON.

Inputs: --mart (12-column CSV), --sql (read-only aggregate.sql), --output (JSON).
Exit status: 0=success, 1=argument/input/SQL/result/output error.

Reuses the earlier build_mart.py mart contract and run_quality_full.py's
argument-error/atomic-JSON-save helpers. This step does not rerun source quality.
"""

import csv
import hashlib
import math
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from build_mart import COLUMNS as MART_COLUMNS, check_row
from run_quality_full import (
    QualityArgumentParser,
    QualityRunError,
    save_json_atomic,
)

GROUPS = ("1일", "2일", "3일 이상")
OUTPUT_COLUMNS = (
    "scope", "code_module", "code_presentation", "activity_group",
    "denominator", "numerator", "return_rate_pct",
)
CHUNK_SIZE = 1024 * 1024
INSERT_BATCH = 4096


# Match SQL ROUND(..., 1) semantics (half away from zero, for nonnegative rates).
def round_rate(numerator: int, denominator: int):
    if denominator == 0:
        return None
    value = Decimal(100 * numerator) / Decimal(denominator)
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while data := handle.read(CHUNK_SIZE):
            digest.update(data)
    return digest.hexdigest()


def required_integer(value: str, field: str, row_number: int) -> int:
    """Read canonical integer CSV fields, rejecting floats and empty values."""
    try:
        if not value or value.strip() != value:
            raise ValueError("missing or padded")
        if not (value.isdecimal() or (
            value.startswith("-") and value[1:].isdecimal()
        )):
            raise ValueError("not an integer")
        return int(value)
    except ValueError as exc:
        raise QualityRunError(f"CSV {row_number}행: {field} 정수 형식 오류 ({value!r})") from exc


def optional_integer(value: str, field: str, row_number: int):
    return None if value == "" else required_integer(value, field, row_number)


def parse_row(values, row_number: int):
    if len(values) != len(MART_COLUMNS):
        raise QualityRunError(f"CSV {row_number}행: 열 개수 오류")
    module, presentation = values[:2]
    if not module.strip() or not presentation.strip():
        raise QualityRunError(f"CSV {row_number}행: 강좌·개설기 키 결측")

    row = (
        module,
        presentation,
        required_integer(values[2], "id_student", row_number),
        required_integer(values[3], "w1_days", row_number),
        required_integer(values[4], "w2_active", row_number),
        required_integer(values[5], "later_active", row_number),
        optional_integer(values[6], "first_day", row_number),
        optional_integer(values[7], "date_unregistration", row_number),
        required_integer(values[8], "first_content", row_number),
        required_integer(values[9], "first_clicks_raw", row_number),
        required_integer(values[10], "first_clicks_exact", row_number),
        required_integer(values[11], "first_clicks_max", row_number),
    )
    # The same business constraints as the existing mart exporter; do not
    # require sorted CSV input (its ordering may change without changing output).
    check_row(row, None, row_number)
    w1, first_day, withdrawal, raw = row[3], row[6], row[7], row[9]
    if withdrawal is not None and withdrawal < 0:
        raise QualityRunError(f"CSV {row_number}행: 적격 수강 건의 탈퇴일이 음수입니다")
    if w1 > 0 and (raw == 0 or w1 > 7 - first_day):
        raise QualityRunError(f"CSV {row_number}행: 첫 주 활동일/클릭값의 모순")
    return row


def create_mart(con):
    con.execute("""
        CREATE TABLE mart (
            code_module VARCHAR NOT NULL,
            code_presentation VARCHAR NOT NULL,
            id_student BIGINT NOT NULL,
            w1_days INTEGER NOT NULL,
            w2_active INTEGER NOT NULL,
            later_active INTEGER NOT NULL,
            first_day INTEGER,
            date_unregistration INTEGER,
            first_content INTEGER NOT NULL,
            first_clicks_raw BIGINT NOT NULL,
            first_clicks_exact BIGINT NOT NULL,
            first_clicks_max BIGINT NOT NULL
        )
    """)


def load_and_summarize(con, csv_path: Path):
    """Validate and stream CSV rows into a temporary in-memory mart.

    Aggregate independently in Python for cross-checking the SQL output.
    """
    if not csv_path.is_file():
        raise QualityRunError(f"mart CSV 파일이 없습니다: {csv_path}")

    create_mart(con)
    seen = set()
    cohorts = set()
    counts = {}
    eligible = active = returned = 0
    batch = []

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            if header != list(MART_COLUMNS):
                raise QualityRunError(
                    f"mart CSV 헤더 오류: 기대={MART_COLUMNS!r}, 실제={header!r}"
                )
            for line_number, values in enumerate(reader, start=2):
                row = parse_row(values, line_number)
                key = row[:3]
                if key in seen:
                    raise QualityRunError(f"CSV {line_number}행: 중복 수강 건 키: {key!r}")
                seen.add(key)
                cohorts.add(key[:2])
                eligible += 1

                if row[3] >= 1:
                    active += 1
                    returned += row[4]
                    group = GROUPS[min(row[3], 3) - 1]
                    for scoped_key in (
                        ("overall", None, None, group),
                        ("cohort", key[0], key[1], group),
                    ):
                        numerator_denominator = counts.setdefault(scoped_key, [0, 0])
                        numerator_denominator[0] += 1
                        numerator_denominator[1] += row[4]

                batch.append(row)
                if len(batch) == INSERT_BATCH:
                    con.executemany("INSERT INTO mart VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
            if batch:
                con.executemany("INSERT INTO mart VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
    except (csv.Error, UnicodeError) as exc:
        raise QualityRunError(f"mart CSV 읽기 오류: {exc}") from exc

    expected_keys = [("overall", None, None, group) for group in GROUPS]
    for module, presentation in sorted(cohorts):
        expected_keys.extend(("cohort", module, presentation, group) for group in GROUPS)
    return {
        "eligible": eligible,
        "w1_active": active,
        "w2_returned": returned,
        "return_rate_pct": round_rate(returned, active),
    }, expected_keys, counts


def validate_sql_result(result, expected_keys, counts, overall):
    columns = tuple(x[0] for x in (result.description or ()))
    if columns != OUTPUT_COLUMNS:
        raise QualityRunError(f"집계 SQL 결과 열 오류: {columns!r}")

    rows = result.fetchall()
    if len(rows) != len(expected_keys):
        raise QualityRunError(
            f"집계 SQL 행 수 오류: 기대={len(expected_keys)}, 실제={len(rows)}"
        )
    validated = []
    for index, (actual, expected_key) in enumerate(zip(rows, expected_keys), 1):
        if len(actual) != len(OUTPUT_COLUMNS) or tuple(actual[:4]) != expected_key:
            raise QualityRunError(f"집계 SQL {index}행: 범위·개설기·활동 그룹 또는 정렬 오류")
        denominator, numerator, rate = actual[4:]
        if (type(denominator) is not int or type(numerator) is not int
                or denominator < 0 or not 0 <= numerator <= denominator):
            raise QualityRunError(f"집계 SQL {index}행: 분모·분자 형식 또는 범위 오류")
        expected_denominator, expected_numerator = counts.get(expected_key, (0, 0))
        if (denominator, numerator) != (expected_denominator, expected_numerator):
            raise QualityRunError(
                f"집계 SQL {index}행: 원본 CSV의 독립 집계와 불일치 "
                f"(SQL={denominator}/{numerator}, 기준={expected_denominator}/{expected_numerator})"
            )
        expected_rate = round_rate(numerator, denominator)
        if expected_rate is None:
            if rate is not None:
                raise QualityRunError(f"집계 SQL {index}행: 분모 0이면 비율은 NULL이어야 합니다")
        elif (isinstance(rate, bool) or not isinstance(rate, (float, int, Decimal))
              or not math.isfinite(float(rate))
              or abs(float(rate) - expected_rate) > 1e-8):
            raise QualityRunError(f"집계 SQL {index}행: 비율 계산 오류")
        validated.append(dict(zip(OUTPUT_COLUMNS, (
            *expected_key, denominator, numerator, expected_rate
        ))))

    # Explicitly confirm the overall three groups reconcile with the mart.
    overall_rows = validated[:3]
    if (sum(x["denominator"] for x in overall_rows) != overall["w1_active"]
            or sum(x["numerator"] for x in overall_rows) != overall["w2_returned"]):
        raise QualityRunError("전체 세 집단 합계가 첫 주 활성·재방문 합계와 다릅니다")

    # Explicitly confirm each cohort's three group sums to the overall totals.
    cohort_rows = validated[3:]
    if (sum(x["denominator"] for x in cohort_rows) != overall["w1_active"]
            or sum(x["numerator"] for x in cohort_rows) != overall["w2_returned"]):
        raise QualityRunError("개설기별 세 집단 합계가 전체 합계와 다릅니다")
    return validated


def run(mart: Path, sql: Path, output: Path) -> int:
    if not mart.is_file() or not sql.is_file():
        raise QualityRunError("--mart 또는 --sql 입력 파일이 없습니다")
    if output.resolve() in {mart.resolve(), sql.resolve()}:
        raise QualityRunError("--output은 CSV 또는 SQL 입력 파일과 달라야 합니다")
    sql_text = sql.read_text(encoding="utf-8-sig")
    if not sql_text.strip():
        raise QualityRunError("집계 SQL이 비어 있습니다")

    try:
        import duckdb
    except ImportError as exc:
        raise QualityRunError("DuckDB 미설치: python -m pip install duckdb") from exc

    before_digest = sha256_file(mart)
    try:
        with duckdb.connect(":memory:") as con:
            overall, expected_keys, counts = load_and_summarize(con, mart)
            if sha256_file(mart) != before_digest:
                raise QualityRunError("실행 중 CSV 입력 파일이 변경되었습니다")
            result = con.execute(sql_text)
            validated = validate_sql_result(result, expected_keys, counts, overall)
    except duckdb.Error as exc:
        raise QualityRunError(f"DuckDB SQL/적재 오류: {exc}") from exc

    # Final input check: never commit a JSON report for a changed CSV.
    if sha256_file(mart) != before_digest:
        raise QualityRunError("실행 중 CSV 입력 파일이 변경되었습니다")
    report = {
        "schema_version": 1,
        "scope": "descriptive_activity_groups",
        "input_sha256": before_digest,
        "overall": overall,
        "rows": validated,
    }
    save_json_atomic(output, report)
    print(f"eligible={overall['eligible']}  w1_active={overall['w1_active']} "
          f"w2_returned={overall['w2_returned']}  "
          f"return_rate_pct={overall['return_rate_pct']}")
    print(f"rows={len(validated)}  json={output}")
    return 0


def main() -> int:
    parser = QualityArgumentParser(description="수강 건별 mart에서 전체·개설기별 활동 집계 JSON 생성")
    parser.add_argument("--mart", required=True, type=Path, help="기존 build_mart.py 출력 CSV")
    parser.add_argument("--sql", required=True, type=Path, help="aggregate.sql")
    parser.add_argument("--output", required=True, type=Path, help="집계 JSON 결과 경로")
    args = parser.parse_args()
    try:
        return run(args.mart, args.sql, args.output)
    except (QualityRunError, OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"ERROR: 집계 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

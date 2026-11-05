#!/usr/bin/env python3
"""Export an OULAD enrollment mart after re-running all 20 quality rules.

Read-only DuckDB inputs. Writes only the requested CSV, atomically.
Exit codes: 0=mart created after PASS/REVIEW, 2=quality BLOCK,
            1=arguments, input, SQL, result, or output error.

Uses validate_results() and decide_gate() from the earlier run_quality_full.py.
"""

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path

from run_quality_full import (
    QualityArgumentParser,
    QualityRunError,
    decide_gate,
    validate_results,
)

COLUMNS = (
    "code_module",
    "code_presentation",
    "id_student",
    "w1_days",
    "w2_active",
    "later_active",
    "first_day",
    "date_unregistration",
    "first_content",
    "first_clicks_raw",
    "first_clicks_exact",
    "first_clicks_max",
)
KEY_COLUMNS = 3
BATCH_SIZE = 4096


def read_sql(path: Path, label: str) -> str:
    if not path.is_file():
        raise QualityRunError(f"{label} 파일이 없습니다: {path}")
    sql = path.read_text(encoding="utf-8-sig")
    if not sql.strip():
        raise QualityRunError(f"{label} 파일이 비어 있습니다: {path}")
    return sql


def check_row(row, previous_key, row_number: int):
    """Reject malformed results before committing the CSV to its final path."""
    if len(row) != len(COLUMNS):
        raise QualityRunError(f"mart {row_number}행: 열 개수 오류")
    module, presentation, student, w1, w2, later, first_day, withdrawal, content, raw, exact, max_clicks = row
    if module is None or presentation is None or student is None:
        raise QualityRunError(f"mart {row_number}행: 수강 건 키가 NULL입니다")
    key = (module, presentation, student)
    if previous_key is not None and key <= previous_key:
        raise QualityRunError(f"mart {row_number}행: 키 중복 또는 정렬 오류: {key!r}")
    if type(w1) is not int or not 0 <= w1 <= 7:
        raise QualityRunError(f"mart {row_number}행: w1_days 범위 오류: {w1!r}")
    for label, value in (("w2_active", w2), ("later_active", later), ("first_content", content)):
        if type(value) is not int or value not in (0, 1):
            raise QualityRunError(f"mart {row_number}행: {label}은 0 또는 1이어야 합니다")
    if w1 == 0:
        if first_day is not None or content != 0 or any(v != 0 for v in (raw, exact, max_clicks)):
            raise QualityRunError(f"mart {row_number}행: 첫 주 비활성 값이 일치하지 않습니다")
    elif type(first_day) is not int or not 0 <= first_day <= 6:
        raise QualityRunError(f"mart {row_number}행: first_day 범위 오류: {first_day!r}")
    if withdrawal is not None and type(withdrawal) is not int:
        raise QualityRunError(f"mart {row_number}행: date_unregistration 형식 오류")
    if any(type(v) is not int or v < 0 for v in (raw, exact, max_clicks)):
        raise QualityRunError(f"mart {row_number}행: 클릭 합계는 0 이상 정수여야 합니다")
    if not (max_clicks <= exact <= raw):
        raise QualityRunError(f"mart {row_number}행: 클릭 집계 순서 위반")
    return key


def export_csv_atomic(result, output: Path):
    """Stream result rows to a temporary CSV and replace only after validation."""
    columns = tuple(desc[0] for desc in (result.description or ()))
    if columns != COLUMNS:
        raise QualityRunError(f"mart SQL 열 오류: 기대={COLUMNS!r}, 실제={columns!r}")

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    count = active = returned = 0
    previous_key = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", prefix=".mart-",
            suffix=".csv.tmp", dir=output.parent, delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            while True:
                batch = result.fetchmany(BATCH_SIZE)
                if not batch:
                    break
                for row in batch:
                    previous_key = check_row(row, previous_key, count + 1)
                    writer.writerow(row)
                    count += 1
                    if row[3] > 0:
                        active += 1
                        if row[4] == 1:
                            returned += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, output)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    return count, active, returned


def run(db: Path, quality_sql: Path, mart_sql: Path, output: Path, strict: bool = False) -> int:
    if not db.is_file():
        raise QualityRunError(f"기존 DuckDB 파일이 없습니다: {db}")
    # Resolve symlink targets as well: never replace a DB or either SQL input.
    inputs = {p.resolve() for p in (db, quality_sql, mart_sql)}
    if output.resolve() in inputs:
        raise QualityRunError("--output은 DB 또는 SQL 입력 파일과 다른 경로여야 합니다")

    quality_text = read_sql(quality_sql, "품질 SQL")
    mart_text = read_sql(mart_sql, "mart SQL")

    try:
        import duckdb
    except ImportError as exc:
        raise QualityRunError("DuckDB 미설치: python -m pip install duckdb") from exc

    try:
        con = duckdb.connect(str(db), read_only=True)
        try:
            check_result = con.execute(quality_text)
            checks = validate_results(check_result.description, check_result.fetchall())
            gate = decide_gate(checks)
            print(f"quality_gate={gate}  strict={strict}")
            if gate == "BLOCK":
                print("BLOCK: 품질 검사에서 차단 규칙이 발견되어 mart를 생성하지 않습니다")
                return 2

            mart_result = con.execute(mart_text, {"strict": strict})
            count, active, returned = export_csv_atomic(mart_result, output)
        finally:
            con.close()
    except duckdb.Error as exc:
        raise QualityRunError(f"DuckDB 연결 또는 SQL 실행 오류: {exc}") from exc

    print(f"eligible_enrollments={count}")
    print(f"first_week_active_enrollments={active}")
    print(f"next_week_active_among_first_week_active={returned}")
    print(f"CSV 저장: {output}")
    return 0


def main() -> int:
    parser = QualityArgumentParser(description="품질 20규칙 검증 후 수강 건별 mart CSV 생성")
    parser.add_argument("--db", required=True, type=Path, help="기존 전용 DuckDB 파일")
    parser.add_argument("--quality-sql", required=True, type=Path, help="quality_full.sql 경로")
    parser.add_argument("--mart-sql", required=True, type=Path, help="build_mart.sql 경로")
    parser.add_argument("--output", required=True, type=Path, help="결과 CSV 경로")
    parser.add_argument("--strict", action="store_true", help="등록·탈퇴 기간 밖 활동 제외")
    args = parser.parse_args()
    try:
        return run(args.db, args.quality_sql, args.mart_sql, args.output, args.strict)
    except (QualityRunError, OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"ERROR: mart 생성 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

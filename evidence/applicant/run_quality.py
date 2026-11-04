#!/usr/bin/env python3
"""Run the previously submitted quality.sql against an existing DuckDB database.

Exit codes: 0 = PASS/REVIEW, 2 = BLOCK, 1 = execution/input/result error.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

RULE_IDS = (
    "registration_missing_date",
    "event_exact_repeat",
    "event_unknown_student",
)


class QualityRunError(Exception):
    """Invalid input or query result; no successful report should be written."""


class QualityArgumentParser(argparse.ArgumentParser):
    """Reserve exit status 2 exclusively for a successful BLOCK judgment."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, f"ERROR: 인자 오류: {message}\n")


def validate_results(description, rows):
    """Require precisely the two expected columns and one nonnegative count per rule."""
    columns = tuple(column[0] for column in description or ())
    if columns != ("rule_id", "issue_count"):
        raise QualityRunError(
            f"SQL 결과 열 오류: 기대=('rule_id', 'issue_count'), 실제={columns}"
        )

    if len(rows) != len(RULE_IDS):
        raise QualityRunError(f"SQL 결과 행 수 오류: 기대=3, 실제={len(rows)}")

    found = {}
    for rule_id, count in rows:
        if not isinstance(rule_id, str) or rule_id not in RULE_IDS:
            raise QualityRunError(f"예상하지 않은 rule_id: {rule_id!r}")
        if rule_id in found:
            raise QualityRunError(f"중복된 rule_id: {rule_id}")
        if type(count) is not int or count < 0:
            raise QualityRunError(f"{rule_id}: issue_count는 0 이상의 정수여야 합니다 (실제={count!r})")
        found[rule_id] = count

    missing = set(RULE_IDS) - set(found)
    if missing:
        raise QualityRunError(f"누락된 rule_id: {sorted(missing)}")

    return [{"rule_id": rule_id, "issue_count": found[rule_id]} for rule_id in RULE_IDS]


def decide_gate(checks):
    counts = {entry["rule_id"]: entry["issue_count"] for entry in checks}
    if counts["event_unknown_student"] > 0:
        return "BLOCK"
    if counts["registration_missing_date"] > 0 or counts["event_exact_repeat"] > 0:
        return "REVIEW"
    return "PASS"


def save_json_atomic(output: Path, report: dict):
    """Replace the result only after a complete and successful query/validation."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp", prefix=".quality-",
            dir=output.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(db: Path, sql: Path, output: Path):
    if not db.is_file():
        raise QualityRunError(f"DB 파일이 없습니다: {db}")
    if not sql.is_file():
        raise QualityRunError(f"SQL 파일이 없습니다: {sql}")
    if output.resolve() in {db.resolve(), sql.resolve()}:
        raise QualityRunError("--output은 --db 또는 --sql과 다른 파일이어야 합니다")

    sql_text = sql.read_text(encoding="utf-8")
    if not sql_text.strip():
        raise QualityRunError(f"SQL 파일이 비어 있습니다: {sql}")

    try:
        import duckdb
    except ImportError as exc:
        raise QualityRunError("DuckDB가 설치되지 않았습니다: python -m pip install duckdb") from exc

    try:
        con = duckdb.connect(str(db), read_only=True)
        try:
            cursor = con.execute(sql_text)
            checks = validate_results(cursor.description, cursor.fetchall())
        finally:
            con.close()
    except duckdb.Error as exc:
        raise QualityRunError(f"DuckDB 연결 또는 SQL 실행 오류: {exc}") from exc

    gate = decide_gate(checks)
    report = {"scope": "first_three_rules", "gate": gate, "checks": checks}
    save_json_atomic(output, report)

    print(f"scope={report['scope']}  gate={gate}")
    for check in checks:
        print(f"{check['rule_id']}: {check['issue_count']}")
    print(f"JSON 저장: {output}")
    return 2 if gate == "BLOCK" else 0


def main() -> int:
    parser = QualityArgumentParser(description="DuckDB 품질 규칙 3개 실행 및 JSON 결과 저장")
    parser.add_argument("--db", type=Path, required=True, help="기존 DuckDB 파일")
    parser.add_argument("--sql", type=Path, required=True, help="기존 quality.sql 파일")
    parser.add_argument("--output", type=Path, required=True, help="결과 JSON 저장 경로")
    args = parser.parse_args()
    try:
        return run(args.db, args.sql, args.output)
    except (QualityRunError, OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: 품질 검사 실행 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

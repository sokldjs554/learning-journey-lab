#!/usr/bin/env python3
"""Run the existing 20-rule quality_full.sql against a read-only DuckDB file.

Exit status: 0=PASS/REVIEW, 2=valid BLOCK, 1=input/query/result/output error.
Preserves the earlier run_quality.py argument and atomic-report conventions.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# Fixed contract from docs/applicant-full-quality-spec.md; do not trust SQL labels.
EXPECTED_RULES = (
    ("registration_missing_date", "review"),
    ("event_exact_repeat", "review"),
    ("event_unknown_student", "block"),
    ("event_required_null", "block"),
    ("event_nonpositive_click", "block"),
    ("event_daily_key_repeat", "review"),
    ("event_unknown_site", "block"),
    ("registration_inverted_dates", "block"),
    ("registration_key_repeat", "block"),
    ("site_key_repeat", "block"),
    ("course_key_repeat", "block"),
    ("event_before_registration", "review"),
    ("event_after_withdrawal", "review"),
    ("event_after_course", "review"),
    ("registration_required_null", "block"),
    ("site_required_null", "block"),
    ("course_required_null", "block"),
    ("course_invalid_length", "block"),
    ("registration_unknown_course", "block"),
    ("site_unknown_course", "block"),
)
EXPECTED_SEVERITY = dict(EXPECTED_RULES)


class QualityRunError(Exception):
    """Invalid input, query result, or output operation."""


class QualityArgumentParser(argparse.ArgumentParser):
    """Use status 1 for argument errors (2 is reserved for BLOCK)."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, f"ERROR: 인자 오류: {message}\n")


def validate_results(description, rows):
    """Validate exact 3-column schema, 20 rule IDs, severity, and counts."""
    columns = tuple(column[0] for column in (description or ()))
    if columns != ("rule_id", "severity", "issue_count"):
        raise QualityRunError(f"SQL 결과 열 오류: {columns!r}")

    if len(rows) != len(EXPECTED_RULES):
        raise QualityRunError(
            f"SQL 결과 행 수 오류: 기대={len(EXPECTED_RULES)}, 실제={len(rows)}"
        )

    found = {}
    for rule_id, severity, count in rows:
        if not isinstance(rule_id, str) or rule_id not in EXPECTED_SEVERITY:
            raise QualityRunError(f"예상하지 않은 rule_id: {rule_id!r}")
        if rule_id in found:
            raise QualityRunError(f"중복된 rule_id: {rule_id}")
        if severity != EXPECTED_SEVERITY[rule_id]:
            raise QualityRunError(
                f"{rule_id}: severity 오류: 기대={EXPECTED_SEVERITY[rule_id]!r}, "
                f"실제={severity!r}"
            )
        # bool is an int subclass, so exact type validation is necessary.
        if type(count) is not int or count < 0:
            raise QualityRunError(
                f"{rule_id}: issue_count는 0 이상의 정수여야 합니다 (실제={count!r})"
            )
        found[rule_id] = count

    missing = set(EXPECTED_SEVERITY) - set(found)
    if missing:
        raise QualityRunError(f"누락된 rule_id: {sorted(missing)}")

    return [
        {"rule_id": rule_id, "severity": severity, "issue_count": found[rule_id]}
        for rule_id, severity in EXPECTED_RULES
    ]


def decide_gate(checks):
    """BLOCK takes precedence over REVIEW, irrespective of SQL result order."""
    if any(c["severity"] == "block" and c["issue_count"] > 0 for c in checks):
        return "BLOCK"
    if any(c["severity"] == "review" and c["issue_count"] > 0 for c in checks):
        return "REVIEW"
    return "PASS"


def save_json_atomic(output: Path, report: dict):
    """Write only validated reports, replacing an old report atomically."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".quality-full-", suffix=".tmp",
            dir=output.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(db: Path, sql: Path, output: Path):
    if not db.is_file():
        raise QualityRunError(f"기존 DuckDB 파일이 없습니다: {db}")
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
        raise QualityRunError(
            "DuckDB가 설치되지 않았습니다: python -m pip install duckdb"
        ) from exc

    try:
        connection = duckdb.connect(str(db), read_only=True)
        try:
            result = connection.execute(sql_text)
            checks = validate_results(result.description, result.fetchall())
        finally:
            connection.close()
    except duckdb.Error as exc:
        raise QualityRunError(f"DuckDB 연결 또는 SQL 실행 오류: {exc}") from exc

    gate = decide_gate(checks)
    report = {"scope": "full_quality_20", "gate": gate, "checks": checks}
    save_json_atomic(output, report)

    print(f"scope={report['scope']}  gate={gate}")
    for check in checks:
        print(f"{check['rule_id']} [{check['severity']}]: {check['issue_count']}")
    print(f"JSON 저장: {output}")
    return 2 if gate == "BLOCK" else 0


def main() -> int:
    parser = QualityArgumentParser(
        description="DuckDB 전체 품질 규칙 20개 실행 및 JSON 저장"
    )
    parser.add_argument("--db", type=Path, required=True, help="기존 DuckDB 파일")
    parser.add_argument("--sql", type=Path, required=True, help="quality_full.sql 경로")
    parser.add_argument("--output", type=Path, required=True, help="결과 JSON 경로")
    args = parser.parse_args()
    try:
        return run(args.db, args.sql, args.output)
    except (QualityRunError, OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: 전체 품질 검사 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

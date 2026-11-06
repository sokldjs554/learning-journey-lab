#!/usr/bin/env python3
"""Validate two OULAD mart CSVs, read history, calculate and save statistics.

Exit status: 0=success, 1=argument/input/DB/calculation/output error.
The input DuckDB is opened read-only; generated JSON contains no learner IDs.

Reuses the existing 12-column mart reader and atomic JSON output helper.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd

from build_mart import COLUMNS as MART_COLUMNS
from learning_stats import calculate_statistics
from run_aggregate import parse_row, sha256_file
from run_quality_full import (
    QualityArgumentParser,
    QualityRunError,
    save_json_atomic,
)

REGISTRATION_COLUMNS = ("code_module", "code_presentation", "id_student")


def read_mart(path: Path, label: str) -> pd.DataFrame:
    """Read validated 12-column CSV; keep optional dates as None."""
    if not path.is_file():
        raise QualityRunError(f"{label} CSV 파일이 없습니다: {path}")
    rows = []
    seen_keys = set()
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            if header != list(MART_COLUMNS):
                raise QualityRunError(
                    f"{label}: CSV 12열 헤더 오류: 기대={MART_COLUMNS!r}, 실제={header!r}"
                )
            for line, values in enumerate(reader, start=2):
                row = parse_row(values, line)
                key = row[:3]
                if key in seen_keys:
                    raise QualityRunError(f"{label}: 중복 수강 건 {line}행: {key!r}")
                seen_keys.add(key)
                rows.append(row)
    except (csv.Error, UnicodeError) as exc:
        raise QualityRunError(f"{label}: CSV 읽기 오류: {exc}") from exc

    # Use object dtype for empty frames to retain all 12 column names.
    frame = pd.DataFrame.from_records(rows, columns=MART_COLUMNS)
    if frame.empty:
        frame = frame.astype(object)
    return frame


def ensure_matching_marts(mart: pd.DataFrame, strict: pd.DataFrame) -> None:
    """One row per enrollment in each CSV, same keys and withdrawal dates."""
    keyed_basic = {
        (r.code_module, r.code_presentation, int(r.id_student)): r.date_unregistration
        for r in mart.itertuples(index=False)
    }
    keyed_strict = {
        (r.code_module, r.code_presentation, int(r.id_student)): r.date_unregistration
        for r in strict.itertuples(index=False)
    }
    if keyed_basic.keys() != keyed_strict.keys():
        missing = len(keyed_basic.keys() - keyed_strict.keys())
        extra = len(keyed_strict.keys() - keyed_basic.keys())
        raise QualityRunError(
            f"기본/strict CSV의 수강 건 키 불일치: strict 누락={missing}, 추가={extra}"
        )
    for key, date in keyed_basic.items():
        other = keyed_strict[key]
        # pandas sometimes represents optional integer as NaN on mixed columns.
        if pd.isna(date) and pd.isna(other):
            continue
        if pd.isna(date) != pd.isna(other) or date != other:
            raise QualityRunError(f"기본/strict 탈퇴일 불일치: 수강 건 {key!r}")


def read_registration_history(db: Path, expected_keys: set[tuple]) -> set[int]:
    """Read *all* registrations from existing DB, including ineligible 2013.

    Reject null or duplicate registration keys, and any mart row without a
    corresponding registration. Different presentations for one ID are valid.
    """
    if not db.is_file():
        raise QualityRunError(f"기존 DuckDB 파일이 없습니다: {db}")
    try:
        import duckdb
    except ImportError as exc:
        raise QualityRunError("DuckDB 미설치: python -m pip install duckdb") from exc

    try:
        connection = duckdb.connect(str(db), read_only=True)
        try:
            cursor = connection.execute(
                "SELECT code_module, code_presentation, id_student FROM studentRegistration"
            )
            columns = tuple(item[0] for item in (cursor.description or ()))
            if columns != REGISTRATION_COLUMNS:
                raise QualityRunError(f"studentRegistration 열 오류: {columns!r}")

            registrations = set()
            historical = set()
            while True:
                batch = cursor.fetchmany(4096)
                if not batch:
                    break
                for row in batch:
                    if len(row) != 3:
                        raise QualityRunError("studentRegistration 등록 키의 열 개수 오류")
                    module, presentation, learner = row
                    if (not isinstance(module, str) or not module.strip()
                            or not isinstance(presentation, str) or not presentation.strip()
                            or type(learner) is not int):
                        raise QualityRunError(f"studentRegistration 등록 키 결측/형식 오류: {row!r}")
                    key = (module, presentation, learner)
                    if key in registrations:
                        raise QualityRunError(f"studentRegistration 중복 복합키: {key!r}")
                    registrations.add(key)
                    if presentation.startswith("2013"):
                        historical.add(learner)
        finally:
            connection.close()
    except duckdb.Error as exc:
        raise QualityRunError(f"DuckDB 읽기 전용 조회 실패: {exc}") from exc

    missing = expected_keys - registrations
    if missing:
        example = min(missing)
        raise QualityRunError(
            f"분석표 수강 건 {len(missing)}개가 studentRegistration에 없습니다: {example!r}"
        )
    return historical


def run(mart_path: Path, strict_path: Path, db: Path, output: Path) -> int:
    input_paths = (mart_path, strict_path, db)
    if not all(path.is_file() for path in input_paths):
        raise QualityRunError("--mart, --strict-mart, --db 입력 파일이 모두 있어야 합니다")
    if output.resolve() in {path.resolve() for path in input_paths}:
        raise QualityRunError("--output이 CSV 또는 DB 입력 파일을 덮어쓸 수 없습니다")
    if output.exists() and any(output.samefile(path) for path in input_paths):
        raise QualityRunError("--output이 CSV 또는 DB와 동일한 파일을 가리킵니다")

    before_hashes = {
        "mart": sha256_file(mart_path),
        "strict_mart": sha256_file(strict_path),
        "db": sha256_file(db),
    }
    mart = read_mart(mart_path, "기본")
    strict = read_mart(strict_path, "strict")
    ensure_matching_marts(mart, strict)

    keys = set(zip(mart["code_module"], mart["code_presentation"], mart["id_student"]))
    previous_2013 = read_registration_history(db, keys)
    calculations = calculate_statistics(mart, strict, previous_2013)
    report = {
        "schema_version": 1,
        "scope": "observational_statistics",
        "input_sha256": before_hashes,
        **calculations,
    }
    # No NaN/Infinity may be serialized as JSON numbers. Catch before writing.
    json.dumps(report, allow_nan=False)
    after_hashes = {
        "mart": sha256_file(mart_path),
        "strict_mart": sha256_file(strict_path),
        "db": sha256_file(db),
    }
    if after_hashes != before_hashes:
        raise QualityRunError("실행 중 입력 CSV 또는 DB 내용이 변경되어 JSON 저장을 중단합니다")

    save_json_atomic(output, report)
    overall = report["overall"]
    sensitivity = report["strict_sensitivity"]
    print(f"eligible={overall['eligible']}  w1_active={overall['w1_active']} "
          f"w2_returned={overall['w2_returned']}  "
          f"return_rate={overall['return_rate']}")
    print(f"cohorts={len(report['cohorts'])}  "
          f"strict_w1={sensitivity['w1_active']}  "
          f"strict_w2={sensitivity['w2_returned']}")
    print(f"JSON 저장: {output}")
    return 0


def main() -> int:
    parser = QualityArgumentParser(description="OULAD 학습자 단위 통계·민감도 JSON")
    parser.add_argument("--mart", required=True, type=Path, help="기본 정책 12열 분석표 CSV")
    parser.add_argument("--strict-mart", required=True, type=Path, help="strict 정책 분석표 CSV")
    parser.add_argument("--db", required=True, type=Path, help="원본 등록 정보가 있는 DuckDB")
    parser.add_argument("--output", required=True, type=Path, help="결과 JSON 파일")
    args = parser.parse_args()
    try:
        return run(args.mart, args.strict_mart, args.db, args.output)
    except (QualityRunError, OSError, ValueError, TypeError, UnicodeError, OverflowError) as exc:
        print(f"ERROR: 통계 실행 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

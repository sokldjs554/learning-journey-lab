#!/usr/bin/env python3
"""Validate OULAD CSV files, then load all seven into a DuckDB database.

Requires: duckdb (pip install duckdb)
Reuses load_manifest() and check_files() from validate_sources.py.
"""

import argparse
import sys
from pathlib import Path

from validate_sources import check_files, load_manifest


def load_csv_tables(connection, files: dict, csv_dir: Path) -> list[tuple[str, int]]:
    """Load all tables atomically; return (table name, row count) pairs."""
    loaded = []
    connection.execute("BEGIN TRANSACTION")
    try:
        for filename in sorted(files):
            table_name = Path(filename).stem
            # The manifest validator limits names to seven known CSV filenames.
            identifier = '"' + table_name.replace('"', '""') + '"'
            connection.execute(
                f"CREATE OR REPLACE TABLE {identifier} AS "
                "SELECT * FROM read_csv_auto(?, header = true, nullstr = ['', '?'])",
                [str(csv_dir / filename)],
            )
            count = connection.execute(
                f"SELECT COUNT(*) FROM {identifier}"
            ).fetchone()[0]
            loaded.append((table_name, count))
        connection.execute("COMMIT")
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass  # Preserve the original loading error.
        raise
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify seven OULAD CSV files, then load them into DuckDB."
    )
    parser.add_argument("--manifest", type=Path, required=True, help="data/manifest.json path")
    parser.add_argument("--csv-dir", type=Path, required=True, help="OULAD raw CSV folder")
    parser.add_argument("--db", type=Path, default=Path("oulad.duckdb"),
                        help="Output DuckDB database (default: ./oulad.duckdb)")
    args = parser.parse_args()

    try:
        files = load_manifest(args.manifest)
    except (OSError, ValueError, UnicodeError) as error:
        print(f"FAIL: manifest 읽기/형식 오류: {error}", file=sys.stderr)
        return 2

    if check_files(files, args.csv_dir) != 0:
        print("FAIL: 원본 검증 실패. DuckDB 적재를 시작하지 않았습니다.", file=sys.stderr)
        return 1

    # Do not open or modify the database unless all seven files passed.
    try:
        import duckdb
    except ImportError:
        print("FAIL: DuckDB 미설치. 'python -m pip install duckdb'로 설치하세요.",
              file=sys.stderr)
        return 3

    connection = None
    try:
        connection = duckdb.connect(str(args.db))
        loaded = load_csv_tables(connection, files, args.csv_dir)
    except Exception as error:
        print(f"FAIL: DuckDB 적재 실패(트랜잭션 롤백): {error}", file=sys.stderr)
        return 3
    finally:
        if connection is not None:
            connection.close()

    print(f"DuckDB 적재 완료: {args.db}")
    for table_name, row_count in loaded:
        print(f"{table_name}: {row_count:,}행")
    print(f"총 {len(loaded)}개 테이블 적재 성공")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Run the submitted OULAD pipeline in isolated, auditable run directories.

Stages: source verification -> DuckDB load -> 20-rule quality -> base/strict
mart -> descriptive aggregation -> observational statistics.

Exit status: 0=success, 2=validated quality/mart BLOCK, 1=error,
             130=interrupted. Existing data and previous runs are never reused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


CHUNK_SIZE = 1024 * 1024
SCRIPTS_AND_SQL = (
    "run_pipeline.py",
    "validate_sources.py",
    "load_sources.py",
    "run_quality_full.py",
    "quality_full.sql",
    "build_mart.py",
    "build_mart.sql",
    "run_aggregate.py",
    "aggregate.sql",
    "run_statistics.py",
    "learning_stats.py",
)
STAGES = (
    "validate_sources", "load_sources", "quality", "mart_base",
    "mart_strict", "aggregate", "statistics",
)
BLOCK_STAGES = frozenset(("quality", "mart_base", "mart_strict"))
ARTIFACT_NAMES = (
    "oulad.duckdb", "quality.json", "enrollment_mart.csv",
    "enrollment_mart_strict.csv", "activity-groups.json", "statistics.json",
)


class PipelineError(Exception):
    """Input, process, report, consistency, or storage error."""


class PipelineParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, f"ERROR: 인자 오류: {message}\n")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_record(path: Path, record: dict) -> None:
    """Write an entire checkpoint then atomically replace the prior record."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".run_record-", suffix=".tmp",
            dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(record, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def validate_output_root(output_root: Path, raw_dir: Path, manifest: Path, code_dir: Path) -> None:
    """Reject output placement that can overwrite raw inputs or script files."""
    if is_within(output_root, raw_dir):
        raise PipelineError("--output-dir은 --raw-dir 자신이나 그 하위일 수 없습니다")
    protected = {manifest, *(code_dir / filename for filename in SCRIPTS_AND_SQL)}
    if output_root in protected:
        raise PipelineError("출력 폴더가 manifest 또는 제출 코드 파일과 충돌합니다")
    if output_root.exists() and not output_root.is_dir():
        raise PipelineError(f"출력 폴더 경로가 디렉터리가 아닙니다: {output_root}")
    runs = (output_root / "runs").resolve()
    if is_within(runs, raw_dir) or runs in protected:
        raise PipelineError("출력 runs 경로가 원본 또는 제출 파일과 충돌합니다")
    if runs.exists() and not runs.is_dir():
        raise PipelineError(f"실행 폴더 경로가 디렉터리가 아닙니다: {runs}")


def create_run_dir(output_root: Path, raw_dir: Path) -> tuple[str, Path]:
    runs = output_root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    if is_within(runs.resolve(), raw_dir):
        raise PipelineError("runs 경로가 원본 폴더를 가리킵니다")
    for _ in range(8):
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + secrets.token_hex(5)
        run_dir = runs / run_id
        try:
            run_dir.mkdir(exist_ok=False)
        except FileExistsError:
            continue
        (run_dir / "logs").mkdir()
        return run_id, run_dir
    raise PipelineError("고유 실행 폴더를 생성하지 못했습니다")


def input_inventory(manifest: Path, code_dir: Path) -> tuple[str, dict]:
    """Hash the actual existing input files; report missing code before execution."""
    if not manifest.is_file():
        raise PipelineError(f"manifest 파일이 없습니다: {manifest}")
    for filename in SCRIPTS_AND_SQL:
        path = code_dir / filename
        if not path.is_file():
            raise PipelineError(f"제출 Python/SQL 파일이 없습니다: {path}")
    return sha256_file(manifest), {
        filename: sha256_file(code_dir / filename) for filename in SCRIPTS_AND_SQL
    }


def commands(code_dir: Path, manifest: Path, raw: Path, run_dir: Path) -> list[tuple[str, list[str], str | None]]:
    db = run_dir / "oulad.duckdb"
    base = run_dir / "enrollment_mart.csv"
    strict = run_dir / "enrollment_mart_strict.csv"
    quality_sql = code_dir / "quality_full.sql"
    mart_sql = code_dir / "build_mart.sql"
    return [
        ("validate_sources", ["validate_sources.py", "--manifest", str(manifest), "--csv-dir", str(raw)], None),
        ("load_sources", ["load_sources.py", "--manifest", str(manifest), "--csv-dir", str(raw), "--db", str(db)], "oulad.duckdb"),
        ("quality", ["run_quality_full.py", "--db", str(db), "--sql", str(quality_sql), "--output", str(run_dir / "quality.json")], "quality.json"),
        ("mart_base", ["build_mart.py", "--db", str(db), "--quality-sql", str(quality_sql), "--mart-sql", str(mart_sql), "--output", str(base)], "enrollment_mart.csv"),
        ("mart_strict", ["build_mart.py", "--db", str(db), "--quality-sql", str(quality_sql), "--mart-sql", str(mart_sql), "--output", str(strict), "--strict"], "enrollment_mart_strict.csv"),
        ("aggregate", ["run_aggregate.py", "--mart", str(base), "--sql", str(code_dir / "aggregate.sql"), "--output", str(run_dir / "activity-groups.json")], "activity-groups.json"),
        ("statistics", ["run_statistics.py", "--mart", str(base), "--strict-mart", str(strict), "--db", str(db), "--output", str(run_dir / "statistics.json")], "statistics.json"),
    ]


def safe_artifact(run_dir: Path, filename: str) -> Path:
    path = run_dir / filename
    if path.is_symlink() or not path.is_file() or not is_within(path.resolve(), run_dir.resolve()):
        raise PipelineError(f"필수 산출물이 없거나 실행 폴더 밖을 가리킵니다: {filename}")
    return path


def load_json(run_dir: Path, filename: str) -> dict:
    path = safe_artifact(run_dir, filename)
    def refuse_constant(value: str):
        raise ValueError(f"JSON에 허용되지 않는 값: {value}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            result = json.load(handle, parse_constant=refuse_constant)
    except (OSError, UnicodeError, ValueError) as exc:
        raise PipelineError(f"{filename} 읽기/JSON 오류: {exc}") from exc
    if not isinstance(result, dict):
        raise PipelineError(f"{filename}의 최상위 구조가 객체가 아닙니다")
    return result


def validate_quality(run_dir: Path, child_exit_code: int) -> tuple[str, list[dict]]:
    from run_quality_full import decide_gate, validate_results, QualityRunError

    report = load_json(run_dir, "quality.json")
    if report.get("scope") != "full_quality_20" or not isinstance(report.get("checks"), list):
        raise PipelineError("quality.json의 20규칙 scope/checks 계약이 잘못됐습니다")
    try:
        tuples = []
        for item in report["checks"]:
            if not isinstance(item, dict) or not {"rule_id", "severity", "issue_count"}.issubset(item):
                raise PipelineError("quality.json의 check 항목이 잘못됐습니다")
            tuples.append((item["rule_id"], item["severity"], item["issue_count"]))
        checks = validate_results(
            [("rule_id",), ("severity",), ("issue_count",)], tuples
        )
    except QualityRunError as exc:
        raise PipelineError(f"quality.json의 검사 결과 계약 오류: {exc}") from exc
    gate = decide_gate(checks)
    if report.get("gate") != gate:
        raise PipelineError(f"quality.json gate 불일치: 기록={report.get('gate')!r}, 계산={gate}")
    if (child_exit_code == 2) != (gate == "BLOCK"):
        raise PipelineError(f"품질 자식 종료 코드({child_exit_code})와 gate({gate}) 불일치")
    return gate, checks


def require_count(data: dict, field: str, label: str) -> int:
    value = data.get(field)
    if type(value) is not int or value < 0:
        raise PipelineError(f"{label}.{field}: 0 이상의 정수가 필요합니다")
    return value


def expected_percent(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return float(
        (Decimal(100 * numerator) / Decimal(denominator)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
    )


def validate_rate(value, expected, label: str, tolerance: float = 1e-10) -> None:
    if expected is None:
        if value is not None:
            raise PipelineError(f"{label}는 분모 0이므로 null이어야 합니다")
    elif (isinstance(value, bool) or not isinstance(value, (float, int))
          or not math.isfinite(float(value)) or not math.isclose(float(value), expected, rel_tol=0, abs_tol=tolerance)):
        raise PipelineError(f"{label} 불일치: 기대={expected}, 실제={value!r}")


def validate_final(run_dir: Path, manifest: Path, original_manifest_hash: str,
                   code_dir: Path, code_hashes: dict, gate: str) -> tuple[dict, dict]:
    """Verify artifacts, input hashes, overall reconciliation and rate units."""
    paths = {name: safe_artifact(run_dir, name) for name in ARTIFACT_NAMES}
    aggregate = load_json(run_dir, "activity-groups.json")
    stats = load_json(run_dir, "statistics.json")

    if aggregate.get("schema_version") != 1 or aggregate.get("scope") != "descriptive_activity_groups":
        raise PipelineError("집계 JSON의 schema_version/scope 계약 오류")
    if stats.get("schema_version") != 1 or stats.get("scope") != "observational_statistics":
        raise PipelineError("통계 JSON의 schema_version/scope 계약 오류")
    required_sections = (
        "overall", "cohorts", "temporal", "first_day_strata",
        "click_sensitivity", "transition", "strict_sensitivity",
    )
    if any(section not in stats for section in required_sections):
        raise PipelineError("통계 JSON의 필수 분석 섹션이 누락됐습니다")
    if not isinstance(aggregate.get("rows"), list) or not isinstance(stats["cohorts"], list):
        raise PipelineError("집계·통계 JSON 배열 구조 오류")

    agg_hash = aggregate.get("input_sha256")
    stats_hashes = stats.get("input_sha256")
    if not isinstance(stats_hashes, dict) or set(stats_hashes) != {"mart", "strict_mart", "db"}:
        raise PipelineError("통계 JSON 입력 해시 계약 오류")
    actual_hashes = {filename: sha256_file(path) for filename, path in paths.items()}
    if (agg_hash != actual_hashes["enrollment_mart.csv"]
        or stats_hashes != {
            "mart": actual_hashes["enrollment_mart.csv"],
            "strict_mart": actual_hashes["enrollment_mart_strict.csv"],
            "db": actual_hashes["oulad.duckdb"],
        }):
        raise PipelineError("집계/통계 JSON 입력 해시가 현재 실행 산출물과 다릅니다")

    a, s = aggregate.get("overall"), stats.get("overall")
    if not isinstance(a, dict) or not isinstance(s, dict):
        raise PipelineError("집계/통계 overall 구조 오류")
    nums = {}
    for key in ("eligible", "w1_active", "w2_returned"):
        x, y = require_count(a, key, "aggregate.overall"), require_count(s, key, "statistics.overall")
        if x != y:
            raise PipelineError(f"최종 집계·통계 불일치: {key} 집계={x} / 통계={y}")
        nums[key] = x
    if not 0 <= nums["w2_returned"] <= nums["w1_active"] <= nums["eligible"]:
        raise PipelineError("전체 분자·분모의 관계가 유효하지 않습니다")
    percent = expected_percent(nums["w2_returned"], nums["w1_active"])
    ratio = (nums["w2_returned"] / nums["w1_active"]) if nums["w1_active"] else None
    validate_rate(a.get("return_rate_pct"), percent, "aggregate.overall.return_rate_pct")
    validate_rate(s.get("return_rate"), ratio, "statistics.overall.return_rate", tolerance=1e-12)

    # The three overall rows are separate from cohort rows. Never sum both scopes.
    rows = aggregate["rows"]
    if len(rows) < 3:
        raise PipelineError("집계 JSON에 전체 3개 활동 그룹이 없습니다")
    for i, group in enumerate(("1일", "2일", "3일 이상")):
        entry = rows[i]
        if (not isinstance(entry, dict) or entry.get("scope") != "overall"
            or entry.get("code_module") is not None
            or entry.get("code_presentation") is not None
            or entry.get("activity_group") != group):
            raise PipelineError(f"집계 JSON의 전체 활동 그룹 {group} 행 오류")
        denominator = require_count(entry, "denominator", f"rows[{i}]")
        numerator = require_count(entry, "numerator", f"rows[{i}]")
        if numerator > denominator:
            raise PipelineError(f"rows[{i}] 분자가 분모보다 큽니다")
        validate_rate(entry.get("return_rate_pct"), expected_percent(numerator, denominator), f"rows[{i}].return_rate_pct")
    if (sum(r["denominator"] for r in rows[:3]) != nums["w1_active"]
        or sum(r["numerator"] for r in rows[:3]) != nums["w2_returned"]):
        raise PipelineError("전체 활동 그룹 합계와 재방문 분자·분모가 불일치합니다")

    if sha256_file(manifest) != original_manifest_hash:
        raise PipelineError("실행 중 manifest 파일 내용이 변경됐습니다")
    for name, original_hash in code_hashes.items():
        if sha256_file(code_dir / name) != original_hash:
            raise PipelineError(f"실행 중 제출 코드/SQL이 변경됐습니다: {name}")
    quality_report = load_json(run_dir, "quality.json")
    if quality_report.get("gate") != gate:
        raise PipelineError("최종 품질 gate가 중간 검증 결과와 다릅니다")

    artifacts = {filename: {"path": filename, "sha256": digest} for filename, digest in actual_hashes.items()}
    return nums, artifacts


def run(manifest_arg: Path, raw_arg: Path, output_arg: Path) -> int:
    code_dir = Path(__file__).resolve().parent
    manifest = manifest_arg.expanduser().resolve()
    raw = raw_arg.expanduser().resolve()
    output_root = output_arg.expanduser().resolve()
    validate_output_root(output_root, raw, manifest, code_dir)
    run_id, run_dir = create_run_dir(output_root, raw)
    record_path = run_dir / "run_record.json"
    started_mono = time.monotonic()
    record = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "running",
        "started_at_utc": utc_now(),
        "ended_at_utc": None,
        "elapsed_seconds": None,
        "inputs": {"manifest": str(manifest), "raw_dir": str(raw), "manifest_sha256": None,
                   "source_csv_from_manifest": None, "code_sha256": {}},
        "steps": [
            {"name": name, "status": "pending", "exit_code": None, "elapsed_seconds": None,
             "stdout_log": None, "stderr_log": None}
            for name in STAGES
        ],
        "failed_step": None,
        "reason": None,
        "quality_gate": None,
        "overall": None,
        "artifacts": None,
    }

    current_step = "preflight"
    final_code = 1
    try:
        atomic_record(record_path, record)
        manifest_hash, code_hashes = input_inventory(manifest, code_dir)
        record["inputs"]["manifest_sha256"] = manifest_hash
        record["inputs"]["code_sha256"] = code_hashes
        if not raw.is_dir():
            raise PipelineError(f"원본 CSV 폴더가 없습니다: {raw}")
        atomic_record(record_path, record)

        for number, (name, argv, output_name) in enumerate(commands(code_dir, manifest, raw, run_dir), 1):
            current_step = name
            entry = record["steps"][number - 1]
            out_rel = f"logs/{number:02d}_{name}.stdout.log"
            err_rel = f"logs/{number:02d}_{name}.stderr.log"
            entry.update({"status": "running", "stdout_log": out_rel, "stderr_log": err_rel})
            atomic_record(record_path, record)
            step_start = time.monotonic()
            try:
                with (run_dir / out_rel).open("wb") as stdout, (run_dir / err_rel).open("wb") as stderr:
                    completed = subprocess.run(
                        [sys.executable, str(code_dir / argv[0]), *argv[1:]],
                        stdout=stdout, stderr=stderr, cwd=code_dir, check=False,
                    )
                entry["exit_code"] = completed.returncode
            except KeyboardInterrupt:
                entry["elapsed_seconds"] = round(time.monotonic() - step_start, 6)
                entry["status"] = "error"
                raise
            except OSError as exc:
                entry["elapsed_seconds"] = round(time.monotonic() - step_start, 6)
                entry["status"] = "error"
                raise PipelineError(f"자식 프로세스 실행/로그 기록 실패: {exc}") from exc
            entry["elapsed_seconds"] = round(time.monotonic() - step_start, 6)
            child_exit = completed.returncode
            if name == "quality" and child_exit in (0, 2):
                gate, _checks = validate_quality(run_dir, child_exit)
                record["quality_gate"] = gate
            if child_exit != 0:
                if child_exit == 2 and name in BLOCK_STAGES:
                    # A quality BLOCK is only valid if the just-written quality JSON
                    # was checked; mart BLOCK is the existing mart runner's contract.
                    entry["status"] = "blocked"
                    atomic_record(record_path, record)
                    raise PipelineError(f"{name}: 품질 BLOCK (자식 종료 코드 2)")
                entry["status"] = "error"
                atomic_record(record_path, record)
                raise PipelineError(f"{name}: 자식 프로세스 종료 코드 {child_exit}; stderr 로그 확인")
            if output_name is not None:
                safe_artifact(run_dir, output_name)
            entry["status"] = "success"
            atomic_record(record_path, record)

        current_step = "final_reconciliation"
        overall, artifacts = validate_final(
            run_dir, manifest, manifest_hash, code_dir, code_hashes, record["quality_gate"]
        )
        record["overall"] = overall
        record["artifacts"] = artifacts
        # Record hashes of the seven CSV files stated in the successfully
        # validated manifest; never expose raw learner-level data in the record.
        with manifest.open("r", encoding="utf-8") as handle:
            source_files = json.load(handle)["files"]
        record["inputs"]["source_csv_from_manifest"] = {
            name: {"sha256": value["sha256"], "bytes": value["bytes"]}
            for name, value in sorted(source_files.items())
        }
        record["status"] = "success"
        record["ended_at_utc"] = utc_now()
        record["elapsed_seconds"] = round(time.monotonic() - started_mono, 6)
        atomic_record(record_path, record)
        print(f"SUCCESS  run_id={run_id}")
        print(f"quality_gate={record['quality_gate']}  eligible={overall['eligible']}  "
              f"w1_active={overall['w1_active']}  w2_returned={overall['w2_returned']}")
        print(f"run_record={record_path}")
        final_code = 0
    except KeyboardInterrupt:
        record["status"] = "aborted"
        record["failed_step"] = current_step
        record["reason"] = "KeyboardInterrupt: 실행이 중단됐습니다"
        final_code = 130
    except (PipelineError, OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        entry = next((s for s in record["steps"] if s["name"] == current_step), None)
        if entry is not None and entry["status"] == "running":
            entry["status"] = "error"
        blocked = entry is not None and entry["status"] == "blocked"
        record["status"] = "blocked" if blocked else "error"
        record["failed_step"] = current_step
        record["reason"] = str(exc)
        final_code = 2 if blocked else 1
    finally:
        if final_code != 0:
            record["ended_at_utc"] = utc_now()
            record["elapsed_seconds"] = round(time.monotonic() - started_mono, 6)
            try:
                atomic_record(record_path, record)
            except OSError as exc:
                print(f"ERROR: run_record.json을 기록하지 못했습니다: {exc}", file=sys.stderr)
                final_code = 1
            print(f"{record['status'].upper()}: {record.get('failed_step')}: {record.get('reason')}", file=sys.stderr)
            print(f"run_record={record_path}", file=sys.stderr)
    return final_code


def main() -> int:
    parser = PipelineParser(description="OULAD 제출 코드 7단계 실행 및 결과 보존")
    parser.add_argument("--manifest", required=True, type=Path, help="data/manifest.json 경로")
    parser.add_argument("--raw-dir", required=True, type=Path, help="원본 CSV 7개 폴더")
    parser.add_argument("--output-dir", required=True, type=Path, help="새 실행별 결과 루트")
    args = parser.parse_args()
    try:
        return run(args.manifest, args.raw_dir, args.output_dir)
    except (PipelineError, OSError, ValueError, UnicodeError) as exc:
        print(f"ERROR: 파이프라인 시작 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

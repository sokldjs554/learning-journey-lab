#!/usr/bin/env python3
"""Track quality-rule issues across validated executions of run_pipeline.py.

Usage:
    python update_issues.py --run-dir PATH/TO/RUN --history ./issue_history.json

A valid 20-rule quality check can be processed even if the pipeline was BLOCKed
by that check or failed later. Invalid/unfinished quality checks never resolve
old issues. Duplicate run_ids do not write to the history again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from run_quality_full import (
    EXPECTED_RULES,
    QualityRunError,
    decide_gate,
    validate_results,
)


class IssueHistoryError(Exception):
    """Bad input, inconsistent records, or an unsafe output operation."""


class IssueArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"ERROR: 인자 오류: {message}\n")


def read_json(path: Path) -> dict:
    """Read an ordinary JSON object, rejecting duplicate keys and NaN."""
    if path.is_symlink() or not path.is_file():
        raise IssueHistoryError(f"파일이 없거나 일반 파일이 아닙니다: {path}")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"JSON 중복 키: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"JSON 비표준 수치: {value}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            result = json.load(
                handle, object_pairs_hook=reject_duplicates,
                parse_constant=reject_constant,
            )
    except (OSError, UnicodeError, ValueError) as exc:
        raise IssueHistoryError(f"JSON 읽기 실패 ({path}): {exc}") from exc
    if not isinstance(result, dict):
        raise IssueHistoryError(f"JSON 최상위는 객체여야 합니다: {path}")
    return result


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def nonempty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_run_record(record: dict) -> tuple[str, str, dict]:
    """Verify that a finished pipeline run completed a valid quality stage."""
    if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise IssueHistoryError("run_record.json schema_version이 1이 아닙니다")
    run_id = record.get("run_id")
    if not nonempty_string(run_id):
        raise IssueHistoryError("run_record.json의 run_id가 유효하지 않습니다")
    if record.get("status") not in {"success", "blocked", "error", "aborted"}:
        raise IssueHistoryError("완료되지 않은 실행의 품질 결과는 처리할 수 없습니다")
    if not nonempty_string(record.get("ended_at_utc")):
        raise IssueHistoryError("실행 종료 시각이 없는 run_record.json입니다")

    inputs = record.get("inputs")
    manifest_hash = inputs.get("manifest_sha256") if isinstance(inputs, dict) else None
    if not isinstance(manifest_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", manifest_hash):
        raise IssueHistoryError("manifest_sha256이 없거나 올바른 SHA-256 형식이 아닙니다")

    steps = record.get("steps")
    if not isinstance(steps, list):
        raise IssueHistoryError("run_record.json의 steps가 배열이 아닙니다")
    quality_steps = [s for s in steps if isinstance(s, dict) and s.get("name") == "quality"]
    if len(quality_steps) != 1:
        raise IssueHistoryError("품질 검사 단계가 정확히 한 번 기록되지 않았습니다")
    step = quality_steps[0]
    stage_state, exit_code = step.get("status"), step.get("exit_code")
    if not ((stage_state == "success" and type(exit_code) is int and exit_code == 0)
            or (stage_state == "blocked" and type(exit_code) is int and exit_code == 2)):
        raise IssueHistoryError(
            f"품질 검사 실패/미완료: 상태={stage_state!r}, 종료 코드={exit_code!r}"
        )
    if stage_state == "blocked" and record.get("status") != "blocked":
        raise IssueHistoryError("품질 BLOCK과 실행 상태가 일치하지 않습니다")
    return run_id, manifest_hash, step


def validate_quality_report(report: dict, record: dict, step: dict) -> list[dict]:
    if report.get("scope") != "full_quality_20" or not isinstance(report.get("checks"), list):
        raise IssueHistoryError("quality.json은 full_quality_20의 20규칙 결과여야 합니다")
    rows = []
    for check in report["checks"]:
        if not isinstance(check, dict) or set(check) != {"rule_id", "severity", "issue_count"}:
            raise IssueHistoryError("quality.json의 검사 항목은 세 필드가 필요합니다")
        rows.append((check["rule_id"], check["severity"], check["issue_count"]))
    try:
        checks = validate_results(
            [("rule_id",), ("severity",), ("issue_count",)], rows
        )
    except (QualityRunError, TypeError, ValueError) as exc:
        raise IssueHistoryError(f"20개 규칙 결과 계약 오류: {exc}") from exc
    gate = decide_gate(checks)
    if report.get("gate") != gate or record.get("quality_gate") != gate:
        raise IssueHistoryError(
            f"판정 불일치: 계산={gate}, quality.json={report.get('gate')!r}, "
            f"run_record.json={record.get('quality_gate')!r}"
        )
    required_step = ("blocked", 2) if gate == "BLOCK" else ("success", 0)
    if (step["status"], step["exit_code"]) != required_step:
        raise IssueHistoryError(f"품질 검사 종료 코드/상태와 gate({gate})가 맞지 않습니다")
    return checks


def new_history(manifest_hash: str) -> dict:
    return {
        "schema_version": 1,
        "manifest_sha256": manifest_hash,
        "processed_runs": [],
        "issues": [],
    }


def validate_existing_history(history: dict, manifest_hash: str) -> dict:
    if type(history.get("schema_version")) is not int or history["schema_version"] != 1:
        raise IssueHistoryError("기존 이력 schema_version이 올바르지 않습니다")
    if history.get("manifest_sha256") != manifest_hash:
        raise IssueHistoryError(
            "다른 manifest_sha256의 실행은 같은 issue_history.json에 합칠 수 없습니다"
        )
    processed = history.get("processed_runs")
    if not isinstance(processed, list):
        raise IssueHistoryError("기존 processed_runs 형식 오류")
    by_run = {}
    for item in processed:
        if (not isinstance(item, dict) or set(item) != {"run_id", "quality_sha256", "gate"}
            or not nonempty_string(item["run_id"]) or item["run_id"] in by_run
            or not isinstance(item["quality_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", item["quality_sha256"])
            or item["gate"] not in {"PASS", "REVIEW", "BLOCK"}):
            raise IssueHistoryError("기존 processed_runs의 중복 또는 잘못된 항목")
        by_run[item["run_id"]] = item

    issues = history.get("issues")
    if not isinstance(issues, list) or len(issues) != len(EXPECTED_RULES):
        raise IssueHistoryError("기존 이력의 20개 규칙 목록이 잘못됐습니다")
    expected = dict(EXPECTED_RULES)
    seen = set()
    for issue in issues:
        if not isinstance(issue, dict):
            raise IssueHistoryError("기존 이력에 잘못된 규칙 항목이 있습니다")
        rid = issue.get("rule_id")
        count = issue.get("issue_count")
        status = issue.get("status")
        first = issue.get("first_seen_run_id")
        last = issue.get("last_checked_run_id")
        changes = issue.get("history")
        if rid not in expected or rid in seen or issue.get("severity") != expected[rid]:
            raise IssueHistoryError(f"기존 규칙 ID/심각도 오류: {rid!r}")
        seen.add(rid)
        if type(count) is not int or count < 0:
            raise IssueHistoryError(f"{rid}: 유효하지 않은 issue_count")
        if status not in {"open", "resolved", "clear"} or (count > 0) != (status == "open"):
            raise IssueHistoryError(f"{rid}: 현재 상태와 건수가 일치하지 않습니다")
        if (first is not None and first not in by_run) or last not in by_run:
            raise IssueHistoryError(f"{rid}: 최초/최종 실행 ID가 처리 기록에 없습니다")
        if (status == "clear" and first is not None) or (status != "clear" and first is None):
            raise IssueHistoryError(f"{rid}: 최초 발견 실행 ID와 상태가 모순됩니다")
        if not isinstance(changes, list) or not changes:
            raise IssueHistoryError(f"{rid}: 변경 이력이 비어 있습니다")
        for event in changes:
            if not isinstance(event, dict) or event.get("run_id") not in by_run:
                raise IssueHistoryError(f"{rid}: 변경 이력의 실행 ID가 잘못됐습니다")
    if seen != set(expected):
        raise IssueHistoryError("기존 이력의 규칙 목록이 완전하지 않습니다")
    return by_run


def apply_run(history: dict, run_id: str, quality_hash: str,
              gate: str, checks: list[dict]) -> int:
    """Apply one valid distinct run; return number of changed rule snapshots."""
    by_id = {item["rule_id"]: item for item in history["issues"]}
    changes = 0
    for check in checks:
        rid = check["rule_id"]
        count = check["issue_count"]
        issue = by_id.get(rid)
        if issue is None:
            issue = {
                "rule_id": rid,
                "severity": check["severity"],
                "issue_count": None,
                "status": None,
                "first_seen_run_id": None,
                "last_checked_run_id": None,
                "history": [],
            }
            by_id[rid] = issue
        old_count, old_status = issue["issue_count"], issue["status"]
        if count > 0 and issue["first_seen_run_id"] is None:
            issue["first_seen_run_id"] = run_id
        next_status = ("open" if count > 0 else
                       "resolved" if issue["first_seen_run_id"] is not None else "clear")
        issue["issue_count"] = count
        issue["status"] = next_status
        issue["last_checked_run_id"] = run_id
        if old_count != count or old_status != next_status:
            issue["history"].append({
                "run_id": run_id,
                "previous_status": old_status,
                "status": next_status,
                "previous_count": old_count,
                "issue_count": count,
            })
            changes += 1
    history["issues"] = [by_id[rid] for rid, _severity in EXPECTED_RULES]
    history["processed_runs"].append({
        "run_id": run_id,
        "quality_sha256": quality_hash,
        "gate": gate,
    })
    return changes


def save_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".issue_history-", suffix=".tmp",
            dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(run_dir: Path, history_path: Path) -> int:
    run_dir = run_dir.expanduser().resolve()
    history_path = history_path.expanduser().absolute()
    if not run_dir.is_dir():
        raise IssueHistoryError(f"실행 폴더가 없습니다: {run_dir}")
    record_path = run_dir / "run_record.json"
    quality_path = run_dir / "quality.json"
    if history_path.is_symlink() or history_path.resolve() in {
        record_path.resolve(), quality_path.resolve()
    }:
        raise IssueHistoryError("--history는 입력 파일과 달라야 하며 심볼릭 링크일 수 없습니다")

    record = read_json(record_path)
    run_id, manifest_hash, quality_step = validate_run_record(record)
    quality = read_json(quality_path)
    checks = validate_quality_report(quality, record, quality_step)
    quality_hash = digest_file(quality_path)

    history = (read_json(history_path) if history_path.exists()
               else new_history(manifest_hash))
    prior = validate_existing_history(history, manifest_hash) if history["processed_runs"] else {}
    if history_path.exists() and not history["processed_runs"]:
        # Refuse a malformed/partially initialized file, rather than resetting it.
        raise IssueHistoryError("기존 이력에 처리된 실행이 없어 안전하게 갱신할 수 없습니다")
    if run_id in prior:
        if prior[run_id]["quality_sha256"] != quality_hash:
            raise IssueHistoryError("동일 run_id에 다른 quality.json 내용이 발견됐습니다")
        print(f"SKIP: 이미 처리한 run_id={run_id}; issue_history.json 변경 없음")
        return 0

    changed = apply_run(history, run_id, quality_hash, quality["gate"], checks)
    save_atomic(history_path, history)
    opened = sum(item["status"] == "open" for item in history["issues"])
    resolved = sum(item["status"] == "resolved" for item in history["issues"])
    print(f"UPDATED: run_id={run_id}, quality_gate={quality['gate']}, "
          f"changed_rules={changed}, open={opened}, resolved={resolved}")
    print(f"history={history_path}")
    return 0


def main() -> int:
    parser = IssueArgumentParser(description="실행별 품질 이슈 상태 및 변경 이력 누적")
    parser.add_argument("--run-dir", required=True, type=Path, help="run_record.json과 quality.json이 있는 실행 폴더")
    parser.add_argument("--history", required=True, type=Path, help="누적 issue_history.json 경로")
    args = parser.parse_args()
    try:
        return run(args.run_dir, args.history)
    except (IssueHistoryError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: 이슈 이력 갱신 실패: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

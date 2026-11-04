#!/usr/bin/env python3
"""Check the seven OULAD raw CSV files against data/manifest.json."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_FILES = {
    "assessments.csv",
    "courses.csv",
    "studentAssessment.csv",
    "studentInfo.csv",
    "studentRegistration.csv",
    "studentVle.csv",
    "vle.csv",
}
CHUNK_SIZE = 1024 * 1024


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise ValueError("manifest에 'files' 객체가 없습니다.")

    files = manifest["files"]
    if set(files) != EXPECTED_FILES:
        missing = sorted(EXPECTED_FILES - set(files))
        extra = sorted(set(files) - EXPECTED_FILES)
        raise ValueError(f"manifest 파일 목록 오류: 누락={missing}, 추가={extra}")

    for name, info in files.items():
        if not isinstance(info, dict):
            raise ValueError(f"{name}: 파일 정보가 객체가 아닙니다.")
        sha256 = info.get("sha256")
        size = info.get("bytes")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
            raise ValueError(f"{name}: 유효한 SHA-256 값이 없습니다.")
        if type(size) is not int or size < 0:
            raise ValueError(f"{name}: 유효한 bytes 값이 없습니다.")

    return files


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as file:
        while chunk := file.read(CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def check_files(files: dict, csv_dir: Path) -> int:
    if not csv_dir.is_dir():
        print(f"FAIL: 원본 CSV 폴더가 없거나 디렉터리가 아닙니다: {csv_dir}", file=sys.stderr)
        return 1

    failed = 0
    for name in sorted(files):
        path = csv_dir / name
        if not path.is_file():
            reason = "파일이 없습니다" if not path.exists() else "일반 파일이 아닙니다"
            print(f"FAIL {name}: {reason} ({path})")
            failed += 1
            continue

        try:
            actual_sha, actual_size = hash_file(path)
        except OSError as error:
            print(f"FAIL {name}: 파일 읽기 실패 ({error})")
            failed += 1
            continue

        expected_sha = files[name]["sha256"].lower()
        expected_size = files[name]["bytes"]
        reasons = []
        if actual_size != expected_size:
            reasons.append(f"크기 불일치 (기대 {expected_size} / 실제 {actual_size} bytes)")
        if actual_sha != expected_sha:
            reasons.append(f"SHA-256 불일치 (기대 {expected_sha} / 실제 {actual_sha})")

        if reasons:
            print(f"FAIL {name}: {'; '.join(reasons)}")
            failed += 1
        else:
            print(f"OK   {name}: {actual_size} bytes / SHA-256 일치")

    print(f"검사 완료: 성공 {len(files) - failed}건 / 실패 {failed}건")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="OULAD 원본 CSV 7개 무결성 검증")
    parser.add_argument("--manifest", type=Path, required=True, help="data/manifest.json 경로")
    parser.add_argument("--csv-dir", type=Path, required=True, help="원본 CSV 7개가 있는 폴더")
    args = parser.parse_args()

    try:
        files = load_manifest(args.manifest)
    except (OSError, ValueError, UnicodeError) as error:
        print(f"FAIL: manifest 읽기/형식 오류: {error}", file=sys.stderr)
        return 2

    return check_files(files, args.csv_dir)


if __name__ == "__main__":
    sys.exit(main())

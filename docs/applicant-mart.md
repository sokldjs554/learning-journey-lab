# 지원자 수강 건별 분석표 제출·검토

2026-11-05 KST, `build_mart.sql`, `build_mart.py`를 수신했다. [사전에 정한 분석표 계약](applicant-mart-spec.md)에 대한 **제출·기능 검토 완료**다. 두 파일의 업로드 바이트를 수정 없이 보존했다. 실제 제출 코드와 Codex가 작성·실행한 검사를 구분한다.

- [제출 SQL](../evidence/applicant/build_mart.sql)
- [제출 Python](../evidence/applicant/build_mart.py)
- [Codex의 손계산·실패 사례 검사](../tests/test_applicant_mart.py)
- [실제 실행 결과와 파일 해시](../reports/applicant-mart.json)

## 실제 OULAD 결과

앞서 제출한 원본 검증·적재 코드로 실제 7 CSV를 검증하고 임시 DuckDB에 적재했다. 이번 Python으로 현재 DB의 전체 품질 SQL을 재실행한 뒤 CSV를 생성했다. 두 정책의 gate는 REVIEW이며 정상 종료 코드 0이다.

| 정책 | 적격 수강 건 | 첫 주 활동 | 첫 주 활동 중 다음 주 활동 |
|---|---:|---:|---:|
| 기본 | 29,671 | 23,522 | 20,303 |
| strict | 29,671 | 23,430 | 20,210 |

strict는 등록·탈퇴 기간 밖 활동을 제외하며 **분모인 적격 수강 건은 유지**한다. 탈퇴 당일 활동은 포함한다. 어느 정책이 실제 수집 진실인지 확정하는 비교는 아니다.

각 정책을 두 번 실행한 CSV 바이트가 같았다. 기존 `sql/marts.sql`을 별도 메모리 DB에서 실행한 결과와 **29,671행 × 12열**을 대조해 불일치 0행이었다. 별도로 원본 CSV를 pandas에서 청크 단위로 읽고 적격성·콘텐츠 키·고유 활동일을 계산해 `w1_days`, `w2_active`, `later_active`를 대조했으며, 두 정책 모두 불일치 0행이었다. pandas 계산은 생산 SQL이나 해당 계산 함수를 호출하지 않았다.

실제 원본·manifest·제출 코드·입력 DB의 내용 해시와 수정 시각을 보존했다. 학습자 키가 포함된 결과 CSV는 임시 폴더에서 검토 후 삭제했고 공개 저장소에 올리지 않았다.

## 손계산과 실패 검증

Codex가 작성한 43개 검사가 통과했다.

- D−1/0/6/7/13/14/27/28의 주차 경계, 첫 주 활동 없음, 활동 자체가 없는 적격 수강 건, 빈 입력.
- 등록일 NULL·개강 후 등록·개강 전 탈퇴·28일 미만 개설기의 제외, NULL의 0 대체 방지.
- 등록·콘텐츠의 전체 복합키 사용, 양수 클릭만 포함, 첫날의 콘텐츠 종류와 후속 날짜 구분.
- 같은 사이트·날짜의 4/4/2와 다른 사이트의 4: raw 14 / exact 10 / max 8. 여러 행을 활동일 여러 개로 세지 않음.
- strict의 탈퇴일 포함과 이후 활동 제외, 동일한 적격 수강 건 유지.
- PASS/REVIEW에서 CSV 생성, 입력 DB가 이후 변경되어 차원 중복이 생기면 새 품질 검사에서 BLOCK. 이때 기존 CSV 보존 또는 신규 CSV 미생성.
- 누락·빈 SQL·SQL 오류·잘못된 품질 계약·결과 열·중복 결과 키·출력 저장 실패에서 종료 1과 이전 CSV 보존. BLOCK은 종료 2로 구분.
- DB/SQL 출력 경로 충돌과 심볼릭 링크 충돌 차단, 읽기 전용 DB, 임시 출력 파일 정리.

실제 자료 대조용 Codex 임시 스크립트에서 DuckDB `ATTACH`의 파일 경로에 사용할 수 없는 `?` 바인딩을 발견해 SQL 리터럴 이스케이프로 수정한 뒤 대조했다. 이는 검토 도구 수정이며 제출 코드 결함이나 지원자의 수정 경험으로 기록하지 않는다.

## 재현

기존 원본 폴더와 별도로 작업한다. Python 환경에 저장소 requirements가 설치되어 있어야 한다. 아래 명령은 저장소 최상위에서 실행한다. `work/applicant`는 생성되는 별도 결과 폴더다.

```bash
mkdir -p work/applicant
python evidence/applicant/load_sources.py --manifest data/manifest.json --csv-dir /실제/원본/CSV/폴더 --db work/applicant/source.duckdb
python evidence/applicant/build_mart.py --db work/applicant/source.duckdb --quality-sql evidence/applicant/quality_full.sql --mart-sql evidence/applicant/build_mart.sql --output work/applicant/mart.csv
python evidence/applicant/build_mart.py --db work/applicant/source.duckdb --quality-sql evidence/applicant/quality_full.sql --mart-sql evidence/applicant/build_mart.sql --output work/applicant/mart-strict.csv --strict
python -m pytest -q tests/test_applicant_mart.py
```

`/실제/원본/CSV/폴더`는 본인 장치의 실제 경로로 바꾼다. 생성된 CSV를 공개 커밋하지 않는다. 위 명령은 재현 안내이며 지원자가 이번 제출과 함께 실행 출력을 보냈다는 뜻은 아니다. 완료한 기존 실측이나 SQL 실습을 다시 요구하지 않는다.

## 역할과 범위

지원자는 분석표 SQL과 품질 검사→분석표 생성→CSV 저장을 연결하는 Python을 제출했다. Codex는 요구사항 안내, 원본 보존, 검사 작성·실행, 실제 자료 대조와 기록을 담당했다. 이번 첨부에는 별도 참고·도움 설명이나 지원자 로컬 실행 출력이 없으므로 이를 추정하지 않는다.

원본 검증·적재·전체 품질·분석표 모듈의 제출·기능 검토가 완료됐다. 이전 활동 기준 비교 SQL과 v2 사람 실측의 완료 상태도 유지한다. 전체 직접 구현의 후속 통계·운영·UI·배포 범위는 [기존 합의](independent-implementation-brief.md)에 따라 진행 중이다. 이번 검토가 전 영역의 무도움 숙련도나 CLASS101 실제 서비스 효과를 인증하지는 않는다.

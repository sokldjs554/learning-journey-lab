# 운영 연결 첫 제출: run_pipeline.py

현재 상태: **제출·기능 검토 완료**. [원본 보존·37개 검사·실제 자료2회 실행 근거](applicant-pipeline.md). 아래는 제출 전에 고정한 작성 계약이다.

2026-11-06 KST. [고정한 전체 구현 계획](applicant-completion-plan.md)의 운영 연결 범위다. 지금은 **이미 통과한 개별 코드를 한 명령으로 실행하고 실패·결과·실행 기록을 관리하는 파일 하나**를 작성한다. 기존 SQL이나 통계 공식을 다시 작성하지 않는다.

이번 파일은 운영 연결의 실행 부분이다. 기존 계획에 있는 이슈 이력·독립 계산 대조·단계별/일괄 비교 도구 연결은 같은 운영 범위에 남으며, 이 파일만으로 그 전부를 완료했다고 표시하지 않는다. 새로운 사람 실측은 없다.

## 어디서 무엇을 작성하나

직접 작성한 `run_statistics.py` 등이 있는 폴더에 새 파일 `run_pipeline.py`를 만든다. 기존 제출 모듈과 SQL을 같은 폴더에서 찾도록 연결한다. 다른 디렉터리에서 실행해도 작동하도록 스크립트 위치를 기준으로 찾는다. 기존 입력 파일과 측정 폴더를 덮어쓰지 않는다.

CLI 인자는 세 개다.

| 인자 | 의미 |
|---|---|
| `--manifest` | 실제 OULAD data/manifest.json 경로 |
| `--raw-dir` | 원본7CSV가 들어 있는 실제 폴더 |
| `--output-dir` | 새 실행별 결과를 저장할 별도 폴더 |

내부에서는 현재 가상환경의 `sys.executable`을 사용해 기존 Python 파일을 순서대로 실행한다. `subprocess.run` 등에 인자 리스트를 전달하고 shell 문자열 조합을 사용하지 않는다. 경로에 공백이 있어도 작동해야 한다. import로 기존 함수 전체를 재설계할 필요는 없다.

## 실행 순서와 실제 인자

아래 `manifest`, `raw`, `run_dir`, `code_dir`는 설명용 이름이며 실제 코드에서는 Path 등으로 정한다. `run_dir`는 이번에만 새로 만든 실행 폴더다.

| 순서·step 이름 | 기존 파일 | 전달할 인자 |
|---|---|---|
| 1 `validate_sources` | validate_sources.py | `--manifest manifest --csv-dir raw` |
| 2 `load_sources` | load_sources.py | `--manifest manifest --csv-dir raw --db run_dir/oulad.duckdb` |
| 3 `quality` | run_quality_full.py | `--db run_dir/oulad.duckdb --sql code_dir/quality_full.sql --output run_dir/quality.json` |
| 4 `mart_base` | build_mart.py | `--db run_dir/oulad.duckdb --quality-sql code_dir/quality_full.sql --mart-sql code_dir/build_mart.sql --output run_dir/enrollment_mart.csv` |
| 5 `mart_strict` | build_mart.py | 4번과 같고 출력은 `run_dir/enrollment_mart_strict.csv`, `--strict` 추가 |
| 6 `aggregate` | run_aggregate.py | `--mart run_dir/enrollment_mart.csv --sql code_dir/aggregate.sql --output run_dir/activity-groups.json` |
| 7 `statistics` | run_statistics.py | `--mart run_dir/enrollment_mart.csv --strict-mart run_dir/enrollment_mart_strict.csv --db run_dir/oulad.duckdb --output run_dir/statistics.json` |

각 Python 앞에는 sys.executable을 사용한다. load_sources와 build_mart 내부의 기존 검증은 그대로 두어도 된다. 중복 검증을 없애기 위해 이미 통과한 코드를 변경하는 것은 이번 과제가 아니다.

위7개는 **기존 명령의 호출 순서**이며 새 과제7개가 아니다. 필요한 의존 모듈인 `run_aggregate.py`, `build_mart.py`, `run_quality_full.py`, `validate_sources.py`, `learning_stats.py` 등도 같은 폴더에 있어야 한다. 누락·입력 경로 오류는 설명하고 종료1로 처리한다. 자동 설치나 원본 다운로드·manifest 변경을 수행하지 않는다.

## 실행별 폴더와 결과 보존

`output-dir/runs/<run_id>/` 형태처럼 실행마다 새 고유 폴더를 만든다. 이름 충돌이 나면 기존 폴더를 재사용하지 않는다. 그 폴더 안에서만 DB·CSV·JSON·로그를 생성한다. 출력 루트는 raw-dir 자신이나 그 하위일 수 없고, 제출 코드 파일·manifest와 충돌해서도 안 된다. 기존 결과 폴더를 삭제하거나 지난 성공 결과를 실패 결과로 덮어쓰지 않는다.

`run_record.json`에는 최소 다음을 기록한다. 세부 필드 이름을 바꾸면 제출 설명에 대응 관계를 적는다.

- `schema_version:1`, 고유 `run_id`, `status` (`running`, `success`, `blocked`, `error`, `aborted` 중 하나).
- 시작·종료 시각(UTC 명시), monotonic clock으로 잰 전체 경과초. 계산 대기 포함이며 사람의 노동 시간/절감률로 부르지 않는다.
- manifest 파일의 SHA-256, 사용한 제출 Python·SQL의 파일명/해시. 입력 CSV 해시는 기존 manifest의 검증 결과와 연결한다.
- `steps`: 위 순서·상태(`pending`,`running`,`success`,`blocked`,`error`), 자식 프로세스 실제 종료 코드, 경과초, 표준 출력/오류 로그의 경로. 실행하지 않은 단계는 pending과 null 값으로 남기며 성공으로 채우지 않는다.
- 실패·차단 위치와 짧은 이유. 없는 시간·종료 코드를 지어내지 않는다.
- 성공한 경우 품질 gate와 전체 eligible/w1_active/w2_returned, 산출물 이름/해시. 산출물은 실행 폴더 안의 상대 경로로 기록할 수 있다.

하위 명령 출력은 단계별 `.stdout.log`, `.stderr.log` 등으로 보존한다. 로그에 로컬 경로나 개별 학습자 키가 포함될 수 있으므로 전체 로그·DB·CSV를 공개 커밋하지 않는다. `run_record.json`은 임시 파일에서 교체하는 방식으로 저장하고 단계 시작/종료 및 최종 상태에서 갱신한다. 디스크가 쓰기 불가하면 로그도 보존하지 못할 수 있으므로 표준 오류로 알리고 비정상 종료한다. 기록을 저장하지 못했는데 성공이라고 출력하지 않는다.

## 중단과 종료 코드

- 모든 단계와 최종 대조가 성공하면 종료0, status success.
- 품질 검사나 분석표 명령이 **그 명령에 정의된 BLOCK 종료2**를 반환하면 즉시 중단하고 종료2, status blocked. 후속 분석을 계속 실행하지 않는다.
- 그 외 입력·실행·결과·저장 오류는 즉시 중단하고 종료1, status error. 원래 자식 종료 코드는 steps에 그대로 보존한다.
- **모든 자식 종료2를 BLOCK으로 취급하면 안 된다.** validate_sources의 manifest 형식 오류도2인데, 이는 파이프라인 오류1이다. `step`과 해당 모듈의 계약을 함께 사용한다.
- KeyboardInterrupt는 성공으로 처리하지 않는다. 가능한 범위에서 자식 종료를 정리하고 aborted를 기록하며 종료130을 사용할 수 있다. 강제 프로세스 종료나 전원 장애에서 완전한 기록을 보장한다고 주장하지 않는다. 강제 종료로 남은 running 기록도 다음 실행이 덮어쓰지 않는다.

quality 단계에서는 출력 JSON이 전체20규칙 계약인지 기존 검증 함수를 재사용해 확인하고, 저장된 gate와 건수·자식 종료 코드의 관계가 맞는지 확인한다. 정상 종료0인데 JSON이 없거나 잘못됐으면 오류1이다. 품질 BLOCK 결과 JSON은 그 실행 폴더에 보존한다. 이후 build_mart에서 재검사 BLOCK이 생기면 해당 단계의 blocked 상태를 기록하며 앞서 저장한 quality.json을 새 검사 결과로 몰래 바꾸지 않는다.

## 성공 전 최종 대조

명령 종료0만 보고 성공으로 결정하지 않는다. 필요한 DB·기본/strict CSV·quality/activity-groups/statistics JSON이 생성됐는지 확인한다. 결과 계약과 필요한 필드를 확인하고, `activity-groups.json`의 overall과 `statistics.json`의 overall에서 eligible/w1_active/w2_returned가 같아야 한다. 집계의 백분율과 통계의0~1 비율은 단위를 맞춰 표시값을 확인한다.

두 JSON이 기록한 입력 해시는 이번 실행 폴더의 해당 CSV/DB 해시와 같아야 한다. 통계 입력으로 기본/strict 파일을 바꿔 연결한 오류나 지난 실행 파일을 읽는 오류를 숨기지 않는다. 실제 OULAD 기본값은29,671/23,522/20,303이지만 이 숫자를 성공 조건에 하드코딩하지 않는다. 작은 생성 테스트도 같은 계약으로 실행할 수 있어야 한다.

## 재실행 일관성의 정확한 범위

같은 원본·코드로 실행별 새 폴더에서 반복하면 품질 건수·분자/분모·통계·민감도 등 **분석 값이 같아야 한다**. 실행 시각·run_id·시간·경로는 달라지는 정상 기록이다. 새로 만든 DuckDB 파일의 내부 바이트/해시는 내용이 같아도 달라질 수 있고, `statistics.json.input_sha256.db`도 그 차이를 반영할 수 있다.

따라서 서로 다른 새 실행의 statistics JSON 전체 해시가 반드시 같아야 한다고 요구하지 않는다. 분석 필드의 일치와 입력·출력 해시 기록을 구분한다. 같은 준비된 입력 파일로 기존 개별 모듈을 다시 실행할 때의 JSON 일치 검증은 이미 완료한 근거로 유지한다. 실행 기록 전체를 같게 만들려고 시간을 제거하거나 이전 실행을 복사하지 않는다.

## 제출 후 Codex 검토

정상·REVIEW 진행, 품질 BLOCK 후 중단, manifest 오류2의 파이프라인 오류1 분류, 중간 단계 실패·누락 출력·잘못된 JSON, 기존 결과 보존, 경로 공백·의존 파일 누락, 키보드 중단 기록을 확인한다. 작은 생성 자료/통제된 실패와 실제 OULAD 실행을 구분한다. 실제 자료로 연결한 결과의 값과 반복 실행을 대조한다. 테스트 실행 횟수를 채우기 위해 새 사람 실측을 요청하지 않는다.

## 작성 후 실행 예시

현재 직접 구현 폴더에서 **파일 작성 후** 실행한다.

```bash
python run_pipeline.py \
  --manifest /실제/manifest.json \
  --raw-dir /실제/원본CSV폴더 \
  --output-dir ./pipeline-output
```

위 두 입력 경로는 예시다. 본인 장치에 존재하는 경로로 바꾸고 필요하면 따옴표로 감싼다. 환경이나 경로가 이미 확인됐다고 가정하지 않는다. 통과한 개별 파일을 다시 제출할 필요 없이 `run_pipeline.py`와 참고/도움 범위를 보내면 된다. 실제 실행했다면 마지막 상태·품질 gate·세 건수 출력만 함께 보낼 수 있다.

## 운영 연결 묶음의 나머지 범위

현재 전체 계획에 있던 다음 내용은 그대로 유지한다: 규칙별 이슈 이력과 반복 시 중복 이력 방지, 별도 계산 대조, 단계별/일괄 비교 도구의 수정·중단·시간 기록 연결. 이번 파일은 그 기반이 되는 실행·결과·실패 관리다. 이 파일 검토 뒤 이미 있는 인터페이스를 재사용해 연결하며, 이번 파일 하나로 운영 묶음 전체를 완료했다고 기록하지 않는다. 기존 사람 실측을 재실행하지 않는다.

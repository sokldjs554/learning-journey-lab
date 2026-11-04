# 지원자 품질 실행·결과 저장 코드 검토

2026-11-05 KST. 지원자가 `run_quality.py`를 첨부했다. **세 규칙 실행·판정·결과 저장 모듈의 코드 제출·기능 검토를 완료했다. 제출본은 수정하지 않았다.**

[제출 원본](../evidence/applicant/run_quality.py) · [검증 결과](../reports/applicant-quality-runner.json) · [Codex 검토 테스트](../tests/test_applicant_run_quality.py) · [재사용한 SQL](applicant-quality-sql.md).

## 제출 코드에서 확인한 동작

- `--db`, `--sql`, `--output` 경로를 받고, 기존 DB를 읽기 전용으로 연다. 입력 파일 누락·빈 SQL·출력과 입력 경로 충돌을 거절한다.
- SQL 결과가 정확히 `rule_id`, `issue_count` 두 열인지, 세 규칙이 한 번씩 있는지, 건수가 0 이상의 int인지 검사한다. bool·NULL·음수·소수·문자 건수는 거절한다.
- 미등록 활동 양수는 BLOCK, 그 외 두 규칙 중 양수가 있으면 REVIEW, 모두 0이면 PASS다. BLOCK의 우선순위도 확인했다.
- `scope: first_three_rules`로 세 규칙만 검사했다는 범위를 보존한다. 임시 파일을 쓴 뒤 결과 파일을 교체하며 실패 시 임시 파일을 정리한다.
- PASS/REVIEW는 종료 0, 정상 검사에서 나온 BLOCK은 2, 인자·입력·실행·결과·저장 오류는 1로 구분한다. `argparse` 인자 오류도 BLOCK과 혼동하지 않도록 처리한다.

위 설계 설명은 Codex가 제출 코드와 실행에서 확인한 내용이다. 지원자의 별도 구두 설명으로 소급하지 않는다.

## 실제 공개 자료 연결 결과

앞선 지원자 제출 검증·적재 모듈로 실제 OULAD CSV를 임시 DB에 적재하고, 제출된 품질 SQL과 이번 실행 코드를 그대로 연결했다.

| 항목 | 결과 |
|---|---|
| scope | first_three_rules |
| gate / 종료 코드 | REVIEW / 0 |
| registration_missing_date | 45 |
| event_exact_repeat | 787,170 |
| event_unknown_student | 0 |

두 번 실행한 JSON 바이트가 일치했다. 실제 원본·manifest·SQL과 DB의 해시 및 수정 시각도 유지됐다. 검사 후 임시 DB와 출력은 정리했고 결과·출력 해시는 검증 JSON에 보존했다. 기존 공개 분석 결과를 덮어쓰지 않았다.

## 검토 사례

Codex가 임시 자료로 작성한 **25개 검사 통과**:

- 실제 제출 SQL을 쓰는 PASS, 등록일 결측 REVIEW, 반복 초과 REVIEW, 미등록 BLOCK, 여러 문제 동시 발생 시 BLOCK 우선.
- 잘못된 열·행 수, 중복/미등록/NULL rule_id, 음수·NULL·소수·문자·bool 건수, 없는 테이블·빈 SQL·쓰기 SQL 거절.
- DB/SQL 누락, 출력 경로가 DB/SQL 또는 DB를 가리키는 심볼릭 링크인 경우, 출력 교체 실패, 명령행 인자 누락.
- 각 정상 판정의 반복 실행 일치, 입력 파일 보존, 오류 시 기존 보고서 보존과 임시 파일 정리.

오류 때 예전 결과 파일을 보존하므로 이를 이번 실행의 성공 결과로 읽지 않도록 호출 측에서 **현재 종료 코드**를 확인해야 한다. BLOCK은 검사 자체가 실패한 것이 아니라 유효한 차단 판정이므로 JSON이 저장되고 종료 코드 2가 나온다. 이는 요구한 동작이다. 불리한 사례나 코드 수정 이력을 만들기 위해 결함을 꾸미지 않았다.

## 역할·완료 범위

지원자는 Python 실행 파일을 제출했다. 이번 첨부에 추가 참고 자료·도움 설명·본인의 실행 출력은 없었다. 이를 무도움 작성이나 직접 실행 확인으로 바꾸지 않는다. Codex는 원본 보존, 테스트 작성, 실제 입력 연결·반복 실행, 결과·문서 검증과 커밋을 수행했다.

이 모듈까지 원본 확인→DuckDB 적재→첫 세 품질 규칙→판정·JSON 저장이 연결됐다. **세 규칙 범위**의 코드 제출·기능 검토 완료이며 전체 20규칙·통계·UI·배포 완료가 아니다. 앞서 완료한 SQL 직접 수행과 v2 사람 실측은 재검증 과제로 바꾸지 않는다.

제출 원본 SHA-256: `d39c27e61401cf65d0729f3e4abb2daf4c4c6092176174db0f306d178d6bebe4`.

## 재현 참고

```bash
python -m pytest -q tests/test_applicant_run_quality.py
python evidence/applicant/run_quality.py --db /실제/전용/oulad.duckdb --sql evidence/applicant/quality.sql --output /별도/결과/quality.json
```

실제 경로를 사용한다. 이 명령은 재현 참고이며 같은 과제를 다시 제출하라는 추가 조건은 아니다.

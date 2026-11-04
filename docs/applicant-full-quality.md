# 지원자 전체 품질 계약 20규칙 제출·검토

2026-11-05 KST. 지원자가 `quality_full.sql`, `run_quality_full.py`를 첨부했다. **요구한 전체 20규칙의 SQL·실행·판정·저장 모듈 제출·기능 검토를 완료했다. 두 제출 원본은 수정하지 않았다.** 기존 세 규칙의 제출물도 별도로 보존한다.

[SQL 원본](../evidence/applicant/quality_full.sql) · [Python 원본](../evidence/applicant/run_quality_full.py) · [실행 증거](../reports/applicant-full-quality.json) · [Codex 검토 테스트](../tests/test_applicant_full_quality.py) · [고정 요구사항](applicant-full-quality-spec.md).

## 실제 OULAD 결과

이전 지원자 검증·적재 모듈로 실제 원본을 임시 DB에 적재한 뒤 두 제출 파일을 그대로 실행했다. JSON 범위는 `full_quality_20`, 판정은 **REVIEW**, 종료 코드는 0이었다. 20개 rule_id·severity·건수가 기존 보고서와 모두 일치했다.

| 양수로 관측된 규칙 | 건수 | severity |
|---|---:|---|
| registration_missing_date | 45 | review |
| event_exact_repeat | 787,170 | review |
| event_daily_key_repeat | 2,195,960 | review |
| event_after_withdrawal | 29,440 | review |
| event_after_course | 4,374 | review |

나머지 15규칙은 0이다. 전체 계약에는 block 14규칙·review 6규칙이 있으며 review 중 5규칙이 양수였다. 두 번 실행한 JSON 바이트가 같았다. 원본 CSV·manifest·제출 파일과 DB의 해시·수정 시각이 유지됐다. 검토용 DB는 임시 폴더에만 생성했으며 기존 분석 결과를 변경하지 않았다.

## 경계·실패 사례 검토

Codex가 손계산 가능한 입력과 실행 실패 사례로 작성한 **51개 검사 통과**:

- 빈 입력과 정상 입력에서 20규칙 0, 동일 행과 일별 키의 서로 다른 반복 정의, 여러 결측값을 가진 한 행의 단일 계산.
- D−1/0/6/7/13/14 경계: 등록일·탈퇴일과 같은 날은 각각 이전/이후가 아니며, 개설 길이와 같은 상대 날짜는 기간 밖으로 계산. NULL 날짜는 0으로 대체하지 않음.
- 등록·콘텐츠·개설기의 복합키, 존재하지 않는 참조, 필수키 NULL, 비양수 클릭·기간, 등록/탈퇴 시점 역전, NULL 키의 반복 초과.
- 중복 등록·개설기 행이 있어도 `EXISTS`로 원본 활동 한 행을 한 번만 셈. 별도 키 반복 규칙은 BLOCK 상태를 나타냄.
- Python이 20개 ID와 고정 severity를 검사해 누락·추가·중복·severity 변경·NULL·bool·음수·정수가 아닌 건수를 거절. SQL 출력 순서가 달라도 정규화된 결과 유지.
- PASS/REVIEW/BLOCK의 판정·종료 코드·저장, BLOCK 우선, 쓰기 SQL 거절, 입력 누락·빈 SQL·저장 실패·출력 경로 충돌 처리와 기존 보고서 보존.

중복 기준 행을 사용한 날짜 검사 예시에서는 등록 3행·개설기 3행·콘텐츠 2행과 활동일 −1/7/14의 활동 3행을 사용했다. 등록일0·탈퇴일6·개설 길이14에서 기대 날짜 위반은 등록 이전1 / 탈퇴 이후2 / 개설 기간 이후1이었다. 제출 SQL은 이 기대값과 일치했고 JOIN에 의한 곱셈 증가가 없었다. 이 예시는 Codex가 만든 시험 자료이며 실제 사용자 기록이나 지원자가 만든 테스트로 세지 않는다.

## 역할과 해석

지원자는 전체 규칙 SQL과 실행 Python을 제출했다. 추가 참고 자료·도움 내역·본인 실행 출력은 이번 첨부에 없었다. Codex는 원본 보존, 테스트 작성, 실제 원본 연결·반복 실행·기존 보고서 대조, 문서·커밋을 담당했다. 코드 수정이나 실제로 발견하지 않은 실패·수정 과정을 만들지 않았다.

완료한 범위는 **20개 원본 품질 규칙과 실행 연결**이다. 반복 행이 실제 전송 오류라는 결론, 로그 완전성, 서비스 성과 또는 전체 통계·UI·배포 구현 완료를 뜻하지 않는다. 서로 충돌하는 차원 키가 있으면 날짜 결과가 나와도 BLOCK 규칙을 무시해서 분석에 쓰면 안 된다. 이미 완료한 SQL 실습·이전 Python 모듈·v2 사람 실측은 그대로 유지한다.

## 재현 참고

```bash
python -m pytest -q tests/test_applicant_full_quality.py
python evidence/applicant/run_quality_full.py --db /실제/전용/oulad.duckdb --sql evidence/applicant/quality_full.sql --output /별도/결과/quality-full.json
```

경로는 환경에 맞춰 바꾼다. 이는 재현 참고이며 완료한 검토의 반복 제출을 요구하지 않는다. 실패한 새 실행에서 이전 보고서가 보존될 수 있으므로 현재 종료 코드를 함께 확인한다. 제출 파일의 SHA-256은 검증 JSON에 보존했다.

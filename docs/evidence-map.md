# 주장과 근거 파일

기존 완료 상태와 표현 범위는 [종합 정리](project-handoff.md), 2026-11-06 사용자가 선택한 후속 구현은 [현재 완료 계획](applicant-completion-plan.md)을 따른다. 아래 근거의 역할·날짜를 유지하고 후속 작성 안내를 실제 제출·완료 근거로 세지 않는다.

2026-11-02 직무 보완: [제품 대안과 선택 조건](product-decision.md), [생성 구독 연결 SQL](subscription-bridge.md), [전체 운영 입력 방식 v2](full-operations-v2.md). 당시 구현은 Codex의 작업이며 실제 서비스 가설 검증·갱신 성과·지원자의 독립 작성으로 표현하지 않는다. 이후 2026-11-05 별도 v2 사람 실측은 [완료 결과](full-operations-v2-human-results.md)로 구분한다. 2026-11-04 [안내 SQL 실습](independent-sql-task.md)의 실행·필터 적용 결과를 수신했다. 예제와 수정 조건은 Codex 제공이며 독립 작성으로 확대하지 않는다.

자소서와 제출용 포트폴리오 작성 전에 **지원자가 실제로 실행·이해한 범위**와 아래 측정 사실을 대조한다. 이 문서는 자소서 문장이 아니다.

후속으로 [활동 기준 비교의 세 단계](applicant-threshold-analysis.md)를 완료했다. 지원자 제출 SQL·가상 8행·손계산·출력·판단을 보존하고 Codex가 재실행했다. 앞선 예제와 실행·합산 비율 안내 등 도움을 함께 공개한다. 이 근거는 제출·검증·판단 경험에 사용할 수 있으며 회사의 재방문 개선이나 전체 독립 구현으로 표현하지 않는다.

| 활용 가능한 측정 사실 | 근거 | 말하면 안 되는 확대 해석 |
|---|---|---|
| 공식 공개 학습 자료를 관계형 키·기간·결측 기준으로 검증 | `data/manifest.json`, `sql/quality.sql`, `sql/dimensions.sql` | CLASS101 운영 로그를 관리했다 |
| 동일 값 반복과 처리 민감도를 발견하고 활동일 지표를 채택 | `reports/report.json`의 quality/click_sensitivity, `sql/marts.sql` | 787,170개 오류를 고쳐 회사 데이터를 정확하게 만들었다 |
| SQL 결과를 독립 pandas 계산과 대조 | `scripts/crosscheck.py`, `reports/crosscheck.json` | 외부 기관이 정확성을 인증했다 |
| 다음 주 활동과 첫 주 활동일 사이의 관계·반례를 분석 | `reports/findings.md`, temporal/cohorts/first_day_strata | 재방문을 22.8%p 개선했다 |
| 생성 로그에서 누락·중복·지연·재수집을 재현 | `data/synthetic/`, `src/journey/faults.py`, `sql/faults.sql` | 실제 회사 장애를 복구했다 |
| 반복 점검을 명령과 이슈 이력으로 자동화, 실행 시간 측정 | `scripts/analyze.py`, `src/journey/tracker.py`, `reports/benchmark.json` | 분석가 근무 시간을 특정 % 줄였다 |
| 잘못된 입력·시간 경계·빈/오류 UI를 테스트하고 수정 | `tests/`, `docs/verification.md`, `docs/learning-log.md` | 자동 검사를 실제 사용자 피드백으로 표현한다 |
| 공개 정적 분석 도구를 배포하고 브라우저에서 확인 | 배포 URL, `reports/browser-deployed.json`, `reports/deployment.json` | 실시간 분석 백엔드/프로덕션 로그 파이프라인을 운영한다 |
| 서비스 맥락에 맞는 실험과 추가 계측을 설계 | `docs/experiment-plan.md`, JSON experiment | 실험으로 매출/연간 구독 효과를 검증했다 |
| AI가 작성한 초안을 테스트·대조하는 개발 과정 | `docs/research/sources.md`, 테스트와 커밋 | 지원자가 코드와 조사 전체를 독립적으로 수행했다 |

## 직접 수행에 사용할 사실과 역할

완료한 실습을 다시 요구하지 않는다. 다음은 제출 문안이 아니라 근거 선택을 위한 사실 목록이다.

| 설명 가능한 사실 | 근거와 역할 | 적용 한계 |
|---|---|---|
| 기존 프로젝트를 참고해 활동일 기준 비교 SQL을 제출·실행하고 가상 자료 손계산과 대조 | 지원자 제출; Codex의 문제 제시·실행 안내·검토와 재실행. [SQL·가상 자료·결과](applicant-threshold-analysis.md) | 무도움 작성이나 전체 분석 파이프라인 독립 구현은 아님 |
| 대상 4,803건 감소와 관찰 비율 +3.1%p를 비교해 높은 비율만으로 기준 변경을 정당화하지 않음 | 지원자의 계산·이유·인과 한계 설명. [원문](../reports/applicant-threshold-analysis.json) | 활동 기준 변경의 타당성 검토이며 최적 정책·인과 효과 확정 아님 |
| 직접 비교 측정에서 입력 오류와 전체 재시작 부담을 경험하고 결과 전달 | 지원자 측정·사유 전달, Codex의 도구 v2 구현·검증. [실측](full-operations-human-results.md), [개선](full-operations-v2.md) | 후속 v2 사람 실측 6회 완료. [중단 포함 결과](full-operations-v2-human-results.md)를 보존하며 회사 생산성·버전 간 인과 효과로 확대하지 않음 |
| 별도 참여자의 데모 응답을 전달하고 수정 후 재검토 결과를 확인 | 지원자 진행·응답 전달, Codex 문구 수정. [사용성 기록](usability-results.md) | 실제 CLASS101 사용자 연구나 정책 채택·매출 성과는 아님 |

문서·SQL·증거 파일의 저장과 이번 문서 커밋은 Codex의 작업이다. 지원자의 실제 커밋은 참여 기록에 연결된 테스트 추가 커밋과 구분한다. 다른 기법의 개인 숙련, 추가 사람 실측, 실제 회사 적용을 이번 실습의 새 완료 조건으로 붙이지 않는다.

## 추가 실제 데이터·실행 검증

| 활용 가능한 사실 | 근거 | 확대하면 안 되는 주장 |
|---|---|---|
| EdNet KT4 실제 2,048명·854,678행을 확보하고 SQL/pandas로 대조 | `docs/ednet-analysis.md`, `reports/ednet_report.json`, `data/ednet_snapshot.json` | CLASS101 로그를 분석했다; 신규 가입자 유지율을 확정했다 |
| 이벤트 정의에 따라 첫 주 2일 이상 여부 23명, 다음 주 기록 여부 14명 변경 | `sql/ednet.sql`, 보고서 quality | 재방문을 개선했다 |
| 실제 구매 173행·환불 5행 확인, 권한·매출·갱신은 판단 보류 | 보고서 payments | 173건의 구독 갱신·매출을 확인했다 |
| 18개 가상 모집 시나리오와 합성 입력의 배정·지연·가드레일 검사 실행 | `reports/experiment-readiness.json`, `tests/test_experiment_readiness.py` | 실제 20명을 모집했다; A/B 효과 검증을 했다 |
| 같은 3개 규칙 검토표를 지원자 1명이 각 방식 3회 수행; 작업 구간 중앙값 A 40.27초/B 14.20초 | `docs/human-comparison-results.md`, `reports/human-comparison.json` | 회사 생산성이 개선됐다; 전체 분석 시간이 줄었다; 오류가 감소했다 |
| 안내받은 실습·직접 Actions 실행·제공 테스트 추가 커밋·실측 JSON 제출 | `docs/participation.md` | 지원자가 분석·코드 전체를 독립 수행했다 |

최종 캡처와 각 파일의 의미는 [포트폴리오 근거 모음](portfolio-evidence.md), 완료한 직접 수행과 증거의 범위는 [참여 기록](participation.md)에서 확인한다.

## 실제 데모 사용성 검토의 범위

지원자가 참여자 1명의 네 과제 응답·경로·도움 여부를 전달하고 익명 요약 공개 동의를 확인했다. 369건의 핵심 설명은 확인했으나, 검증 계획의 의미와 실행 여부 구분은 전달된 응답에서 완료 기준을 충족하지 못해 Codex가 문구를 수정했다. 근거는 [사용성 결과](usability-results.md)와 `web/index.html`, `web/catalog.js`다. 지원자가 진행한 실제 검토와 Codex가 작성한 UI 수정 코드를 구분한다. 수정 후 같은 참여자에게 요청한 재검토에서 더 읽기 편하다는 평가와 추가 질문 뒤 목적 설명을 받았다. 실험 미실행 상태 구분은 미확인이며, 문구 수정만의 인과 효과·신규 사용자 성공률·실제 서비스 효과는 말할 수 없다.

## 추가 제출: 원본 검증 Python

지원자가 7 CSV의 존재·SHA-256·크기를 점검하는 Python 파일을 제출했다. 파일을 작은 구간으로 읽고 누락·불일치·manifest 오류를 종료 코드로 구분한다. 제출본 논리 수정 없이 Codex의 15개 검사와 실제 원본 검사를 통과했다. [원본·실행·역할 근거](applicant-source-validation.md). 테스트 작성과 재실행은 Codex의 작업이며 지원자가 수행했다고 소급하지 않는다.

## 추가 제출: DuckDB 적재 Python

지원자 제출 적재 코드는 원본 검증 성공 후에만 DB를 열고, 7개 테이블 적재를 하나의 트랜잭션으로 처리한다. Codex의 11개 검토 검사와 실제 CSV 7개의 독립 행 수 대조를 통과했다. [출처·검토·역할](applicant-source-loading.md). 지원자 코드 원본과 Codex 작성 테스트를 구분하며, 전체 구현 완료나 실제 회사 로그 운영으로 표현하지 않는다.

## 추가 제출: 품질 SQL 세 규칙

지원자가 등록일 결측, 여섯 열이 같은 활동의 초과 행, 등록 복합키가 없는 활동을 계산하는 SQL을 제출했다. `GROUP BY`의 초과 합계와 `NOT EXISTS`가 손계산 사례를 통과했고 실제 45 / 787,170 / 0과 일치했다. [제출 원본과 Codex 검증](applicant-quality-sql.md). 이는 원본의 세 품질 규칙 구현이며 실제 회사 로그 오류 복구나 전체 품질 계약 완료로 확대하지 않는다.

## 추가 제출: 품질 판정·결과 저장 Python

지원자가 기존 품질 SQL을 읽기 전용 DB에서 실행하고 결과 계약·판정·JSON 저장·종료 코드를 연결하는 Python 파일을 제출했다. Codex의 25개 검사와 실제 자료 반복 실행을 통과했다. [원본·검증·역할](applicant-quality-runner.md). JSON의 first_three_rules 범위를 유지하며 전체 품질 계약이나 실제 회사 운영 완료로 확대하지 않는다.

## 추가 제출: 전체 품질 계약 20규칙

지원자가 처음 세 규칙을 확장한 SQL과 실행 Python을 제출했다. 20개 규칙의 계약·판정·저장이 Codex의 51개 검사와 실제 원본 대조를 통과했다. 특히 날짜 검사의 EXISTS와 별도 키 반복 BLOCK을 함께 사용했다. [제출 원본·결과·역할](applicant-full-quality.md). 이는 원본 품질 계약 구현의 근거이며 실제 회사 장애 복구나 완전한 수집 보장으로 확대하지 않는다.

## 수강 건별 분석표 SQL·Python 제출·검토 (2026-11-05 KST)

지원자가 `build_mart.sql`, `build_mart.py`를 제출했다. 원본 수정 없이 Codex의 43개 검사와 실제 OULAD 대조를 통과했다. 기본 정책은 29,671 / 23,522 / 20,303건, strict는 같은 적격 29,671건에서 23,430 / 20,210건이다. 두 정책 모두 기존 SQL 12열 및 독립 pandas 활동 지표 3열과 일치하고 반복 CSV가 같았다. [제출 원본·검사·역할](applicant-mart.md). 테스트 작성·실행과 문서화는 Codex의 작업이며 지원자의 로컬 실행을 대신 기록하지 않는다. 분석표 모듈의 제출·기능 검토 완료를 전체 통계·UI·배포 구현 완료로 확대하지 않는다.

## 전체·개설기별 활동 집계 SQL·Python 제출·검토 (2026-11-05 KST)

지원자가 `aggregate.sql`, `run_aggregate.py`를 제출했다. 제출 원본 수정 없이 Codex의 52개 검사와 실제 기본/strict 정책별 69행 대조를 통과했다. 빈 그룹을 유지하고 Python 자체 집계로 SQL의 각 행을 검증하며 반복 JSON이 동일했다. [원본·검사·역할](applicant-aggregate.md). 검토용 테스트 작성·실제 실행·문서화·커밋은 Codex의 작업이다. 이번 첨부에 지원자 로컬 실행 출력이나 별도 설명이 있었다고 기록하지 않는다. 활동 그룹의 기술 집계 모듈 제출·기능 검토 완료이며 신뢰구간이나 전체 UI·배포 완료로 확대하지 않는다.

# 통계·민감도 구현 계약

2026-11-06 KST. [남은 전체 범위](applicant-completion-plan.md)의 첫 묶음이다. 이미 만든 수강 건별 분석표를 사용해 관찰된 차이와 불확실성, 조건별 결과 변화를 계산한다. 새 분석 방법을 추가하는 과제가 아니다.

## 제출 파일과 입력

| 파일 | 역할 |
|---|---|
| `learning_stats.py` | 비교·요약·시기 분리·민감도 계산 함수. import만으로 파일 생성·분석 실행을 하지 않음 |
| `run_statistics.py` | 입력 검증 → 위 함수 실행 → 결정적인 JSON 저장과 종료 코드 |

함수 이름과 내부 구조는 직접 정해도 된다. 기존 제출의 CSV 파싱·검증·파일 저장 함수를 재사용할 수 있다. 기존 생산 코드·지표 계약도 참고할 수 있으며 참고한 부분과 직접 작성/변경한 부분을 기록한다. 기존 함수를 호출하는 연결 코드와 계산을 직접 작성한 코드는 역할을 구분한다.

명령행 입력:

- `--mart`: 기본 정책의 12열 분석표 CSV.
- `--strict-mart`: 같은 대상 수강 건의 strict 정책 CSV.
- `--db`: 앞서 검증·적재한 DuckDB. 시간 분리에 필요한 **전체 studentRegistration**을 읽기 전용으로 조회한다. mart만으로 과거 이력을 대신하지 않는다.
- `--output`: 통계 JSON.

같은 수강 건 키가 두 CSV에 각각 한 번 있어야 하며 키 집합·date_unregistration이 같아야 한다. 정렬 순서가 달라도 키로 맞춘다. 기존 12열 계약의 결측·범위·논리·중복 검증을 재사용한다. 기본/strict 의미는 호출자가 지정한 입력에서 이어지며, 파일명을 보고 정책의 진실을 자동으로 인증하지 않는다. 실제 통합 과정에서는 앞선 build_mart 실행과 연결한다.

DB가 없거나 필요한 등록 열/키가 없으면 오류다. 등록 키 결측·중복, mart 키가 등록에 없는 경우를 거부한다. 동일 학습자의 다른 개설기 등록을 중복 키로 취급하지 않는다. 등록일 결측이나 사전 탈퇴 때문에 mart에서 빠진 2013년 등록도 시간 분리의 과거 이력에 포함한다. DB를 새로 만들거나 수정하지 않는다.

## 비교의 분모와 단위

주요 비교에는 w1_days≥1 수강 건만 사용한다.

| 결과 이름 | 0 집단(control) | 1 집단(exposed) |
|---|---|---|
| repeat_comparison | 첫 주1일 | 첫 주2일 이상 |
| content_comparison | first_content=0 | first_content=1 |

control/exposed는 기존 결과와 연결하기 위한 필드 이름이다. 무작위 배정된 실험군·대조군이라는 뜻이 아니다. 분모는 수강 건, 분자는 그중 w2_active=1이다. 같은 사람이 여러 수강 건을 가질 수 있다.

비교 결과의 필드:

- `control`, `exposed`: 각각 `{n, returned, rate}`. rate는 **0~1 비율**, 분모0은 null.
- `difference`: 1 집단 rate − 0 집단 rate. **비율 차이**로 저장하고 화면에서100배해 %p로 표시한다. 집단 하나가 비면 null.
- `ci`: difference의 95% 군집 부트스트랩 구간 `[lower, upper]`, 계산 불가하면 null.
- `clusters`: 비교에 들어간 고유 id_student 수.
- `bootstrap_draws`: 시도하기로 한 재표집 수. `valid_draws`: 양쪽 분모가 모두 있어 실제 구간 계산에 사용한 수.

## 학습자 단위 부트스트랩

쉽게 말하면 같은 학습자의 수강 건들을 한 묶음으로 다시 뽑아, 관찰 차이가 얼마나 흔들리는지 확인하는 계산이다. 같은 사람의 여러 수강 건을 서로 독립인 사람처럼 뽑지 않는다.

1. 비교 대상의 고유 id_student를 오름차순으로 정렬한다.
2. **각 비교 호출마다** NumPy `default_rng(101)`을 새로 만든다. 반복 횟수는 전체·시간 분리1,000회, 개설기·최초 활동일500회다.
3. 매회 고유 학습자 수 K개를 K명에서 복원 추출한다. 기준 재현은 `rng.integers(0, K, K)`의 인덱스 순서다. 한 사람이 두 번 뽑히면 그 사람의 해당 범위 모든 수강 건도 두 번 기여한다. 뽑힌 ID를 set으로 바꾸지 않는다.
4. 뽑힌 수강 건들의 양쪽 분자·분모를 다시 합쳐 비율 차이를 계산한다. 어느 한쪽 분모가0이면 그 회차를 건너뛰고 valid_draws를 늘리지 않는다. 그 차이를0으로 채우지 않는다.
5. 유효 차이의2.5/97.5 백분위, NumPy quantile의 linear 방법을 사용한다.
6. 원래 한쪽 집단이 비면 difference/ci는 null, valid_draws=0. 양쪽은 있지만 어느 집단의 고유 학습자가2명 미만이면 점 차이만 남기고 ci=null, valid_draws=0. 유효 추출이 하나도 없으면 ci=null.

위 seed·정렬·추출 순서는 기존 결과 재현을 위한 계산 계약이다. 검토에서는 같은 정의의 작은 사례와 실제 결과를 비교한다. 불가피한 라이브러리 차이는 근거를 확인하며, 출력 숫자를 하드코딩하거나 다를 때 숨겨 맞추지 않는다. 이 구간은 선택 편향·미관측 교란·회사로의 일반화 문제를 해결하지 않는다.

### 재표집을 이해하기 위한 생성 예시

다음은 실제 자료가 아닌 설명용4수강 건이다. 다시 손계산 답변을 제출하는 과제가 아니라 코드 검토에 사용할 기준이다.

| 학습자 | 수강 건 | w1_days | w2_active |
|---|---|---:|---:|
| A | 강좌X | 1 | 0 |
| A | 강좌Y | 2 | 1 |
| B | 강좌X | 1 | 1 |
| C | 강좌Y | 2 | 0 |

원래 두 집단 비율은 각각1/2여서 차이는0이다. 학습자 추출이 `[A,A,B]`이면 A의 두 수강 건이 각각 두 번 기여한다. 1일군은1/3,2일 이상군은2/2, 차이는2/3이다. `[B,B,B]`이면2일 이상군 분모가 없어 무효 추출로 건너뛴다. A를 한 번만 남기는 중복 제거는 잘못된 재표집이다.

## 결과 묶음

### overall과 cohorts

각 범위의 요약은 다음 필드를 가진다.

- `eligible`, `w1_active`, `w2_returned`, `return_rate`, `unique_learners`.
- `days`: 활동일0~7 각각 `{days,n,returned,rate}`. 0일 그룹의 다음 주 활동도 이 표에는 표시하되 주 재방문율의 분자·분모에는 더하지 않는다. 없는 그룹은 n0/returned0/rate null.
- `repeat_comparison`, `content_comparison`: 위 비교 계약.

overall은 기본 mart 전체, cohorts는 입력에 존재하는 강좌·개설기별 요약이다. cohorts의 각 항목에는 `module`,`term`을 추가하며 키 순서로 정렬한다. 전체·개설기의 평균 비율을 다시 평균내지 않는다.

### temporal

- `id: discovery`, `label: 2013 탐색`: 기본 mart의 code_presentation이2013으로 시작하는 행.
- `id: holdout`, `label: 2014 신규 학습자 재확인`: 기본 mart의2014 행 중 **전체 studentRegistration에2013 등록 이력이 없는 id_student**만 포함.
- 각 항목에 위 요약 필드를 넣는다. 미래 수료/탈퇴 결과·W2 활동을 조건으로 대상을 고르지 않는다. 두 범위의 학습자 교집합이 없어야 한다.
- 이미 공개된 데이터를 나누는 절차다. 실제 사전등록·블라인드 검증이라고 부르지 않는다. 2013/2014가 아닌 개설기는 overall/cohorts에는 남기되 두 시기 묶음에 억지로 넣지 않는다.

### first_day_strata

기본 mart의 W1 활성 수강 건을 first_day별로 나눈다. 실제 존재하는 시작일을 오름차순으로 내보낸다. `{first_day, comparison}`이며 comparison은 해당 범위의 repeat_comparison,500회다. D6은 한 주 안에서2일 이상 활동할 수 없어 비교 불가가 정상이다.

### click_sensitivity

W1 활성 수강 건에서 임계값10/20/50 각각 계산한다. 조건은 각 first_clicks_*가 임계값 **이상**인지다.

`{threshold, raw_qualified, exact_qualified, max_qualified, raw_vs_exact_changed, raw_vs_max_changed}`.

changed는 같은 수강 건의 기준 충족 여부가 서로 다른 건수다. 두 CSV의 행 순서나 단순 비율 차이로 세지 않는다. 클릭 정책 중 어느 것도 원천 수신 진실로 확정하지 않는다.

### transition

기본 mart에서 W1 활성0/1 × W2 활성0/1의 네 조합, `(0,0),(0,1),(1,0),(1,1)` 순서로 `{w1,w2,n,later_active}`를 저장한다. later_active는 해당 조합 중 D14~27 활동이 있는 수강 건수다. 빈 조합은0이다. 네 n의 합은 eligible이며 과거/미래 조건으로 분모를 다시 줄이지 않는다.

### strict_sensitivity

`{w1_active,w2_returned,changed_w1_enrollments,changed_w2_enrollments}`.

앞의 두 건수는 strict 정책의 집계다. 뒤 두 값은 키로 맞춘 기본/strict의 w1_days 값, w2_active 값이 달라진 수강 건수다. w1_days가2→1로 바뀐 경우도 changed_w1에 포함한다. 단순 활성 여부만 비교하거나 합계의 차이로 계산하지 않는다.

## JSON과 실패 처리

최상위는 `schema_version:1`, `scope:"observational_statistics"`, `input_sha256:{mart,strict_mart,db}`, `overall`, `cohorts`, `temporal`, `first_day_strata`, `click_sensitivity`, `transition`, `strict_sensitivity`다. 입력 해시는 실제 파일 바이트를 기록하며 CSV 직렬화가 다르면 기존 참고 파일과 해시가 달라도 정상이다.

같은 입력·환경에서 결과 JSON은 반복 실행 시 같아야 한다. 비율·차이·구간은 중간 반올림 없이 저장한다. 표시 반올림은 UI에서 한다. NaN/Infinity는 JSON에 넣지 않고 계산 불가는 null로 표시한다. 입력·DB·기존 제출 SQL을 수정하지 않는다. 출력 경로가 입력과 겹치면 중단한다. 실패 시 기존 결과를 보존하고 임시 파일을 정리한다. 성공0, 입력/계산/저장 오류1로 종료한다. 신뢰구간 계산 불가는 정상적인 null 결과로, 깨진 입력은 오류로 구분한다.

입력이 비어도 열 계약이 맞으면 overall의 n0/rate null, days8개, cohorts빈 배열, temporal두 빈 요약, first_day_strata빈 배열, 임계값3개의0건, 전환4개의0건, strict변경0건을 내보낸다. 빈 입력에 적격 수강 건이 있다고 꾸미지 않는다.

## 실제 기본 자료의 주요 대조값

| 항목 | 기대값 |
|---|---|
| 전체 eligible / W1 / W2 | 29,671 / 23,522 / 20,303 |
| 1일 vs2일 이상 | 3,835/5,565 vs16,468/17,957 |
| 비율 차이·군집 구간(화면 표시) | +22.8%p, 약 +21.5~+24.0%p |
| 콘텐츠 접촉 | 5,137/6,032 vs15,166/17,490; 전체 약 +1.5%p |
| 콘텐츠 반대 방향 | 22개 개설기 중9개 |
| 2013 탐색 eligible / W1 / W2 | 12,487 / 9,902 / 8,630 |
| 2014 과거 등록자 제외 eligible / W1 / W2 | 15,435 / 12,285 / 10,568 |
| 임계값10 raw / exact / max | 14,637 / 14,268 / 13,599 |
| 임계값10 raw 대 exact 변경 | 369 |
| strict W1 / W2 | 23,430 / 20,210 |
| strict 변경 W1값 / W2값 | 127 / 134 |

[기존 통계 결과 발췌](../reports/applicant-statistics-reference.json)는 생산 보고서에서 선택한 참고값이며 새 제출 코드의 실행 결과가 아니다. 기본 점 집계는 정확히 대조하고 같은 seed·방법의 부트스트랩은 작은 부동소수 오차를 고려해 비교한다. 자료 유형·정의가 다른 임의 CSV에 위 숫자를 강제로 적용하지 않는다.

## Codex가 확인할 실패 가능성

동일 학습자의 복수 수강·재표집 중복 횟수, 비어 있는 집단·학습자1명 집단·무효 추출, 활동0일과 마지막 날6, 등록은2013에 있으나 mart에 없는 사람의2014 제외, 기본/strict 키 불일치·재정렬, 클릭 임계값의같음/미만, 빈 전환, 결과 반복성·입력 보존을 별도 예시로 확인한다. 실제 고정 OULAD와 기존 보고서 대조도 한다. 생산 보고서와 같다는 사실만을 독립 손계산 검증이라고 부르지 않는다.

## 작성·실행·제출

직접 구현하던 폴더에서 두 파일을 작성한다. 이전 검증 함수를 import한다면 해당 제출 파일들도 같은 폴더 또는 올바른 Python 경로에 있어야 한다. 기존 프로젝트의 requirements에 NumPy·pandas·DuckDB가 포함돼 있다. 설치돼 있다고 가정해 성공을 기록하지 않는다.

파일 작성 뒤의 실행 예시:

```bash
python run_statistics.py --mart work/applicant/mart.csv --strict-mart work/applicant/mart-strict.csv --db work/applicant/source.duckdb --output work/applicant/statistics.json
```

예시 경로는 본인 장치의 실제 파일 경로로 바꾼다. 없으면 [이전 분석표 실행 안내](applicant-mart.md#재현)에 따라 기존 제출 코드로 만들 수 있다. 기존 파일을 새로 내려받아 덮어쓰거나 완료한 사람 실측을 다시 시작하지 않는다.

제출은 두 Python 파일과 참고한 자료·도움 범위다. 실행했다면 전체 요약 출력과 주요 선택 이유도 함께 남길 수 있다. 개인 수준 CSV는 공개하지 않는다. 작성 중 막힌 곳이 있으면 그 부분까지 보내면 된다. Codex가 완성 코드를 대신 작성하면 그 부분은 도움받은 구현으로 구분한다.

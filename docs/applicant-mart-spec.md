# 다음 구현: 수강 건별 학습 분석표

원본 검증·적재·전체 20규칙 품질 검사의 제출·기능 검토를 완료했다. 다음은 기존 프로젝트 범위인 수강 건별 분석표(mart)다. 이미 제출한 활동 기준 비교 SQL은 이 분석표의 `w1_days`, `w2_active`를 사용하므로 재사용할 수 있다. 새 통계 기법이나 UI 기능을 추가하는 과제가 아니다.

제출 파일은 `build_mart.sql`, `build_mart.py` 두 개다. 원본·기존 분석 DB 테이블을 수정하지 않고 별도 CSV로 내보낸다. 참고 정의는 [기존 데이터 계약](data-contract.md)이다.

## 대상과 시간

행 단위는 `(code_module, code_presentation, id_student)` 수강 건이다. 다음 조건을 모두 충족하는 등록을 포함한다.

- date_registration ≤ 0. NULL은 포함하지 않으며 0으로 대체하지 않는다.
- date_unregistration이 NULL이거나 ≥ 0. 개강 후 탈퇴했다고 분모에서 제거하지 않는다.
- 대응 개설기의 module_presentation_length ≥ 28.

D0는 가입일이나 첫 학습일이 아니라 개강일이다. 첫 주는 0~6, 다음 주는 7~13, 후속은 14~27이며 양끝을 포함한다. 입력은 이미 적재한 studentRegistration, courses, studentVle, vle다.

## SQL 결과

SQL은 읽기 전용 SELECT로 작성하고 DuckDB 이름 매개변수 `$strict`(boolean)를 받는다. 유효 활동은 대상 수강 건과 콘텐츠의 복합키가 일치하고, sum_click > 0이며 date가 0~27인 행이다. 콘텐츠 조인은 강좌·개설기·id_site를 모두 사용한다.

- strict=False: 위 유효 활동을 사용한다. 탈퇴 이후라는 이유만으로 제거하지 않는다.
- strict=True: 동일한 대상 수강 건을 유지하면서 활동일이 등록일 이상이고, 탈퇴일이 있으면 탈퇴일 이하인 활동만 사용한다. 탈퇴 당일은 포함한다.
- 활동이 없는 적격 수강 건도 결과에 남긴다. 동일한 날짜에 행이 여러 개여도 활동일은 한 번만 센다.

다음 12열을 반환하고 수강 건 키 순서로 정렬한다.

| 열 | 의미 |
|---|---|
| code_module, code_presentation, id_student | 수강 건 키 3열 |
| w1_days | 첫 주의 고유 유효 활동일 수, 0~7 |
| w2_active | 다음 주 활동 하나 이상이면 1, 없으면 0 |
| later_active | 14~27일 활동 하나 이상이면 1, 없으면 0 |
| first_day | 첫 주 최초 유효 활동일. 첫 주 활동 없으면 NULL |
| date_unregistration | 원본 등록의 탈퇴일. NULL을 보존 |
| first_content | first_day에 oucontent/resource/subpage/page 중 하나 이상의 콘텐츠 접촉이 있으면 1, 없으면 0 |
| first_clicks_raw | first_day의 양수 클릭을 원본 행 그대로 합산 |
| first_clicks_exact | first_day에서 같은 콘텐츠의 동일 클릭 값을 한 번씩 합산하고 콘텐츠별 합계를 더함 |
| first_clicks_max | first_day에서 콘텐츠별 최대 클릭을 선택한 뒤 콘텐츠 간 합산 |

첫 주 활동이 없으면 first_content와 클릭 3열은 0이다. 예를 들어 같은 콘텐츠·같은 날짜의 클릭이 4,4,2라면 raw=10, exact=6, max=4다. 클릭 정책 중 어느 것도 실제 수신 진실이라고 단정하지 않는다.

## Python 실행 연결

입력은 `--db`, `--quality-sql`, `--mart-sql`, `--output`, 선택 플래그 `--strict`다. `--strict`가 없으면 False다.

1. 기존 전용 DB를 읽기 전용으로 열고 **현재 DB에 대해** 전체 품질 SQL을 실행한다. 이미 제출한 `run_quality_full.py`의 결과 검증·판정 기능을 재사용할 수 있다. 이전 JSON의 gate만 믿고 진행하지 않는다.
2. 품질 결과 계약이 유효하고 gate가 PASS/REVIEW이면 분석표를 생성한다. BLOCK이면 종료 코드 2로 끝내고 새 CSV를 만들거나 기존 CSV를 교체하지 않는다. 차원 중복 때문에 분석 조인에서 행 수가 늘어나는 것을 막는 조건이다.
3. SQL에 strict 값을 전달하고 결과를 CSV로 저장한다. 헤더는 위 12열, 불필요한 행 번호 열은 제외한다. 입력 DB·SQL 경로를 출력으로 덮어쓰지 않는다. 실행·쓰기 오류는 종료 코드 1, 정상 완료는 0이다. 실패를 정상 CSV 생성으로 표시하지 않는다.
4. 콘솔에 품질 gate, strict 여부, 적격 수강 건수, 첫 주 활성 건수, 첫 주 활성 중 다음 주 활동 건수를 출력한다. 기계 실행을 실제 사용자 성과로 표현하지 않는다.

기본 정책의 실제 고정 OULAD 기준은 적격 29,671 / 첫 주 활성 23,522 / 그중 다음 주 활동 20,303이다. 이는 출력 대조 기준이며 SQL에 상수 결과를 넣지 않는다. strict 결과·날짜 경계·반복 행·첫 주 비활성·활동 없는 수강 건은 Codex가 별도 예시로 검토한다.

두 파일과 참고 자료/도움 범위를 제출한다. 실행했다면 집계 출력만 함께 보낼 수 있다. 학습자 키가 담긴 전체 CSV는 공개 저장소에 커밋하지 않는다. 이번 분석표 구현 완료와 통계·UI·배포의 완료 상태는 구분한다.

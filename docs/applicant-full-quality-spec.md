# 다음 구현: 기존 품질 계약 20개로 확장

첫 세 규칙과 실행·판정·저장 연결은 이미 검토를 마쳤다. 여기서는 원래 프로젝트 범위인 전체 20규칙으로 확장한다. 새로운 제품 기능을 추가하는 과제가 아니다. 기존 제출 원본은 보존하고 `quality_full.sql`, `run_quality_full.py` 두 파일로 제출한다. 앞선 SQL·Python을 재사용할 수 있다.

## SQL 출력 계약

열은 `rule_id`, `severity`, `issue_count`, 행은 아래 정확히 20개다. severity는 소문자 `block` 또는 `review`, 건수는 0 이상의 정수다. `*_repeat`는 각 그룹에서 첫 행을 제외한 초과 행 합계다. 그 외는 조건을 만족하는 원본 행 수이며 여러 결측·여러 대응 행 때문에 같은 원본 행을 중복 계산하지 않는다. SQL은 읽기 전용이다.

| rule_id | severity | 셀 대상 |
|---|---|---|
| registration_missing_date | review | studentRegistration의 date_registration NULL |
| event_exact_repeat | review | studentVle의 강좌·개설기·학습자·콘텐츠·date·sum_click 여섯 열이 같은 초과 행 |
| event_unknown_student | block | studentVle의 id_student가 NULL이 아니며 등록의 강좌·개설기·학습자 조합에 없는 활동 행 |
| event_required_null | block | studentVle의 code_module, code_presentation, id_student, id_site, date, sum_click 중 하나 이상 NULL인 행 |
| event_nonpositive_click | block | studentVle의 sum_click ≤ 0 |
| event_daily_key_repeat | review | studentVle의 강좌·개설기·학습자·콘텐츠·date 다섯 열이 같은 초과 행. sum_click은 묶음에서 제외 |
| event_unknown_site | block | studentVle의 id_site가 NULL이 아니며 vle의 강좌·개설기·콘텐츠 조합에 없는 활동 행 |
| registration_inverted_dates | block | studentRegistration의 date_registration > date_unregistration |
| registration_key_repeat | block | studentRegistration의 강좌·개설기·학습자 키 반복 초과 |
| site_key_repeat | block | vle의 강좌·개설기·콘텐츠 키 반복 초과 |
| course_key_repeat | block | courses의 강좌·개설기 키 반복 초과 |
| event_before_registration | review | 해당 강좌·개설기·학습자의 등록 행과 비교해 활동 date < date_registration인 활동 행 |
| event_after_withdrawal | review | 해당 강좌·개설기·학습자의 등록 행과 비교해 활동 date > date_unregistration인 활동 행 |
| event_after_course | review | 해당 강좌·개설기에서 활동 date ≥ module_presentation_length인 활동 행 |
| registration_required_null | block | studentRegistration의 code_module, code_presentation, id_student 중 하나 이상 NULL |
| site_required_null | block | vle의 code_module, code_presentation, id_site, activity_type 중 하나 이상 NULL |
| course_required_null | block | courses의 code_module, code_presentation 중 하나 이상 NULL |
| course_invalid_length | block | courses의 module_presentation_length NULL 또는 ≤ 0 |
| registration_unknown_course | block | 등록의 강좌·개설기 키가 둘 다 NULL이 아니면서 courses에 해당 조합이 없는 등록 행 |
| site_unknown_course | block | vle의 강좌·개설기 키가 둘 다 NULL이 아니면서 courses에 해당 조합이 없는 콘텐츠 행 |

강좌·개설기·학습자·콘텐츠 열 이름은 각각 `code_module`, `code_presentation`, `id_student`, `id_site`다. 날짜의 NULL을 0으로 채우지 않는다. 비교할 등록·개설기 행이 없다면 날짜 위반으로 임의 분류하지 않고 관계 검사에서 잡는다. 날짜 검사에서는 조건을 만족하는 대응 행이 하나 이상 있어도 원본 활동 한 행당 한 번만 센다. 기준 키가 반복·충돌하면 별도 block 규칙이 활성화되므로 날짜 검사만으로 원본 의미를 확정하지 않는다.

## Python 실행·결과 계약

입력 `--db`, `--sql`, `--output`, 읽기 전용 DB, 오류 시 입력/기존 보고서 보존과 원자적 JSON 교체 등은 이미 제출한 실행 코드를 재사용한다.

- 위 20개의 rule_id·severity 매핑이 정확한지 확인한다. 누락·추가·중복 규칙, 바뀐 severity, 음수·NULL·bool·정수가 아닌 건수는 실행 오류다.
- block 규칙 중 양수 하나라도 있으면 BLOCK. 없고 review 규칙 중 양수가 있으면 REVIEW. 모두 0이면 PASS.
- JSON은 `scope: "full_quality_20"`, `gate`, `checks`를 포함한다. 각 check에 `rule_id`, `severity`, `issue_count`를 저장한다.
- PASS/REVIEW 종료 0, 유효한 BLOCK 판정 종료 2, 인자·입력·SQL·결과·저장 오류 종료 1을 유지한다.

실제 고정 원본의 review 양수는 등록일 결측45, 반복 초과787,170, 일별 복합키 반복2,195,960, 탈퇴 이후29,440, 개설 기간 이후4,374다. 나머지는 0이며 전체 판정은 REVIEW다. 이는 기존 보고서의 비교 기준이다. 작은 가상 사례에서도 구현이 맞는지는 Codex가 별도로 검토한다.

두 파일과 참고한 자료/도움 범위를 제출한다. 구현 방법은 지원자가 정하며 이 문서는 완성 SQL·Python을 제공하는 답안이 아니다. 이번 범위가 완료되면 전체 품질 계약 구현으로 기록한다. 통계·UI·배포까지 완료했다고 확대하지 않는다.

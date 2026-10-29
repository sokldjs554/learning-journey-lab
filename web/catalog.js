'use strict';
const ruleText={
 registration_required_null:['등록 필수키 결측','익명 수강 건이 분모에 들어가지 않도록 집계 전에 차단.'],
 site_required_null:['콘텐츠 필수값 결측','식별 키와 콘텐츠 유형의 결측을 차단.'],
 course_required_null:['개설기 필수키 결측','개설기 식별 불가 시 집계 차단.'],
 course_invalid_length:['개설 기간 유효성','결측 또는 0 이하 길이는 집계 전에 차단.'],
 registration_unknown_course:['등록→개설기 참조','존재하지 않는 개설기가 INNER JOIN에서 사라지기 전에 차단.'],
 site_unknown_course:['콘텐츠→개설기 참조','콘텐츠가 참조하는 개설기의 존재 여부 확인.'],
 event_exact_repeat:['동일 값 반복','모든 값이 같은 초과 행. 수신 중복인지 반복 활동 집계인지 미확정. 임의 제거 대신 클릭 민감도를 제시하고 활동일 지표 사용.'],
 event_daily_key_repeat:['일별 복합키 반복','학습자·자료·개설기·날짜가 같은 초과 행. 행을 곧 이벤트로 해석하지 않음.'],
 registration_missing_date:['등록일 결측','분석 분모에서 제외. 등록일을 0으로 대체하지 않음.'],
 event_after_withdrawal:['탈퇴일 이후 활동','동기화 시차·등록 정의 등 원인 미확정. 기본 분석은 보존하고 등록 기간 제한 결과를 별도 비교.'],
 event_after_course:['개설 기간 이후 활동','복습 또는 추출 기준 가능성. 원본은 보존; 첫 28일 분석에 영향 없음.'],
 event_before_registration:['등록일 이전 활동','개강 전 음수 날짜 자체는 오류가 아님. 등록일보다 앞선 기록만 검사.'],
 event_required_null:['활동 필수값 결측','학습자·콘텐츠·개설기·날짜·클릭 수의 결측 검사.'],
 event_nonpositive_click:['0 이하 클릭','활동 지표에서 제외. 원천 정의와 수집 오류 확인 필요.'],
 event_unknown_student:['미등록 학습자 키','복합 등록 키와 일치하지 않는 행. 격리 및 집계 보류.'],
 event_unknown_site:['콘텐츠 키 불일치','개설기까지 포함한 콘텐츠 키 대조.'],
 registration_inverted_dates:['등록·탈퇴 시점 역전','탈퇴일이 등록일보다 빠른 기록 검사.'],
 registration_key_repeat:['등록 키 유일성','중복 차원 키가 있으면 JOIN 전에 실행 중단.'],
 site_key_repeat:['콘텐츠 키 유일성','중복 차원 키가 있으면 JOIN 전에 실행 중단.'],
 course_key_repeat:['개설기 키 유일성','중복 차원 키가 있으면 JOIN 전에 실행 중단.']};

const ReviewCatalog = {
 event_exact_repeat: {question:'클릭 수를 첫 학습 성공 기준으로 사용해도 되는가', expected:'원천 이벤트 ID가 없어 유일성을 확정할 수 없음', unit:'초과 행', impact:'10클릭 기준 · 처리 정책 비교', action:'클릭 기준 보류 · 활동일 사용', before:'같은 값의 행은 수집 중복일 것이라는 초기 기대', finding:'일별 집계에는 동일 값 반복이 있지만 원천 이벤트 ID가 없습니다.', change:'반복 행을 삭제한 한 가지 결과 대신 세 정책의 차이를 비교했습니다.', next:'원천 집계·수집 규약 확인 전 클릭 임계값을 의사결정 기준으로 확정하지 않습니다.'},
 event_daily_key_repeat: {question:'일별 복합키를 이벤트의 유일키로 볼 수 있는가', expected:'학습자 × 자료 × 개설기 × 날짜의 반복 정도 확인',unit:'초과 행',impact:'일별 집계 단위 · 클릭 정책', action:'행을 이벤트 1개로 해석하지 않음',before:'일별 키가 하나의 기록을 식별할 것이라는 기대',finding:'같은 일별 키가 반복됩니다. 동일 값 반복 규칙과 대상이 겹칩니다.',change:'클릭 수의 처리 민감도와 고유 활동일을 분리했습니다.',next:'겹치는 규칙의 건수를 합산하지 않고 원천 집계 단위를 확인합니다.'},
 event_after_withdrawal: {question:'탈퇴 이후 활동을 제외하면 재방문 판단이 달라지는가', expected:'활동 날짜와 등록 자료의 탈퇴일 대조',unit:'활동 행',impact:'등록 기간 정책 · 재방문 분모',action:'원본 보존 · 제외 정책과 비교',before:'탈퇴 이후 기록을 모두 잘못된 활동으로 제거하는 접근',finding:'등록 동기화나 탈퇴 정의를 설명할 원천 정보가 없습니다.',change:'기본 분석은 보존하고, 탈퇴 이후 활동을 제한한 민감도를 별도로 계산했습니다.',next:'탈퇴의 실제 의미를 확인합니다. 사후 탈퇴자를 분석 대상에서 제거하지 않습니다.'},
 registration_missing_date: {question:'등록일이 없는 수강 건을 분모에 포함할 수 있는가',expected:'등록일 존재 여부 확인',unit:'등록 건',impact:'분모 확정 · 순차 제외',action:'분모 제외 · 0일 대체 금지',before:'CSV 날짜를 자동 추론해도 분석이 가능할 것이라는 접근',finding:'? 결측이 문자열 추론과 날짜 비교 문제를 일으켰습니다.',change:'결측 표현을 명시하고 등록일 없는 수강 건을 순차 제외했습니다.',next:'등록일 결측을 첫날 등록으로 보정하지 않습니다.'},
 event_after_course: {question:'개설 기간 밖의 활동이 첫 주 지표를 바꾸는가',expected:'활동 날짜 ≥ 개설 기간 검사',unit:'활동 행',impact:'관측 기간 · 첫 28일 범위',action:'보존 · 원천 의미 확인',before:'개설 종료 후 활동은 모두 오류라는 가정',finding:'복습·접근 권한·추출 시점의 의미가 확인되지 않았습니다.',change:'원본을 보존하고 분석의 시간 창을 별도로 적용했습니다.',next:'첫 28일 지표에 영향이 없는 기간 외 활동을 오류 수정 성과로 세지 않습니다.'}
};
const reviewOrder=['event_exact_repeat','event_after_withdrawal','registration_missing_date','event_after_course','event_daily_key_repeat'];
const viewCopy={
 review:['학습 지표 검토','첫 주 학습 신호를 재방문 실험에 사용할 수 있는지 검토합니다.'],
 analysis:['재방문 근거','같은 분석 범위에서 활동일·콘텐츠 접촉의 관계와 반례를 비교합니다.'],
 runs:['실행 기록','반복 점검의 실제 실행 결과와 원본 스냅샷별 이슈 상태입니다.'],
 plan:['검증 계획','공개 분석의 판단을 서비스 계측과 다음 실험의 조건으로 연결합니다.'],
 lab:['로그 장애 실습','별도 생성 장부에서 중복·누락·지연과 원천 재수집을 비교합니다.']
};

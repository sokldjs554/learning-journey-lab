# 검증 기록

## 사용성 응답에 따른 문구 보완 (2026-10-30 KST)

- 참여자 1명의 응답을 진행자를 통해 받았으며, 개인 식별 정보·직접 인용 없는 요약 공개 동의를 확인했다. [실제 응답 요약·판정 한계](usability-results.md). 수정 후 참여자 재검토는 아직 미실시다.
- 검증 계획의 제목·목적·현재 상태와 생성 검사의 의미를 쉬운 표현으로 보완했다. 대상·배정·D7–13·ITT·해석 조건은 유지했다. SQL·집계·분석 수치는 바꾸지 않았다.
- 로컬 Chromium에서 기존 주요 흐름·3개 폭·HTTP 오류 복구를 통과했다. [흐름 결과](../reports/usability-copy-local.json). 검증 계획의 1440/390/320px 가로 넘침 없음, axe 탐지 위반 0. 브랜드 색 대비의 자동 판정 불완전은 남는다. [접근성 결과](../reports/usability-copy-accessibility.json). 이 검사는 참여자 이해도 개선의 증거가 아니다.
- 소스 `79477e33c209590afc135989b9e5a563c5c10181`, Render `dep-dbi5kro473hc73em8qo0` live. 공개 파일 18개 바이트 일치 및 수정 화면의 3개 폭·axe 검사를 통과했다. [공개 검사·캡처 해시](../reports/usability-copy-deployed.json). [품질 CI 41029212940](https://github.com/sokldjs554/learning-journey-lab/actions/runs/41029212940)에서 115개 테스트(1.18초)·build·verify 통과. [브라우저 CI 41029212945](https://github.com/sokldjs554/learning-journey-lab/actions/runs/41029212945)는 Chromium 141·Firefox 142·WebKit 26 모두 success. [엔진별 실행 근거](../reports/usability-browser-engines.json). 이후 근거 문서·캡처 추가는 web 파일을 바꾸지 않는다.

## 문서·화면 최신성 재검토 (2026-10-30 KST)

- README의 자료별 결제 필드, 면접 안내의 1인 실측, 참여 근거 링크, EdNet 초기 미선정/후속 선정 이력을 맞췄다. 전체 파이프라인 사람 기준선은 미측정으로 유지한다.
- 공개 배포 b506a0a의 PC·모바일 폭 캡처를 갱신했다. 완료 전 문구가 남은 분석·검증 계획 4개 이미지를 교체했다. [캡처 출처·해시](../reports/closeout-screenshots.json). 모바일 전체 화면 캡처에 화면 밖 고정 바로가기 링크가 끼어드는 문제를 발견해, 촬영 전 스크롤을 처음으로 복귀시켰다. UI 데이터나 CSS는 바꾸지 않았다.
- 로컬 pytest 115개 통과(1.96초), build/verify 및 diff 공백 검사 통과. OULAD 결과 해시 불변. 공개 Chromium 주요 흐름·22개 개설기·SQL 링크·오류 재시도, 보조 데이터 3개 정의·18개 모집 조합·3개 폭 검사를 통과했다. [기존 흐름](../reports/browser-closeout.json) · [추가 흐름](../reports/extension-browser-closeout.json).
- 공개 자산 18개 바이트 대조와 폭 1440/390/320에서의 동일 과제·HTTP 실패 복구를 Chromium 141로 통과했다. [엔진 검사 로컬 결과](../reports/browser-engines-local-chromium.json). Firefox/WebKit은 로컬 sandbox/시스템 라이브러리 제약으로 실행하지 못했으나, Ubuntu CI로 옮겨 Chromium 141.0.7390.37·Firefox 142.0.1·WebKit 26.0 모두 통과했다. 각 엔진은 공개 파일 18개 바이트 일치, 3개 폭의 분자/분모·반대 근거·빈 검색·실측 준비 조건, HTTP 실패 후 복구를 검증했다. [전체 JSON·실행 링크](../reports/browser-engines-ci.json). WebKit을 실제 Apple Safari나 물리 장치 검사로 표현하지 않는다.
- 소스 `5d1d087489cf96bb3bdea941c20f0b169cad386b`의 [품질 CI 41023985573](https://github.com/sokldjs554/learning-journey-lab/actions/runs/41023985573)도 pytest·build·verify success. Render `dep-dbi4uva9lscs73fh3da0` live를 확인했다. 이번 변경은 공개 web 파일과 분석 결과를 바꾸지 않는다.
- 이 보완 당시 참여 동의만 확인했던 별도 사용성 검토는 이후 네 과제 응답을 받았다. [후속 결과·문구 수정·재검토 대기](usability-results.md). 자동 검사를 실제 사람의 이해도 검토로 집계하지 않는다.

## 2026-10-30 KST: 실제 자료·실행 조건 보완

- 출발점: `main` c70ecd45d21633ac042e0936bd674290678b2971, 미커밋 변경 없음. 별도 `feat/evidence-extension` 작업 트리에서 수행했다. 공고 전문과 기존 공개 배포·Actions·원본 코드를 재확인했다.
- 통합 pytest **109개 통과**. 기존 OULAD 29개를 유지하고 EdNet 표본/해시/다운로드 25개, 실험 입력 38개, 사람 실측 가져오기 6개, 보고서 계약 11개를 검증했다. 독립 리뷰 후 그룹 이름·행동 정의·음수/소수/초과 인원 5개 회귀를 추가하여 최종 **114개가 통과했다**. 원격 상태는 아래 최종 기록을 따른다.
- 기존 OULAD 전체 분석 2회 재실행: 각각 27.424초·22.070초(이번 로컬 기계 시간; 기존 3회 benchmark와 별개). 결과 SHA `675dfa6fa3126da0ba74b5a4b4c4222afff4d950297703f3314788f9135a30db` 불변. 독립 pandas 29,671건×3필드 불일치 0.
- EdNet 실제 2,048명×9필드 SQL/pandas 대조, 동일 파일 반복 집계, 감사 시각·전송량만 다른 캐시 재실행 일치. 고정 원본/선정 목록/색인/콘텐츠 ZIP을 검증한다. [staging 실제 실행 기록](../reports/ednet_verification.json)은 배포 검증과 구분했다.
- 14일 경계·배정 중복/군 오염·이벤트 키·지연·관찰 성숙·SRM·가드레일을 합성 입력으로 확인. 실제 서비스 실험 0건.
- 기존 전체 사용자 경로·12개 데이터 계약 변형·4개 UI 회귀·23개 범위의 분자/분모·PC/모바일을 재확인했다. 추가 화면의 3개 이벤트 정의와 18개 가상 모집 조합, HTTP 실패와 재시도, 해시를 바꿔도 의미 오류 차단을 확인했다.
- axe: 기존 9상태×3폭(1440/390/320)의 탐지 위반 0. 각 상태에 자동 판정 불완전 항목이 남아 있어 완전한 접근성 인증은 아니다. EdNet 3폭과 실측 페이지의 준비/수행/완료 상태도 별도 검사했다.
- 실측 도구는 개발자 합성 조작으로 누락·검토·일시중지·탭 숨김·JSON 내보내기/검증·오류 복구를 확인했다. 합성 파일은 임시 디렉터리에서 삭제하고 실제 사람의 시간으로 기록하지 않았다.
- 브라우저는 Playwright 1.56 / Chromium 141. 당시 Safari·Firefox·실제 모바일 기기·스크린 리더 사용자 검토는 미실시였으며, 이후 Firefox/WebKit CI 보완은 문서 맨 위의 최신 기록을 따른다.


최신 보완: 2026-10-30 (Asia/Seoul). 초기 검증 기록은 아래 날짜와 구분한다. 실행 결과를 근거로 작성. 로컬 성공과 배포 성공을 구분한다.

## UI 개편 검증

사용자 승인한 [UI 재조사](research/ui-audit-2026-10-29.md)를 기준으로 검토 목록/상세, 독립 작업 화면, URL 상태, 같은 범위의 분석, 운영 기록을 구현했다. 아래는 개편 버전의 기록이며 이전 섹션은 최초 분석·개발 이력이다.

- `pytest`: **29 passed**. 기존 24개 + 운영 근거 묶음 5개. 잘못된 count·snapshot·중복 issue·benchmark hash 차단, 실제 SQL 20개 위치 확인. 6개 차원 규칙은 dimensions.sql로 연결.
- [업무 흐름 검사](../reports/workbench-local.json): 첫 검토 진입, 영향·이력 상세, URL 새로고침/뒤로가기, 잘못된 URL 기본값, 모바일 목록 복귀 초점.
- [브라우저 검사](../reports/browser-local.json): PC 전체 22개 개설기의 활성·재방문·콘텐츠 차이·활동일 차트/표, 20개 SQL 링크, 생성 5단계, 표본 6시나리오. report/operations 각각의 HTTP 실패→재시도 복구.
- [변형 응답 검사](../reports/report-contract.json): 숫자·분수·출처·BLOCK·미검증·빈 개설기·null 구간·오래된 이슈·잘못된 SQL·스냅샷·중복 이슈·실행 해시. BLOCK은 공개 보류, 미검증은 상태 미확인으로 구분.
- 접근성: 1440/390/320px × 기본 검토/상세 3탭/분석/실행/계획/실습/오류 = 27개 조합. 자동 위반 0. [기록](../reports/accessibility-local.json). 브랜드 장식·화살표 등 color-contrast 자동 판정 불완전은 남김. 고정색 계산과 위치 측정은 [ui-redesign.json](../reports/ui-redesign.json)에 별도 기록.
- 별도 리뷰 4개 회귀: 실제 report 바이트 해시 결합, 모바일 브라우저 뒤로가기 초점, 개설기 설명의 전체 분모 분리, 0분모 비교 불가. [수정 전](../reports/review-regressions-before.json) 모두 실패 → [수정 후](../reports/review-regressions-local.json) 모두 통과. [리뷰와 판단](../reports/ui-review.json).
- 개편은 분석 report의 내용·해시를 바꾸지 않는다. 화면용 operations.json은 기존 issues/benchmark/SQL에서 생성하고 build/verify로 대조한다.
- 공개 소스 `a9ba161d4c3a50548486ec60b72dd9d5f798d3cd`, Render `dep-dbhf79dckfvc73fanc90` live. HTML/JS/CSS/데이터 8개가 HTTP 200이며 로컬 바이트와 일치한다. [배포 근거](../reports/ui-deployment.json).
- 공개 주소에서도 [주요 흐름](../reports/browser-deployed.json), [검토 작업](../reports/workbench-deployed.json), [리뷰 회귀 4개](../reports/review-regressions-deployed.json), 변형 응답 12개, [접근성 27개 조합](../reports/accessibility-deployed.json)을 재실행해 통과했다. PC·모바일 공개 스크린샷을 직접 확인했다. 접근성 자동 판정 불완전 항목과 미수행 범위는 위와 같다.
- 공개 환경 첫 키보드 검사에서 로딩 중 숨겨진 탭을 조작해 실패했다. 응답 0.8초 지연으로 재현: 준비 전 focus 없음, 준비 후 tab-impact. [원인 기록](../reports/browser-loading-diagnosis.json). 테스트에 화면 준비 조건을 추가하고 로컬·공개 전체 흐름을 재검사했다. 제품 결함으로 집계하지 않았다.
- 개편 소스의 [원격 품질 CI 40834758383](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40834758383): pytest·build·verify 모두 success. [단계 기록](../reports/ui-ci.json). 원본 분석 SQL/Python은 변경하지 않아 전체 원본 분석은 이번 UI 변경에서 다시 실행하지 않았다. 기존 독립 재현 근거는 아래에 보존한다.
- 이후 검증 기록·스크린샷·테스트 준비 조건의 커밋은 배포 web 파일과 분석 수치를 바꾸지 않는다.

## 초기 분석·코드 검증

- Python 3.12.14 / DuckDB 1.4.3. `python -m pytest -q`: **24 passed**.
- 손계산 기준: 등록 6명 중 적격 1/2/6, D0/6/7/13/14 경계, 양수 클릭, 동일 행, 고아 키, null, 탈퇴 이후 활동.
- 생성 기준: 적격 12명 / 첫 주 10명 / 다음 주 6명, 원천 장부 32행. 중복이 누락을 가리는 사례, 역순 수신과 잘못된 발생 순서를 구분.
- 다운로드: SHA256 불일치, archive 경로 탈출, 기존 다른 파일 덮어쓰기 방지 테스트.
- 회귀: 차원 null/없는 개설기/잘못된 기간 6개, 독립 군집 1명, 상태 해결 이력과 동일 실행 중복 방지.
- 독립 pandas: SQL/production helper를 import하지 않는 `scripts/crosscheck.py`로 **29,671 수강 건의 3개 활동 지표**를 대조, 불일치 **0**. [기계 결과](../reports/crosscheck.json).
- 최종 결과 3회 재생성: JSON 해시 동일. 실제 실행 시간/포함 범위/환경은 [benchmark.json](../reports/benchmark.json). 이 전체 분석의 사람 수작업 기준선은 없다. 별도 3개 규칙 기록·대조 실측은 아래 후속 기록과 구분한다.
- 전체 원본의 품질 규칙 20개. BLOCK 유형 14개 모두 0, REVIEW 유형 중 5개 비영. REVIEW를 통과로 바꾸거나 실제 오류라고 단정하지 않음.

## 브라우저

Playwright 1.56 / Chromium 141, 실제 HTTP 서버에서 확인.

- 1440×1000, 390×844: 전체·개설기 필터, 분모·분자·비율, 22개 개설기의 수치와 차트 라벨, 빈 검색, 5단계 생성 실습, 가상 표본 계산.
- 키보드: 본문 바로가기와 focus 이동. 표 스크롤 영역의 키보드 접근 보완.
- HTTP 500 로드 실패: 결과 숨김→오류 표시→재시도 회복.
- 변형 응답: 문자열 비율, 분수 불일치, 출처 뒤바뀜, BLOCK, 빈 개설기 차단. 사용 가능한 데이터의 null CI는 전체 실패 없이 '비교 불가'.
- 페이지 JS 예외 없음. 문서 폭 기준 가로 넘침 없음. 넓은 표는 명시된 가로 스크롤 영역.
- 스크린샷: `reports/screenshots/`의 PC·모바일 첫 화면. 최종 렌더링을 시각적으로 확인.

[로컬 흐름 결과](../reports/browser-local.json) · [보고서 계약 결과](../reports/report-contract.json).

## 접근성

axe-core 4.11, WCAG 2 A/AA·2.1 AA·2.2 AA 자동 규칙, 1440/390/320px.

수정 전: 하단 링크 target-size, 모바일 표 scrollable-region-focusable 위반. [수정 전 결과](../reports/accessibility-before.json).
수정 후: 자동 탐지 위반 0. 모바일의 일부 color-contrast 항목은 자동 판정 불완전으로 남아 있어 별도 명시한다. [최종 로컬 결과](../reports/accessibility-local.json).

실제 스크린 리더 사용자 테스트, Apple Safari, 다양한 물리 기기, 전체 WCAG 적합성 인증은 수행하지 않았다. Firefox와 WebKit의 이후 CI 검증은 문서 맨 위의 최신 기록을 따른다. 자동 검사 0건은 완전한 접근성 보장이 아니다.

## 초기 배포·원격 CI 이력

- 공개 URL: https://learning-journey-lab.onrender.com
- Render 정적 사이트, 사용자 선택 `my2 workspace`. 최초 소스 커밋 `f3c5090499a67b6f267de4cadae4084dc2c240d7`, 배포 `dep-dbhd5mo8v5cc7385iqug`, 상태 live 확인.
- HTML/CSS/JS/report/release 6개 경로 HTTP 200. 공개 report SHA256이 로컬과 정확히 일치. [HTTP 근거](../reports/deployment.json).
- 실제 공개 주소의 PC/모바일 사용자 흐름을 확인했다. 위의 브라우저·접근성 결과 파일은 현재 개편 버전의 재검증 결과로 갱신했다. 환경 프록시의 기존 CA 공개키만 신뢰하도록 Chromium QA를 설정했으며 전체 TLS 오류를 무시하는 옵션은 사용하지 않았다. Python HTTP 검증도 시스템 CA 체인을 검증했다.
- 첫 원격 CI [40820849573](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40820849573): 테스트·빌드·증거 일관성 단계 success.
- 검증 소스 `9b863b5950ee630b84a95d9b935f4d6a610cdf91`: [품질 CI 40821666750](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40821666750), [전체 원본 재현 40821666614](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40821666614) 모두 success. 별도 GitHub runner에서 공식 다운로드→전체 분석→독립 pandas 대조→빌드→수치·해시 일치 검증→근거 artifact 업로드까지 통과. [기계 기록](../reports/ci.json).
- 해당 소스의 후속 Render 배포 `dep-dbhd9knavr4c739mpbo0`도 live. 후속 문서·검증 기록 커밋은 분석 결과와 web 파일을 바꾸지 않는다. 완료 시점의 최종 커밋은 저장소 main과 별도 전달 기록에서 확인.
- 전체 원본 재현은 수동 또는 SQL/분석/manifest/workflow 변경 시 실행. 주간 자동화는 소규모 테스트·정적 증거 검증이며, 원본 데이터가 실시간으로 갱신되는 서비스는 아니다.

## 코드 리뷰

별도 리뷰어가 24개 회귀 테스트 추가 전 상태를 검토하고 당시 17개 통과를 확인했다. 주요 발견은 차원 계약 누락, JSON 의미 검증 부족. null 구간·BLOCK 수용·단일 군집도 범위 내 결함으로 처리했다. 수정마다 회귀 사례와 전체 테스트를 다시 실행했다. 리뷰어는 실제 Chromium을 실행하지 못해 UI는 Node로 재현했으며, 최종 브라우저 검증은 주 작업 환경에서 별도로 수행했다. README/CI/배포는 당시 작업 중이어서 리뷰어의 검토 범위 밖이었다. 미수행 검토를 완료로 표시하지 않는다.

## 이번 보완의 독립 리뷰와 수정

새 리뷰어가 109개 테스트, 실제 EdNet 전체 재계산과 집계 바이트 일치, OULAD 보존 해시를 독립 확인했다. 현재 분석값 오류는 없었으나 잘못된 그룹 이름과 음수 인원이 보고서 계약을 통과하는 빈틈을 발견했다. 사용자에게 잘못된 근거를 표시할 수 있어 수정 대상으로 판단했다. 5개 Python 실패 사례와 실제 브라우저 실패를 먼저 확인하고, Python·JS 양쪽에서 이벤트 정의/그룹 순서/인원 정수·범위를 검사하도록 수정했다. 해당 회귀와 전체 테스트를 다시 실행했다. 라이선스 법률 해석·실제 사용자 참여·배포는 독립 리뷰어가 검증한 범위가 아니며 별도 근거와 미완료 표시를 따른다.

## 이번 보완의 원격 재현·공개 배포

소스 `a3a8ba78e5d6e0a679f6344c4fe291ea1f96c641` 기준:

- [품질 CI 40918238570](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40918238570): 114개 테스트·build·verify 성공.
- [OULAD 전체 재현 40918238321](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40918238321): 공식 다운로드→분석→독립 대조→정적 검증 성공.
- [EdNet 추가 실제 자료 재현 40918238369](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40918238369): 빈 runner에서 공식 파일 새 다운로드→고정 해시 검사→전체 분석 2회→두 결과 및 저장소 집계 바이트 일치→실험 입력 검사·빌드·검증 성공. [단계별 기계 기록](../reports/extension-ci.json).
- Render `dep-dbhnqg2vcj2c738demkg` live, 소스 SHA 일치. 공개 18개 자산 모두 HTTP 200 및 로컬 SHA 일치. [배포 기록](../reports/extension-deployment.json).
- 공개 URL에서 기존 PC/모바일 경로, 모든 범위 분자/분모, 보조 자료·모집 계산·실측 도구의 개발자 합성 경로와 오류 복구를 다시 실행했다. [기존 흐름](../reports/browser-deployed-extension.json), [작업 동선](../reports/workbench-deployed-extension.json), [분모](../reports/reading-deployed-extension.json), [추가 화면](../reports/extension-browser-deployed-extension.json), [회귀](../reports/review-regressions-deployed-extension.json), [axe 27상태](../reports/accessibility-deployed-extension.json).
- 공개 화면 PC·모바일 캡처를 실제 렌더링과 함께 확인했다. [화면 색인](portfolio-evidence.md). 공개 실측 페이지 검사는 자동 조작·합성 내보내기이며 실제 참여자 결과가 아니다.
- 후속 문서·캡처·검증 스크립트 커밋은 분석 및 web 자산을 바꾸지 않는다. 최종 후속 커밋의 품질 CI와 Render live는 완료 전달 시 별도 재확인한다. 소스 검증과 문서 후속을 혼동하지 않는다.

## 지원자 테스트 통합 (2026-10-30 KST)

사용자 커밋 [4996ef6](https://github.com/sokldjs554/learning-journey-lab/commit/4996ef674df442ccfe40e590fe94a024a6a1da3b)의 테스트를 수정 없이 통합했다. 실습 브랜치 [CI 41011751113](https://github.com/sokldjs554/learning-journey-lab/actions/runs/41011751113) 성공. 최신 코드 통합에서 `python -m pytest tests/test_user_repeat.py -q`: 1 passed, 전체 115 passed. 테스트는 동일 행 3개 중 초과 2개를 검사한다. 원본 분석·web 자산은 바꾸지 않았다. Codex가 처음 로컬 명령을 기존 main 디렉터리에서 실행해 파일을 찾지 못했고, 통합 작업 트리로 경로를 바로잡아 검증했다. 사용자의 코드 오류가 아니었다.

## 지원자 실측 원본 검증 (2026-10-30 KST)

업로드된 human_self_reported JSON을 `scripts/import_practice.py`로 검사했다. 2회 연습·6회 ABBAAB 순서·스냅샷·원문 기대값·누락/오류/대조·구간 연속성/합계·벽시계 허용 오차를 통과했다. 6회 모두 유효. 원본 해시와 상대 구간·결과는 `reports/human-comparison.json`, 해석은 `docs/human-comparison-results.md`에 있다. 원본 전체와 정확한 시각·원문 장치 식별 문자열은 공개하지 않았다. 중앙값은 statistics.median 및 정렬 후 가운데 값으로 각각 대조했다. 사용자 수행과 파일 일관성 검증은 주의 집중·생산성 개선의 인증이 아니다.

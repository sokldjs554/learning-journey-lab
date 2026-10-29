# 검증 기록

확인일: 2026-10-29 (Asia/Seoul). 실행 결과를 근거로 작성. 로컬 성공과 배포 성공을 구분한다.

## UI 개편 검증

사용자 승인한 [UI 재조사](research/ui-audit-2026-10-29.md)를 기준으로 검토 목록/상세, 독립 작업 화면, URL 상태, 같은 범위의 분석, 운영 기록을 구현했다. 아래는 개편 버전의 기록이며 이전 섹션은 최초 분석·개발 이력이다.

- `pytest`: **29 passed**. 기존 24개 + 운영 근거 묶음 5개. 잘못된 count·snapshot·중복 issue·benchmark hash 차단, 실제 SQL 20개 위치 확인. 6개 차원 규칙은 dimensions.sql로 연결.
- [업무 흐름 검사](../reports/workbench-local.json): 첫 검토 진입, 영향·이력 상세, URL 새로고침/뒤로가기, 잘못된 URL 기본값, 모바일 목록 복귀 초점.
- [브라우저 검사](../reports/browser-local.json): PC 전체 22개 개설기의 활성·재방문·콘텐츠 차이·활동일 차트/표, 20개 SQL 링크, 생성 5단계, 표본 6시나리오. report/operations 각각의 HTTP 실패→재시도 복구.
- [변형 응답 검사](../reports/report-contract.json): 숫자·분수·출처·BLOCK·미검증·빈 개설기·null 구간·오래된 이슈·잘못된 SQL·스냅샷·중복 이슈·실행 해시. BLOCK은 공개 보류, 미검증은 상태 미확인으로 구분.
- 접근성: 1440/390/320px × 기본 검토/상세 3탭/분석/실행/계획/실습/오류 = 27개 조합. 자동 위반 0. [기록](../reports/accessibility-local.json). 브랜드 장식·화살표 등 color-contrast 자동 판정 불완전은 남김. 고정색 계산과 위치 측정은 [ui-redesign.json](../reports/ui-redesign.json)에 별도 기록.
- 별도 리뷰 4개 회귀: 실제 report 바이트 해시 결합, 모바일 브라우저 뒤로가기 초점, 개설기 설명의 전체 분모 분리, 0분모 비교 불가. [수정 전](../reports/review-regressions-before.json) 모두 실패 → [수정 후](../reports/review-regressions-local.json) 모두 통과. [리뷰와 판단](../reports/ui-review.json).
- 개편은 분석 report의 내용·해시를 바꾸지 않는다. 화면용 operations.json은 기존 issues/benchmark/SQL에서 생성하고 build/verify로 대조한다.
- 로컬 검증 후 공개 배포에서도 같은 테스트와 파일 일치를 재확인한다. 배포 완료 기록은 후속 항목에 추가한다.

## 초기 분석·코드 검증

- Python 3.12.14 / DuckDB 1.4.3. `python -m pytest -q`: **24 passed**.
- 손계산 기준: 등록 6명 중 적격 1/2/6, D0/6/7/13/14 경계, 양수 클릭, 동일 행, 고아 키, null, 탈퇴 이후 활동.
- 생성 기준: 적격 12명 / 첫 주 10명 / 다음 주 6명, 원천 장부 32행. 중복이 누락을 가리는 사례, 역순 수신과 잘못된 발생 순서를 구분.
- 다운로드: SHA256 불일치, archive 경로 탈출, 기존 다른 파일 덮어쓰기 방지 테스트.
- 회귀: 차원 null/없는 개설기/잘못된 기간 6개, 독립 군집 1명, 상태 해결 이력과 동일 실행 중복 방지.
- 독립 pandas: SQL/production helper를 import하지 않는 `scripts/crosscheck.py`로 **29,671 수강 건의 3개 활동 지표**를 대조, 불일치 **0**. [기계 결과](../reports/crosscheck.json).
- 최종 결과 3회 재생성: JSON 해시 동일. 실제 실행 시간/포함 범위/환경은 [benchmark.json](../reports/benchmark.json). 수작업 기준선 없음.
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

실제 스크린 리더 사용자 테스트, Safari/Firefox, 다양한 기기, 전체 WCAG 적합성 인증은 수행하지 않았다. 자동 검사 0건은 완전한 접근성 보장이 아니다.

## 배포·원격 CI

- 공개 URL: https://learning-journey-lab.onrender.com
- Render 정적 사이트, 사용자 선택 `my2 workspace`. 최초 소스 커밋 `f3c5090499a67b6f267de4cadae4084dc2c240d7`, 배포 `dep-dbhd5mo8v5cc7385iqug`, 상태 live 확인.
- HTML/CSS/JS/report/release 6개 경로 HTTP 200. 공개 report SHA256이 로컬과 정확히 일치. [HTTP 근거](../reports/deployment.json).
- 실제 공개 주소의 PC/모바일 사용자 흐름을 [브라우저 결과](../reports/browser-deployed.json)와 [접근성 결과](../reports/accessibility-deployed.json)에 기록. 환경 프록시의 기존 CA 공개키만 신뢰하도록 Chromium QA를 설정했으며 전체 TLS 오류를 무시하는 옵션은 사용하지 않았다. Python HTTP 검증도 시스템 CA 체인을 검증했다.
- 첫 원격 CI [40820849573](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40820849573): 테스트·빌드·증거 일관성 단계 success.
- 검증 소스 `9b863b5950ee630b84a95d9b935f4d6a610cdf91`: [품질 CI 40821666750](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40821666750), [전체 원본 재현 40821666614](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40821666614) 모두 success. 별도 GitHub runner에서 공식 다운로드→전체 분석→독립 pandas 대조→빌드→수치·해시 일치 검증→근거 artifact 업로드까지 통과. [기계 기록](../reports/ci.json).
- 해당 소스의 후속 Render 배포 `dep-dbhd9knavr4c739mpbo0`도 live. 후속 문서·검증 기록 커밋은 분석 결과와 web 파일을 바꾸지 않는다. 완료 시점의 최종 커밋은 저장소 main과 별도 전달 기록에서 확인.
- 전체 원본 재현은 수동 또는 SQL/분석/manifest/workflow 변경 시 실행. 주간 자동화는 소규모 테스트·정적 증거 검증이며, 원본 데이터가 실시간으로 갱신되는 서비스는 아니다.

## 코드 리뷰

별도 리뷰어가 24개 회귀 테스트 추가 전 상태를 검토하고 당시 17개 통과를 확인했다. 주요 발견은 차원 계약 누락, JSON 의미 검증 부족. null 구간·BLOCK 수용·단일 군집도 범위 내 결함으로 처리했다. 수정마다 회귀 사례와 전체 테스트를 다시 실행했다. 리뷰어는 실제 Chromium을 실행하지 못해 UI는 Node로 재현했으며, 최종 브라우저 검증은 주 작업 환경에서 별도로 수행했다. README/CI/배포는 당시 작업 중이어서 리뷰어의 검토 범위 밖이었다. 미수행 검토를 완료로 표시하지 않는다.

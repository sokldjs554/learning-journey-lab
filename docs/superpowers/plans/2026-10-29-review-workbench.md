# Review Workbench Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; final fresh reviewer.

**Goal:** 검토 항목에서 근거·영향·판단까지 이어지는 실제 분석 업무 흐름.
**Architecture:** 분석 report는 보존. build가 이슈·벤치마크·SQL 위치를 검증해 operations.json으로 묶고, 정적 웹이 검토/분석/실행/계획/생성 실습의 독립 화면을 URL 상태로 제공.
**Tech Stack:** Python stdlib build, 기존 vanilla JS/CSS, Playwright, axe, pytest.
**Spec:** ../../research/ui-audit-2026-10-29.md (사용자가 조사 결과대로 수정 승인)

## Global Constraints
- 공개/생성 완전 분리. 가짜 실행·담당자·협업·실험 성과 금지.
- 원본 분석 수치와 해시 보존. 실제 snapshot hash를 날짜로 해석 금지.
- 첫 화면에 목적·출처·현재 판단·검토 진입점. PC 1440×900, 모바일 390×844.
- 상태는 색+문자. 실제 가능한 링크·필터·다운로드만 제공.
- 기존 저장소와 선택한 Render 서비스만 사용. 공개 수정 배포는 사용자 승인 범위.

## Review Focus
- URL의 잘못된 view/rule/cohort/tab/stage 및 뒤로가기·새로고침
- 선택 개설기 근거에 전체 결과를 혼합하는 오해
- 0건/검색 없음/null 구간/HTTP 실패/서로 다른 스냅샷 결합
- SQL 차원 6개 매핑과 이슈 history의 의미
- 모바일 목록/상세 복귀, 키보드 초점, 긴 SQL·표 넘침

### Task 1: Operations evidence contract
Files: scripts/build.py, scripts/verify.py, tests/test_build.py, web/data/operations.json.
Interface: build_operations(root, report) -> {schema_version, report_sha256, snapshot_id, rules, sql_files, benchmark}. rules contain actual issue history plus sql_file/sql_line.
- [x] Write failing tests: all20 mapping, 6dimension sources, stale count/hash/snapshot and duplicate issue rejection.
- [x] Implement deterministic export; include operations hash in release; verify byte-for-byte source derivation.
- [x] Run pytest; commit.

### Task 2: Review workspace and coherent navigation
Files: web/index.html, web/style.css, web/app.js, web/catalog.js, web/report-contract.js, tests/browser_check.py.
Interface: URL query view=review|analysis|runs|plan|lab, rule=<known rule>, tab=evidence|impact|decision, cohort=all|module.term, stage=<known stage>, detail=1 (mobile opened detail).
- [x] Browser tests fail on old UI: compact task entry, rule evidence, exact SQL link, issue history, URL restore/back, scoped content comparison, 22cohorts, empty state, generated stages.
- [x] Build compact header/navigation and review list+detail; mobile list/detail with keyboard-safe return.
- [x] Build analysis scoped view and explicit separate all-dataset validation; runs and plans display real records only; retain isolated fault lab.
- [x] Validate operations provenance/counts and report; retry state. Browser contract mutations.
- [x] Run browser and all pytest; commit.

### Task 3: Visual verification, review, deployment
Files: tests/accessibility_check.py, reports/*, README.md, docs/verification.md, docs/learning-log.md.
- [x] Inspect desktop/mobile screenshots; axe every view 1440/390/320, keyboard/detail/back/empty/error.
- [x] Fresh whole-change review, classify/fix material findings with regression cases.
- [x] Update screenshots and README demo guide, record actual changes/limits.
- [x] Run final checks, publish, verify deployed UI/hash and CI, record completion evidence.

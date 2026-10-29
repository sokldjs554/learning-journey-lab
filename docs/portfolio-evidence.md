# 실제 화면과 근거 모음

2026-10-30 KST 보완. 제출용 포트폴리오 문장이 아니라 사실 확인용 색인이다. 공개 화면은 정적 집계 자료이며, 실시간 분석 서버나 실제 CLASS101 계정 화면이 아니다.

## 공개 배포 화면

아래 `deployed-extension-*` 파일은 공개 Render URL을 Chromium으로 직접 열어 캡처한다. 브라우저·배포 결과는 [최종 검증 기록](verification.md)의 이번 보완 항목과 함께 확인한다.

| 파일 | 보여 주는 내용 |
|---|---|
| [PC 첫 화면](../reports/screenshots/deployed-extension-desktop-cover.png) | 활동일 사용·클릭 기준 보류 판단, 반복 행과 검토 목록 |
| [모바일 첫 화면](../reports/screenshots/deployed-extension-mobile-cover.png) | 같은 목적과 판단을 좁은 화면에서 확인 |
| [PC 처리 정책](../reports/screenshots/deployed-extension-desktop-impact-cover.png) | 첫날 10클릭 기준과 369 수강 건 분류 변경 |
| [모바일 처리 정책](../reports/screenshots/deployed-extension-mobile-impact-cover.png) | 처리 영향의 상세 설명과 복귀 동선 |
| [전체 재방문 근거](../reports/screenshots/deployed-extension-analysis-overall.png) | 분자 20,303·분모 23,522, 활동일 비교와 9개 반대 방향 |
| [BBB 2014J 반대 근거](../reports/screenshots/deployed-extension-analysis-counter.png) | 콘텐츠 접촉 −6.6%p와 범위 필터; 활동일 비교와 구분 |
| [EdNet PC](../reports/screenshots/deployed-extension-external-1440.png) | 실제 보조 자료의 이벤트 정의·결제 관측·관측 종료 한계 |
| [EdNet 모바일](../reports/screenshots/deployed-extension-external-390.png) | 같은 근거의 모바일 구성 |
| [검증 계획](../reports/screenshots/deployed-extension-plan-1440.png) | 실제 참여자 0, 합성 입력 검사와 가상 모집 기간 |

## 계산과 검증 원본

- 기존 OULAD: [집계](../reports/report.json), [SQL 품질 규칙](../sql/quality.sql), [독립 pandas 대조](../reports/crosscheck.json), [지표 정의](data-contract.md).
- 추가 EdNet: [분석·분모·제외·한계](ednet-analysis.md), [실제 집계](../reports/ednet_report.json), [추출 기준 해시](../data/ednet_snapshot.json), [계산 SQL](../sql/ednet.sql), [실제 반복 실행 기록](../reports/ednet_verification.json).
- 실제 데이터 조사: [선택·제외 근거와 라이선스](data-sources.md), [출처 점검 JSON](../reports/external_source_review.json), [데이터 권리 구분](../DATA_LICENSES.md).
- 실험: [계획](experiment-plan.md), [구현한 입력 검사](experiment-readiness.md), [합성 결과·18개 가상 시나리오](../reports/experiment-readiness.json). 실제 리텐션 실험 성과가 아니다.
- 자동화: [기존 기계 실행 시간](../reports/benchmark.json), [동일 작업 실측 절차](human-comparison-protocol.md). 사람의 제출 기록과 절감률은 아직 없다.
- 사용성: [실제 참여자용 과제](novice-usability-protocol.md). 미실시이며 개발자 자동 조작을 피드백으로 바꾸지 않는다.
- 지원자: [완료한 실습·미완료 코드 작업](participation.md), [직접 실행한 Actions](https://github.com/sokldjs554/learning-journey-lab/actions/runs/40879343617).
- 주장 범위: [주장과 증거](evidence-map.md). 어떤 분석이 구현되어 있다는 사실과 지원자가 독립적으로 수행했다는 경험을 구분한다.

## 직접 코드 작성 안내

`practice/repeat-rule`의 [새 테스트 파일](https://github.com/sokldjs554/learning-journey-lab/new/practice/repeat-rule?filename=tests/test_user_repeat.py)을 연다. Codex가 제공한 아래 예제를 직접 입력하고, **이 브랜치에 커밋**한다. 이미 있는 테스트 fixture에는 같은 활동 행 2개가 있으므로 1개를 더 넣으면 총 3개, 서로 다른 행 1개, 초과 2개다.

```python
from journey.pipeline import quality

def test_three_identical_rows_count_two_excess(db):
    db.execute("INSERT INTO studentVle VALUES ('AAA','2013J',1,10,0,5)")
    checks = {row['rule_id']: row['count'] for row in quality(db)}
    assert checks['event_exact_repeat'] == 2
```

커밋 후 Actions의 **Quality and static evidence**에서 해당 브랜치 결과를 확인한다. 설치된 로컬 환경이 있다면 `python -m pytest tests/test_user_repeat.py -q`로 1 passed를 확인할 수 있다. 환경이 없으면 설치하지 않고 Actions를 사용한다. 실패하면 오류 문구와 커밋 주소를 전달한다. Codex가 결과를 확인하고 반영하기 전에는 직접 작성 완료로 기록하지 않는다. 예제 설계는 Codex 도움을 받은 작업이며 독립 설계로 표현하지 않는다.

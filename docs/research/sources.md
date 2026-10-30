# 조사 기록과 범위 선택

확인일: 2026-10-29, Asia/Seoul. 웹 검색 결과만으로 채택하지 않고 아래 원문·README·스키마를 직접 읽었다. 링크의 내용은 이후 바뀔 수 있다. 타사의 성과나 README 주장에 대한 독립 감사는 아니다.

## 채용 공고

[CLASS101 채용연계형 Data Analyst](https://jobs.class101.net/job_posting/Yhpgrtd3)의 팀 소개부터 리더 메시지, 전형·근무 형태까지 전문을 확인했다. 열람 당시 채용 시 마감으로 표시되고 지원 버튼이 존재했다. 채용 담당자에게 실제 접수 가능 여부를 확인한 것은 아니다.

제품전략팀의 DA이며 AI Engineer가 아니다. 초기 업무의 중심은 로그·정합성 관리이고, 운영 개선을 거쳐 분석과 실험으로 확장한다. SQL·통계·개발 이해와 함께 집요한 원인 탐색, 생산성 개선, 실패를 학습으로 연결하는 태도를 강조한다. 리더가 제시한 문제에는 구독 유지의 선행 행동, 콘텐츠의 증분 효과와 정산 정책의 수익성 판단이 포함된다. 방법론 이름은 수단의 예시이므로 기술 개수를 채우는 목표로 삼지 않았다.

### 직무와 구현 연결

| 공고의 방향 | 프로젝트 증거 | 범위 한계 |
|---|---|---|
| 로그 품질·정합성 | `sql/quality.sql`, `reports/issues.json`, 생성 실습 | 실제 운영 원천 로그에 접속하지 않음 |
| 반복 업무 개선 | 해시 검증→SQL→통계→JSON→화면, 이슈 상태 추적, CI | 전체 분석의 사람 수작업 기준선은 미측정. 별도 3개 규칙 검토표는 1명·각 3회 [실측](../human-comparison-results.md) |
| 제품 성장 문제 해결 | 첫 주 신호의 민감도, 개설기/시점 반례, 우선순위와 실험 설계 | 실제 실험·매출 성과 없음 |
| SQL | 복합키, JOIN, 조건부 집계, distinct 활동일, 품질 규칙 | 외부 웨어하우스 운영 경험 주장 불가 |
| 통계 | 군집 부트스트랩, 시간 순서 재확인, 검정력 시나리오 | 관측 교란 제거 불가 |
| 개발 이해 | 데이터 계약, 고정 의존성, 배포, 브라우저 오류 처리, 재현 테스트 | 실시간 백엔드·실서비스 계측 구현 아님 |
| 실패·학습·오너십 | `docs/learning-log.md`의 발견→수정→재검증 | 에이전트 작업과 지원자의 경험을 구분 |

## 서비스 공개 자료

- [플러스 구독 안내](https://help.class101.tv/classmate/class101-plus-subscription-guide): 구독 대상 클래스의 폭넓은 이용, 퀴즈·연속 수강 목표, 일부 상품 제외, 크리에이터 계약에 따른 제공 변경을 확인했다.
- [수강 방법](https://help.class101.tv/classmate/how-to-take-class): PC와 모바일의 내 클래스 진입 경로와 상품별 이용 권한 차이를 확인했다.
- [마스터 개별 구매 안내](https://help.class101.tv/classmate/class101-master-purchase-guide): 개별 구매와 구독의 구분, 같은 클래스라도 제공 범위가 다를 수 있음을 확인했다.
- [그룹 구독](https://help.class101.tv/classmate/class101-group-plan): 결제 주체와 초대된 학습 계정이 나뉨을 확인했다.
- [한국어 구독 안내](https://docs.channel.io/classmate/ko/articles/CLASS101-%EA%B5%AC%EB%8F%85-%EC%84%9C%EB%B9%84%EC%8A%A4%EB%9E%80-96e00610): 검색 시 한국어 문구와 직접 열린 도움말의 자동 번역본에서 클래스 수가 달랐다. 가격·콘텐츠 수를 프로젝트 근거 숫자로 고정하지 않았다. 일부 직접 열린 도움말에는 자동 번역 고지가 있었다.

**제품적 함의(추론):** 활동 계정의 재방문과 결제 계정의 갱신은 다르다. 콘텐츠 권한 종료도 무관심에 의한 이탈과 구분해야 한다. 이미 존재하는 꾸준한 학습 기능을 새로 발명한 것처럼 제안하면 안 된다. 따라서 '다음 학습 재개 동선'은 기존 경험을 조사한 뒤 개선안을 정하는 실험 후보로만 제시했다. 로그인 후 유료 수강 경험이나 사용자의 실제 피드백을 관찰한 것은 아니다.

## 제품 문제 대안 비교

| 문제 후보 | 공고와의 연결 | 확보한 자료로 가능한 판단 | 선택 |
|---|---|---|---|
| 구독 갱신·해지 원인 | 제품 성장과 구독 전략에 직접 연결 | 결제·권한·갱신 이력이 없어 공개 학습 자료로 답할 수 없음 | 후속 내부 데이터 과제 |
| 콘텐츠별 증분 가치·정산 정책 | 콘텐츠 전략·수익성 판단 | 노출 배정·비용·정산·매출이 없어 효과나 수익성 추정 불가 | 미채택 |
| 첫 주 학습 신호의 신뢰성과 다음 주 활동 | 로그 운영→자동화→제품 가설 흐름 | 관계형 키·일별 활동·등록 시점으로 지표 민감도와 관찰적 관계 검증 가능 | 채택, 구독 성과와 분리 |

처음 제시된 방향에서 **첫 재생의 세부 단계 이탈**을 분석하는 부분은 관측 불가능해 제외했다. 실제 확보 가능한 단위인 개강 후 첫 주 활동으로 좁히고, 원천 순서·누락 복구는 별도 생성 실습으로 옮겼다.

## 초기 데이터 대안 비교와 이후 변경

| 후보 | 사건 단위·기간 | 라이선스·접근 | 선택 판단 |
|---|---|---|---|
| **OULAD** | 학습자×자료×상대 일자의 클릭 집계, 2013/2014 | 공식 UCI ZIP 46,748,244 bytes 실제 다운로드, CC BY 4.0 | 선택: 관계형 정합성·등록 분모·시간 창 검증 가능. 순서/영상/갱신 없음 |
| **EdNet KT4 (초기 판단)** | 계정별 행위 시각, 문제·영상·결제/환불; README상 2018-08-27 이후 상세 행위 수집, 전체 사업 데이터 2017년부터 | 공식 README와 라이선스 직접 확인. CC BY-NC 4.0, KT4 압축 1.2GB/해제 6.4GB 표기. 다운로드 링크는 존재하나 전체 파일 미다운로드 | 더 풍부하지만 TOEIC 문제 풀이 중심, 타임스탬프 이동, 규모·비상업 조건을 고려해 초기에는 미채택. 이후 실제 보조 분석으로 추가(아래 변경 기록) |
| **HarvardX Person-Course AY2013** | 2012 가을~2013 여름 개인-강좌 요약 | [공식 Dataverse](https://doi.org/10.7910/DVN/26147)와 [MIT 발표](https://news.mit.edu/2014/mit-and-harvard-release-de-identified-learning-data-open-online-courses) 확인. 개별 파일 이용조건 전문은 이번 조사에서 확정하지 못함 | 첫 주 활동 날짜/원천 이벤트 복원 불가. 채택하지 않았고 다운로드·재배포하지 않음 |

**이후 변경(2026-10-30 KST):** EdNet KT4의 공식 사용자 파일 중 사전 해시로 고른 2,048명의 전체 제공 이력 854,678행을 확보해 별도 보조 분석을 완료했다. 전체 ZIP을 받았다는 뜻은 아니다. OULAD를 유지하고 두 자료의 분모를 합치지 않았다. 최신 선택·다운로드·라이선스 근거는 [데이터 조사](../data-sources.md), 결과는 [EdNet 분석](../ednet-analysis.md)을 따른다.

OULAD 근거:
- [현행 OU 데이터 설명](https://research.stem.open.ac.uk/ouanalyse/open-dataset-more/): 7개 테이블, 상대 날짜, B/J 분리 권고, 클릭 집계 정의.
- [현행 OU 데이터 소개](https://research.stem.open.ac.uk/ouanalyse/dataset/).
- [UCI 원본·라이선스](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset), DOI [10.24432/C5KK69](https://doi.org/10.24432/C5KK69).
- [원 논문](https://doi.org/10.1038/sdata.2017.171): Kuzilek, Hlosta, Zdrahal, 2017.
- EdNet [공식 README](https://github.com/riiid/ednet): 이벤트 구조와 이동된 타임스탬프 고지, [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

예전 `analyse.kmi.open.ac.uk/open_dataset` 링크는 조사 당시 OU 프로젝트 홈으로 리다이렉트됐다. 현행 스키마 페이지를 찾아 읽고 ZIP은 공식 UCI에서 확보했다. 이 접근 실패를 생성 데이터로 조용히 대체하지 않았다.

## 유사 포트폴리오

1. [Student Cohort Retention](https://github.com/zakiyyah-ai/student_cohort_retention): 실제 README에서 주별 활성·코호트 분모·Tableau 데모·실행법을 확인. 시각화만으로 끝내지 않기 위해 우리 프로젝트는 반복 행의 의미와 판단 민감도, 배포 보류 조건을 추가했다.
2. [OULAD Student Success Analytics Platform](https://github.com/LixinTu/OULAD-Student-Success-Analytics-Platform): ETL/시간 분할/모델/SHAP/오프라인 실험을 연결한 README를 읽었다. 데모 생성과 실제 자료 구분, 원명령 실행은 참고하되 이번 문제에 필요 없는 예측·클라우드 DB·모델링은 채택하지 않았다.
3. [Student risk early warning](https://github.com/Destinetheanalyst/student-risk-early-warning): 공개 검색에서 SQL→대시보드와 위험 예측이라는 방향을 확인. 전체 코드를 감사한 것은 아니며 상세 비교의 근거로 사용하지 않았다.

차별점은 '최초'나 '유일' 주장이 아니다. 조사한 예시들에 비춰 이번 작업의 중심을 **신뢰할 수 있는 판단의 조건, 반대 근거, 수정 불가능한 누락의 처리**로 좁힌 설계 선택이다.

## README 실제 참고 자료

| 읽은 README | 참고한 구성 | 그대로 가져오지 않은 부분 |
|---|---|---|
| [Great Expectations](https://github.com/fivetran/great_expectations) | 품질 규칙을 협업 가능한 기대 조건으로 설명; 결과 문서화 | 라이브러리 설치 자체를 성과로 삼지 않음 |
| [Evidently](https://github.com/evidentlyai/evidently) | 리포트와 pass/fail 조건 분리, 실제 화면, JSON/HTML 결과 접근 | ML/LLM 평가 기능은 이 문제에 불필요 |
| [dbt Jaffle Shop DuckDB](https://github.com/dbt-labs/jaffle_shop_duckdb) | 가상 데이터 고지, 빠른 로컬 실행, 테스트와 문서 경로 | 규모가 작은 프로젝트에 dbt 계층을 억지로 추가하지 않음 |
| [Student Cohort Retention](https://github.com/zakiyyah-ai/student_cohort_retention) | 데모 우선, 분석 분모/정의와 재현 경로 | 단순 주별 리텐션 대시보드로 끝내지 않음 |

`dbt-labs/jaffle_shop`는 보존된 `jaffle-shop-classic`으로 이동하고 README에 유지보수 중단 고지가 있어, 그 안내가 제시한 DuckDB 후속 저장소를 추가로 읽었다. Great Expectations의 기존 링크도 열람 당시 fivetran 소유 저장소로 이동했다. 정확한 `sk family` 주소는 확인하지 못해 추측해 인용하지 않았다.

## 도구와 AI 사용

Codex가 조사 정리, SQL/Python/화면 코드 초안, 테스트 사례와 문서 초안을 작성했다. 검증은 원본 해시, 손계산 가능한 사례, 독립 pandas 집계, 고정 seed 재실행, 별도 코드 리뷰, 실제 브라우저 테스트로 수행했다. 모델이 내놓은 숫자를 분석 결과로 사용하지 않았다. 외부 LLM 호출, 챗봇, 자동 요약 API 없이 핵심 흐름 전체가 작동한다. 이 프로젝트의 AI 사용 경험은 지원자의 독립 수행 경험과 동일하지 않다.

## 보완 전 재확인 (2026-10-29 UTC / 2026-10-30 KST)

동일 채용 공고의 팀 소개·업무·역량·리더 메시지·채용 절차까지 원문을 다시 읽었다. 제품전략팀 Data Analyst의 로그 운영→자동화→제품 분석·실험 흐름을 유지한다. 기존 자료와 [보조 실제 데이터 조사](../data-sources.md)를 대조해 추가 범위를 선정했다. 공개 서비스 안내의 최신 재열람 결과는 [service-guidance-check.json](../../reports/service-guidance-check.json)에 기록했다. 유료 CLASS101 계정의 실제 화면이나 내부 기준 재방문율·일별 유입은 확인하지 못했다.

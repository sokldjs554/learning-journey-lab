# 실제 보조 데이터 조사와 선택

2026-10-29 UTC(2026-10-30 KST)에 공개 원출처·다운로드·라이선스를 확인했다. **OULAD와 기존 결과는 유지하고 EdNet-KT4를 보조 분석으로 추가**했다. Santa는 한국의 모바일·웹 TOEIC 학습 서비스로, 학습 화면 이벤트와 유료 이용권 구매 기록이 함께 있다. CLASS101 내부 데이터나 현재의 구독 사업 데이터는 아니다.

## 후보 비교

| 후보 / 원출처 | 수집 기간·단위·확인한 필드 | 이용 조건·실제 접근 확인 | CLASS101와의 관련성 / 선택 |
|---|---|---|---|
| [EdNet-KT4, Riiid](https://github.com/riiid/ednet) / [논문](https://arxiv.org/abs/1912.03072) | 전체 EdNet은 2017년부터 약 2년; KT2–4의 세부 행동 수집은 **2018-08-27부터**. README는 이용자별 관측 종료일을 제공하지 않으며 시간값을 이동했다고 명시한다. 이용자별 CSV의 `timestamp,action_type,item_id,cursor_time,source,user_answer,platform`; `pay/refund/enroll_coupon`과 이용권 카탈로그 존재. | 원출처 명시: **CC BY-NC 4.0, 연구 목적**. 공식 단축 링크가 Google Drive 공개 ZIP으로 연결됨. 실제 HTTP 206 범위 다운로드·ZIP CRC 검증 성공. 297,915명 중 사전에 고정한 해시 표본 2,048명의 전체 파일과 콘텐츠 파일 확보. | 자율 학습·영상·모바일/웹·유료 접근이라는 공통점. TOEIC 문제 풀이 중심이고 가격·갱신 원장은 없음. **실제 추가 분석에 선택.** |
| [EdNet-KT1](https://github.com/riiid/ednet#kt1) | 2017-04-18부터의 문제 응답 기록. `timestamp,solving_id,question_id,user_answer,elapsed_time`; 784,309명. | 같은 CC BY-NC 4.0. 공식 링크의 공개 Drive 리디렉션 확인; KT1 전체 다운로드는 하지 않음. | 단순 문제 응답 시퀀스라 KT4의 화면·영상·결제 차이를 검증할 수 없다. 같은 서비스 데이터를 두 번 분석하기보다 KT4 선택. |
| [Junyi Academy 2018–2019](https://www.kaggle.com/datasets/junyiacademy/learning-activity-public-dataset-by-junyi-academy) | **2018-08–2019-07**, 선택된 72,630명의 문제 시도 16,217,311행. `Log_Problem.csv` 헤더 직접 확인: `timestamp_TW,uuid,ucid,upid,problem_number,exercise_problem_repeat_session,is_correct,total_sec_taken,total_attempt_cnt,used_hint_cnt,is_hint_used,is_downgrade,is_upgrade,level`. 이용자 테이블에는 `first_login_date_TW` 등이 있음. | 게시자 공식 Kaggle API로 버전 9, 파일 목록·설명·**CC BY-NC-SA 4.0** 확인. 로그/이용자 파일 앞 65,536바이트를 받아 압축을 풀고 헤더 확인; 콘텐츠 CSV 389,397바이트도 접근 성공. 전체 로그 다운로드·분석은 미실시. 게시자 정책과 비상업·동일조건변경허락 준수 필요. | 무료 초·중·고 교육 서비스. 첫 로그인 필드와 명시적 기간은 장점이나 게시자가 이미 선택한 표본이고 결제·구독 자료는 없음. KT4가 유료 접근·이벤트 정의 차이를 더 직접 보여 주므로 이번 추가 분석에서는 제외. |
| [KKBox Churn Prediction Challenge](https://www.kaggle.com/competitions/kkbox-churn-prediction-challenge) | 음악 구독 이탈 예측 대회. 결제·만료·청취 자료 후보로 조사했으나 이번 세션에서는 공식 상세 스키마와 정확한 기간을 검증하지 못함. | 공식 `data`/`rules` 페이지는 Kaggle CSS 로딩 오류, 공식 파일 목록 API는 **HTTP 401**. 공개 대회라는 사실만으로 원자료 재배포·상업 이용 허용을 추정하지 않음. 라이선스/대회 이용 조건 **미확인**, 다운로드·분석 미실시. | 구독 유지 질문에는 가깝지만 음악 서비스이고 이번 접근 권한·이용 조건 검증을 통과하지 못했다. 제3자 복제본으로 우회하지 않고 제외. |
| [HarvardX/MITx AY2013](https://news.mit.edu/2014/mit-and-harvard-release-de-identified-learning-data-open-online-courses) / [Dataverse](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/26147) | MIT 공식 발표에서 **2012–2013년, 16개 강좌**, 비식별화된 학습자-강좌 단위 자료 확인. 개인식별정보 제거·집계·민감 필드 흐림 처리. | Dataverse 웹 접근은 bot blocked, 공식 metadata API는 **HTTP 403**. 현재 데이터 파일·세부 필드·라이선스는 이번 세션에서 검증하지 못했으므로 이용/재배포 가능으로 판정하지 않음. 다운로드·분석 미실시. | 온라인 강좌와 수료라는 공통점은 있으나 과거 대학 MOOC이고 공개 집계 단위가 세부 재개 행동 분석에 약하다. KT4를 선택. |

`미확인`은 데이터가 반드시 비공개라는 의미가 아니라 **이번 실행에서 확인할 수 없었다**는 뜻이다. Kaggle의 HTML 렌더링 오류와 API 인증 오류도 구분했다. Junyi는 HTML 화면이 깨졌어도 공식 API와 실제 파일로 접근·이용 조건을 확인할 수 있었다.

## 원출처와 이용 범위

EdNet 저자: Youngduck Choi, Youngnam Lee, Dongmin Shin, Junghyun Cho, Seoyon Park, Seewoo Lee, Jineon Baek, Chan Bae, Byungsoo Kim, Jaewe Heo. *EdNet: A Large-Scale Hierarchical Dataset in Education*, arXiv:1912.03072. 데이터 제공: Riiid / Santa.

확인한 [README 고정 리비전](https://github.com/riiid/ednet/blob/27db572eeaf4455a1f6c029ba27e34f78bb49d73/README.md)의 SHA-256은 `4230e5fbcc5bda373f315d9cbb4a9eb55e9088225fd1aa5d91b3f628359f923b`이다. 원문 라이선스 문장: “The dataset is publicly released under Creative Commons Attribution-NonCommercial 4.0 International license for research purposes.” [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)은 저작자 표시와 비상업 조건의 공유·변경을 허용한다. 이 프로젝트는 비상업적 분석·검증 범위로 사용하며, 원본 사용자 파일과 사용자별 분석표를 저장소/데모에 재배포하지 않는다. 코드를 실행하면 공식 배포처에서 필요한 데이터만 받는다. 공개하는 것은 출처를 붙인 집계 결과와 재현 코드다. 저장소 코드 라이선스가 원자료 라이선스를 대체하지 않는다.

Junyi의 게시자 공식 API와 검증한 헤더, 차단 응답 등 최소 조사 근거는 [external_source_review.json](../reports/external_source_review.json)에 정리했다. Junyi는 원자료 권리를 확인했으나 이번 프로젝트에서 원자료를 재배포하거나 분석 결과를 만들지는 않았다.

## OULAD를 대체하지 않는 이유

OULAD에서는 개설기·등록 정보, 반복 일별 집계 행, SQL 품질 검사와 반대 방향의 개설기 근거를 이미 검증했다. EdNet은 서비스 내 개별 행동과 구매 기록을 더 가깝게 보여 주지만, 이동된 시간과 이용자별 관측 종료일 부재 때문에 이탈·구독 유지 추정의 분모를 오히려 확정하기 어렵다. 따라서 **OULAD의 기존 판단을 보존하고, 다른 실제 서비스에서 측정 정의와 관찰 연관을 검증하는 보조 자료**로 범위를 정했다. 두 서비스의 숫자를 합치거나 효과 크기를 직접 비교하지 않는다.

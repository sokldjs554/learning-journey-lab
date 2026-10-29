# 주장과 근거 파일

자소서와 제출용 포트폴리오 작성 전에 **지원자가 실제로 실행·이해한 범위**와 아래 측정 사실을 대조한다. 이 문서는 자소서 문장이 아니다.

| 활용 가능한 측정 사실 | 근거 | 말하면 안 되는 확대 해석 |
|---|---|---|
| 공식 공개 학습 자료를 관계형 키·기간·결측 기준으로 검증 | `data/manifest.json`, `sql/quality.sql`, `sql/dimensions.sql` | CLASS101 운영 로그를 관리했다 |
| 동일 값 반복과 처리 민감도를 발견하고 활동일 지표를 채택 | `reports/report.json`의 quality/click_sensitivity, `sql/marts.sql` | 787,170개 오류를 고쳐 회사 데이터를 정확하게 만들었다 |
| SQL 결과를 독립 pandas 계산과 대조 | `scripts/crosscheck.py`, `reports/crosscheck.json` | 외부 기관이 정확성을 인증했다 |
| 다음 주 활동과 첫 주 활동일 사이의 관계·반례를 분석 | `reports/findings.md`, temporal/cohorts/first_day_strata | 재방문을 22.8%p 개선했다 |
| 생성 로그에서 누락·중복·지연·재수집을 재현 | `data/synthetic/`, `src/journey/faults.py`, `sql/faults.sql` | 실제 회사 장애를 복구했다 |
| 반복 점검을 명령과 이슈 이력으로 자동화, 실행 시간 측정 | `scripts/analyze.py`, `src/journey/tracker.py`, `reports/benchmark.json` | 분석가 근무 시간을 특정 % 줄였다 |
| 잘못된 입력·시간 경계·빈/오류 UI를 테스트하고 수정 | `tests/`, `docs/verification.md`, `docs/learning-log.md` | 실제 사용자 피드백을 받아 개선했다 |
| 공개 정적 분석 도구를 배포하고 브라우저에서 확인 | 배포 URL, `reports/browser-deployed.json`, `reports/deployment.json` (생성 후 유효) | 실시간 분석 백엔드/프로덕션 로그 파이프라인을 운영한다 |
| 서비스 맥락에 맞는 실험과 추가 계측을 설계 | `docs/experiment-plan.md`, JSON experiment | 실험으로 매출/연간 구독 효과를 검증했다 |
| AI가 작성한 초안을 테스트·대조하는 개발 과정 | `docs/research/sources.md`, 테스트와 커밋 | 지원자가 코드와 조사 전체를 독립적으로 수행했다 |

## 확인 순서

1. `reports/findings.md`의 각 숫자를 JSON에서 찾는다.
2. 해당 숫자가 나온 SQL·분모·제외 조건을 설명한다.
3. 손계산 실습을 직접 하고 실행 로그와 본인 커밋을 남긴다.
4. CLASS101에 옮기기 위해 무엇을 새로 관측해야 하는지 적는다.
5. 지원자의 실제 참여로 채울 수 없는 문장은 사용하지 않는다.

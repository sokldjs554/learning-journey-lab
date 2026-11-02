# 전체 운영 비교: 입력 수정 방식 v2

Codex가 기존 실측에서 발견한 도구 문제를 수정했다. **새 사람 실측은 아직 없다.** 기존 [실측](full-operations-human-results.md)의 완료 6회·무효 5회·시간은 그대로 보존한다. v2로 기존 시도를 다시 계산하거나 절감률을 만들어내지 않는다.

## 무엇이 달라졌는가

| 구분 | legacy-v1 | retry-input-v2 |
|---|---|---|
| 실행/확인 문구 오타 | 시도 무효, 회차 재시작 | 같은 입력에서 다시 질문 |
| 직접 기록한 값 오류 | 시도 무효, 회차 재시작 | 같은 필드에서 수정 |
| 오류 근거 | 무효 시도·이벤트 | 잘못된 입력, 수정 이력, 최종 값, 오류 건수·이벤트 모두 보존 |
| 시간 | 실패 시도와 재실행을 별도 합산 | 수정 시간을 같은 시도 경과에 포함 |
| 계산 실패·해시 불일치 | 무효 | 계속 무효. 입력 재시도로 덮지 않음 |
| 비교 범위 | 같은 12단계·84항목 | 동일. A는 단계 실행·전사, B는 일괄 실행·자동 채움 검토 |

완료 상태여도 `invalid_inputs`·`input_corrections`는 0이 아닐 수 있다. **수정 후 정확함을 최초 입력 오류가 없었다고 표현하지 않는다.** `audit`는 최종 입력뿐 아니라 각 시도와 오류 이벤트를 대조한다. `reviewed`는 확인 의사 표시이며 이해도 평가가 아니다.

## 새 측정 전제

v2는 조작상의 과도한 재시작 부담 하나를 제거한다. A의 전사와 B의 자동 채움 차이, 한 사람·같은 자료·고정 순서의 학습 효과는 남는다. 따라서 이것도 회사의 실제 전체 업무 시간 절감을 입증하는 설계는 아니다. 회사 적용 시 실제 반복 업무의 입력·검토·수정 범위를 먼저 관찰하고, 충분한 참여자와 순서 분산, 같은 오류 탐지 과제로 검토 품질도 함께 평가해야 한다. 이 개선만으로 인과적인 생산성 효과를 확보했다고 말하지 않는다.

## 실행

기존 측정은 원래의 고정 커밋 `95e8c205deaba7868d56bfda6df2c6035ab8abe1`에서만 계속 확인한다. **새 코드를 기존 측정 폴더 위에 덮거나 기존 protocol을 편집하지 않는다.** 새 코드의 코드 지문이 다르면 기존 연구를 재개하지 않도록 차단한다.

새 별도 저장소 폴더·가상환경에서, 원본 CSV 폴더 경로를 확인한 뒤 다음과 같이 새 측정을 초기화할 수 있다. 아래 경로는 예시이므로 실제 경로로 바꾼다.

```bash
python scripts/full_operations.py init --study work/full-operations-v2 \
  --raw-dir /실제/원본/폴더/data/raw --provenance human_self_reported \
  --input-policy retry-input-v2
python scripts/full_operations.py run --study work/full-operations-v2
python scripts/full_operations.py audit --study work/full-operations-v2
```

일반 기본값은 기존 호환성을 위해 `legacy-v1`이다. 정책은 init 시 고정되고 run 시 프로토콜에서 읽는다. 기존 폴더면 덮어쓰지 않고 종료한다. 연습 A/B 이후 본 측정 ABBAAB의 순서이며 새 측정을 원할 때만 수행한다. 이번 보완에서 지원자에게 재측정을 수행했다고 기록하지 않았다.

## 개발 검증

```bash
python -m pytest -q tests/test_full_operations.py
python scripts/check_operations_v2.py --raw-dir /실제/원본/폴더/data/raw \
  --study work/developer-operations-v2
```

두 번째 명령은 **개발자 자동 입력**으로 실제 OULAD 계산을 실행한다. A에 실행 문구·기록 값·확인 문구 오류, B에 확인 문구 오류를 넣고 같은 회차에서 고친다. `developer_synthetic`은 입력 주체가 사람이 아닌 자동 검증이라는 표시이며 원본 분석 자료는 실제 OULAD다. 사람의 읽기 속도·검토 품질을 재현하지 않는다. 보고서는 `reports/operations-v2-validation.json`이며 시간 절감 수치를 포함하지 않는다.

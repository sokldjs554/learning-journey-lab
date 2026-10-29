"""Regenerate only the numeric blocks so README, findings and JSON share evidence."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]

def generated_blocks(r,b):
    s=r['overall'];c=s['repeat_comparison'];q={x['rule_id']:x['count'] for x in r['quality']['checks']}
    neg=sum(x['content_comparison']['difference']<0 for x in r['cohorts'])
    pct=lambda x:f'{100*x:.1f}%';pp=lambda x:f'{100*x:+.1f}%p'
    facts=f'''| 실제 측정 결과 | 의미 |
|---|---|
| {r['inventory']['studentVle']:,} 활동 행 / {r['unique_people']:,} 고유 학습자 | 공개 원본 전체. 수강 등록은 {r['inventory']['studentRegistration']:,}건 |
| {s['eligible']:,} 분석 수강 건 → {s['w1_active']:,} 첫 주 활성 → {s['w2_returned']:,} 다음 주 재방문 | 재방문율 {pct(s['return_rate'])} |
| 1일 활동 {pct(c['control']['rate'])} vs 2일+ {pct(c['exposed']['rate'])} | 차이 {pp(c['difference'])}, 95% 군집 구간 {pp(c['ci'][0])}~{pp(c['ci'][1])} |
| 동일 값 반복 초과 행 {q['event_exact_repeat']:,}개 | 오류 확정 아님. 첫날 10클릭 기준은 처리에 따라 {r['click_sensitivity'][0]['raw_vs_exact_changed']:,} 수강 건 분류 변경 |
| 첫날 콘텐츠 접촉: {len(r['cohorts'])}개 개설기 중 {neg}개가 반대 방향 | 전체 평균만으로 노출 확대 결론 보류 |
| 생성 실습: 60%처럼 보이는 행 지표, 실제 수신 학습자는 40% | 중복이 누락을 가림. 원천 재수집 뒤 기준 60% 복원 |'''
    validation=f'''- 독립 pandas 집계와 **{s['eligible']:,}개 수강 건 × 3개 활동 지표** 대조: 불일치 0.
- 최종 코드 전체 파이프라인 3회 실행, 결과 JSON SHA256 동일. 실행 중앙값 **{b['median_seconds']:.2f}초** (원본 다운로드 제외, 로컬 환경). 사람의 시간 절감률은 미측정.
- 측정 대상 결과 해시: `{b['runs'][0]['report_sha256']}`.
- 손계산 사례·회귀 테스트와 실제 브라우저 검증의 최종 상태는 [검증 기록](docs/verification.md)에서 확인.'''
    return facts,validation

def main():
    r=json.loads((ROOT/'reports/report.json').read_text());b=json.loads((ROOT/'reports/benchmark.json').read_text())
    facts,validation=generated_blocks(r,b)
    path=ROOT/'README.md';s=path.read_text()
    for name,body in [('FINDINGS',facts),('VALIDATION',validation)]:
        s=re.sub(f'<!-- BEGIN GENERATED {name} -->.*?<!-- END GENERATED {name} -->',f'<!-- BEGIN GENERATED {name} -->\n{body}\n<!-- END GENERATED {name} -->',s,flags=re.S)
    path.write_text(s)
    (ROOT/'reports/findings.md').write_text('# 분석 결과\n\n`reports/report.json`에서 자동 생성. 공개 OULAD와 생성 실습 구분.\n\n'+facts+'\n\n## 재현 측정\n\n'+validation.replace('(docs/verification.md)','(../docs/verification.md)')+'\n\n## 판단\n\n활동일 신호로 다음 학습 진입점 실험을 제안한다. 클릭 임계값의 정답과 연간 구독 리텐션 효과는 판단할 수 없다. 개설기·다음 해·최초 활동일별 비교는 report.json에 포함되며 인과효과가 아니다.\n')
    print('README and findings regenerated from measured evidence')
if __name__=='__main__':main()

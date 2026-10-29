"""Validate supplementary source boundaries before a static release (stdlib only)."""
import json,math,hashlib,shutil

def require(condition,message):
    if not condition:raise ValueError(message)
def count(x):return type(x) is int and x>=0
def close(a,b):return isinstance(a,(int,float)) and math.isfinite(a) and abs(a-b)<1e-10

def validate_external(r):
    require(r['analysis_type']=='observational_public_data','External source is descriptive')
    require(r['manifest']['dataset']=='EdNet-KT4','Unexpected dataset')
    require(r['censoring_sensitivity']['status']=='not_identifiable','Coverage cannot be asserted')
    n=r['sample']['users'];q=r['quality'];p=r['payments']
    require(count(n) and n==r['manifest']['sample_users'] and n>0,'Sample size')
    require(q['raw_rows']==r['sample']['raw_rows']==sum(q['action_counts'].values()),'Event inventory')
    require(q['raw_rows']-q['exact_duplicate_rows']==q['deduplicated_rows'],'Repeat rows')
    comparisons=[r['primary'],*r['event_definition_sensitivity']]
    require([c['definition'] for c in comparisons]==['submit','entry','ui'],'Event definitions')
    for c in comparisons:
        require([g['active_days'] for g in c['groups']]==['1','2+'],'Group identities')
        require(count(c['eligible_firstweek_users']) and count(c['excluded_zero_firstweek_users']),'Cohort counts')
        require(c['eligible_firstweek_users']+c['excluded_zero_firstweek_users']==n,'Denominator')
        require(len(c['groups'])==2 and sum(g['n'] for g in c['groups'])==c['eligible_firstweek_users'],'Group totals')
        for g in c['groups']:
            require(count(g['n']) and count(g['recorded_nextweek']) and g['recorded_nextweek']<=g['n'],'Group counts')
            require((g['rate'] is None if not g['n'] else close(g['rate'],g['recorded_nextweek']/g['n'])),'Group rate')
        a,b=c['groups'];require(close(c['difference'],b['rate']-a['rate']),'Group difference')
        require(len(c['ci95'])==2 and all(math.isfinite(x) and -1<=x<=1 for x in c['ci95']) and c['ci95'][0]<=c['ci95'][1],'Difference interval')
    require(p['pay_events']==q['action_counts'].get('pay',0) and p['refund_events']==q['action_counts'].get('refund',0),'Payment counts')
    for people,events,action in [('paying_users','pay_events','pay'),('refunding_users','refund_events','refund'),('coupon_users','coupon_events','enroll_coupon')]:
        require(count(p[people]) and count(p[events]) and p[people]<=min(n,p[events]),'Payment people')
        require(p[events]==q['action_counts'].get(action,0),'Commerce event inventory')
    require(r['validation']['sql_pandas_equal'] and r['validation']['repeat_feature_equal'] and r['validation']['compared_user_rows']==n,'Independent validation')
    return r

def validate_experiment(r,original):
    require(r['type']=='synthetic_engineering_validation_not_live_experiment','Engineering provenance')
    require(r['actual_participants']==0 and r['actual_service_effect'] is None and r['actual_service_baseline'] is None and r['actual_daily_eligible'] is None,'No live experiment')
    for case in r['synthetic_cases'].values():
        require(case['status'] in ['hold','ready_for_review'],'Unknown readiness')
        require(case['status']!='hold' or case['difference'] is None,'Hold cannot report difference')
    targets={(x['baseline'],x['mde']):x['per_arm'] for x in original['experiment']['samples']}
    require(len(r['recruitment_scenarios'])==18,'Scenario coverage')
    seen=set()
    for x in r['recruitment_scenarios']:
        key=(x['baseline'],x['mde']);d=x['hypothetical_daily_eligible']
        require(key in targets and x['per_arm']==targets[key] and d in [50,100,500],'Scenario input')
        require((key,d) not in seen,'Duplicate scenario');seen.add((key,d))
        raw=math.ceil(2*x['per_arm']/d);weeks=max(7,7*math.ceil(raw/7))
        require(x['raw_recruitment_days']==raw and x['recruitment_days']==weeks and x['maturation_days']==14 and x['late_buffer_days']==1 and x['total_days_upper_bound']==weeks+15,'Recruitment arithmetic')
    return r

def validate_all(root):
    original=json.loads((root/'reports/report.json').read_text())
    validate_external(json.loads((root/'reports/ednet_report.json').read_text()))
    validate_experiment(json.loads((root/'reports/experiment-readiness.json').read_text()),original)

def publish(root):
    validate_all(root);hashes={}
    for name in ['ednet_report.json','experiment-readiness.json']:
        source=root/'reports'/name;shutil.copyfile(source,root/'web/data'/name)
        hashes[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    return hashes

def summary_block(r):
    q,p,s=r['quality'],r['payments'],r['sample'];a,b=r['primary']['groups']
    return '\n'.join([
        f"- EdNet-KT4: 사전 해시 표본 **{s['users']:,}명 / {s['raw_rows']:,}행**, 사용자별 제공 파일 전체.",
        f"- 문제 제출 ↔ 모든 이벤트(구매·환불 포함): 첫 주 **2일 이상 여부 {q['firstweek_activity_group_changed_submit_vs_all_ui']}명**, 다음 주 기록 여부 **{q['nextweek_flag_changed_submit_vs_all_ui']}명** 변경.",
        f"- 문제 제출 기준 다음 주 기록: 1일군 **{a['recorded_nextweek']:,}/{a['n']:,} ({a['rate']*100:.1f}%)**, 2일+군 **{b['recorded_nextweek']:,}/{b['n']:,} ({b['rate']*100:.1f}%)**. 관찰 종료가 불명확해 서비스 유지율로 해석하지 않음.",
        f"- 동일 값 반복 초과 **{q['exact_duplicate_rows']:,}행**, 동일 값 한 번 처리 시 활동 지표 변경 **{q['raw_vs_dedup_changed_users']}명**. 플랫폼 결측 **{q['missing_platform_rows']}행**은 구매·환불·쿠폰 기록에 집중.",
        f"- 구매 **{p['pay_events']}행/{p['paying_users']}명**, 환불 **{p['refund_events']}행/{p['refunding_users']}명**. 가격·거래 ID·갱신·권한 원장이 없어 매출과 갱신율은 산출하지 않음.",
        f"- SQL과 독립 pandas 계산 **{r['validation']['compared_user_rows']:,}명** 일치. 실제 파일 해시·ZIP CRC 검증, 동일 캐시 분석 2회 결과 일치.",
    ])

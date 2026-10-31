"""One-command, offline-after-download evidence build."""
import json
import sys
import time
from pathlib import Path
import hashlib
import platform
import math
import numpy as np
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from journey.pipeline import connect,load_sources,quality,build_marts
from journey.statistics import summarize,temporal_split,compare
from journey.faults import fault_lab
from journey.tracker import update_issues


def write_json(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def sample_size(p,delta):
    p2=p+delta;bar=(p+p2)/2
    return math.ceil(((norm.ppf(.975)*math.sqrt(2*bar*(1-bar))+norm.ppf(.8)*math.sqrt(p*(1-p)+p2*(1-p2)))/delta)**2)


def main(ROOT=ROOT, checkpoint=None):
    """Run unchanged calculations; optional explicit before/after checkpoints."""
    def before(name):
        if checkpoint: checkpoint.before(name)
    def after(name, payload):
        if checkpoint: checkpoint.after(name, payload)
    started=time.perf_counter();times={}
    c=connect(ROOT/'work/analysis.duckdb')
    before('source_load')
    t=time.perf_counter();load_sources(c,ROOT/'data/raw',ROOT/'data/manifest.json');times['load_and_hash_seconds']=time.perf_counter()-t
    after('source_load', {'source_files':len(json.loads((ROOT/'data/manifest.json').read_text())['files']), 'archive_sha256':json.loads((ROOT/'data/manifest.json').read_text())['archive_sha256']})
    before('quality')
    t=time.perf_counter();checks=quality(c);times['quality_seconds']=time.perf_counter()-t
    after('quality', {'checks':checks})
    if any(x['count'] and x['severity']=='block' for x in checks):
        write_json(ROOT/'reports/quality-failure.json',{'checks':checks,'gate':'BLOCK'})
        c.close();raise SystemExit(2)
    before('marts')
    t=time.perf_counter();mart=build_marts(c);strict=build_marts(c,strict=True);build_marts(c);times['mart_and_sensitivity_seconds']=time.perf_counter()-t
    after('marts', {'eligible':len(mart), 'strict_w1_active':int((strict.w1_days>0).sum()), 'strict_w2_returned':int(strict.loc[strict.w1_days>0,'w2_active'].sum())})
    before('overall')
    t=time.perf_counter();all_summary=summarize(mart)
    after('overall', all_summary)
    before('cohorts')
    cohorts=[]
    for (module,term),m in mart.groupby(['code_module','code_presentation'],sort=True):
        cohorts.append({'module':module,'term':term,**summarize(m,draws=500)})
    after('cohorts', {'cohorts':cohorts})
    before('temporal')
    train,holdout=temporal_split(mart)
    # Also exclude earlier registered learners who were ineligible in 2013.
    prior=set(c.sql("select distinct id_student from studentRegistration where code_presentation like '2013%'").df().id_student)
    holdout=holdout[~holdout.id_student.isin(prior)]
    temporal=[{'label':'2013 탐색','id':'discovery',**summarize(train)},
              {'label':'2014 신규 학습자 재확인','id':'holdout',**summarize(holdout)}]
    after('temporal', {'temporal':temporal})
    before('sensitivity')
    active=mart[mart.w1_days>0].copy();active['repeat']=(active.w1_days>=2).astype(int)
    by_start=[]
    for day,m in active.groupby('first_day',sort=True):
        by_start.append({'first_day':int(day),'comparison':compare(m,'repeat',draws=500)})
    click_sensitivity=[]
    for threshold in [10,20,50]:
        raw=active.first_clicks_raw>=threshold; exact=active.first_clicks_exact>=threshold; maximum=active.first_clicks_max>=threshold
        click_sensitivity.append({'threshold':threshold,'raw_qualified':int(raw.sum()),'exact_qualified':int(exact.sum()),'max_qualified':int(maximum.sum()),
                                  'raw_vs_exact_changed':int((raw!=exact).sum()),'raw_vs_max_changed':int((raw!=maximum).sum())})
    transition=[]
    for first in [0,1]:
        for second in [0,1]:
            s=mart[((mart.w1_days>0).astype(int)==first)&(mart.w2_active==second)]
            transition.append({'w1':first,'w2':second,'n':len(s),'later_active':int(s.later_active.sum())})
    eligibility=c.sql('''select count(*) total, count(*) filter(where date_registration is null) missing_registration,
      count(*) filter(where date_registration is not null and date_registration>0) late_registration,
      count(*) filter(where date_registration<=0 and date_unregistration<0) pre_start_withdrawal
      from studentRegistration''').df().to_dict('records')[0]
    inventory={name:int(c.sql(f'select count(*) from {name}').fetchone()[0]) for name in ['studentVle','studentRegistration','studentInfo','vle','courses','assessments','studentAssessment']}
    unique=int(c.sql('select count(distinct id_student) from studentInfo').fetchone()[0])
    total_clicks=int(c.sql('select sum(sum_click) from studentVle').fetchone()[0])
    event_range=list(c.sql('select min(date),max(date) from studentVle').fetchone())
    times['statistics_seconds']=time.perf_counter()-t
    after('sensitivity', {'first_day_strata':by_start, 'click_sensitivity':click_sensitivity, 'transition':transition})
    before('fault_lab')
    fault=fault_lab(ROOT/'data/synthetic')
    after('fault_lab', fault)
    before('report_issues')
    gate='BLOCK' if any(x['count'] and x['severity']=='block' for x in checks) else ('REVIEW' if any(x['count'] for x in checks) else 'PASS')
    report={'schema_version':1,'title':'Learning Journey Lab','as_of':'2026-10-29','source_type':'public',
      'source':{'name':'OULAD','authors':'Jakub Kuzilek, Martin Hlosta, Zdenek Zdrahal','years':[2013,2014],
                'url':'https://research.stem.open.ac.uk/ouanalyse/open-dataset-more/','doi':'https://doi.org/10.1038/sdata.2017.171','license':'CC BY 4.0',
                'archive_sha256':json.loads((ROOT/'data/manifest.json').read_text())['archive_sha256']},
      'inventory':inventory,'unique_people':unique,'raw_clicks':total_clicks,'event_day_range':event_range,
      'eligibility':eligibility,'quality':{'gate':gate,'checks':checks,'unobservable':['원천 이벤트 누락','일내 발생 순서','영상 시청 시간','구독 결제·갱신']},
      'overall':all_summary,'cohorts':cohorts,'temporal':temporal,'first_day_strata':by_start,
      'transition':transition,'click_sensitivity':click_sensitivity,
      'strict_sensitivity':{'w1_active':int((strict.w1_days>0).sum()),'w2_returned':int(strict.loc[strict.w1_days>0,'w2_active'].sum()),
                            'changed_w1_enrollments':int((mart.w1_days!=strict.w1_days).sum()),
                            'changed_w2_enrollments':int((mart.w2_active!=strict.w2_active).sum())},
      'fault_lab':fault,'experiment':{'type':'design_only','alpha':.05,'power':.8,'allocation':'1:1',
        'samples':[{'baseline':p,'mde':d,'per_arm':sample_size(p,d)} for p in [.3,.5,.7] for d in [.03,.05]]}}
    write_json(ROOT/'reports/report.json',report)
    (ROOT/'work').mkdir(exist_ok=True)
    mart.to_csv(ROOT/'work/enrollment_mart.csv',index=False)
    # No raw learner IDs in published artifacts.
    issue_path=ROOT/'reports/issues.json'
    previous=json.loads(issue_path.read_text()) if issue_path.exists() else []
    # Legacy pre-tracker exports were flat observations, not historical evidence.
    previous=[r for r in previous if 'history' in r]
    issue_records=update_issues(previous,checks,report['source']['archive_sha256'])
    write_json(issue_path,issue_records)
    after('report_issues', {'report_sha256':hashlib.sha256((ROOT/'reports/report.json').read_bytes()).hexdigest(), 'mart_rows':len(mart), 'issue_records':len(issue_records), 'issue_history_entries':sum(len(x['history']) for x in issue_records)})
    times['total_seconds']=time.perf_counter()-started
    write_json(ROOT/'work/latest_run.json',{'python':platform.python_version(),'duckdb':__import__('duckdb').__version__,
        'platform':platform.platform(),'timings':times,'report_sha256':hashlib.sha256((ROOT/'reports/report.json').read_bytes()).hexdigest()})
    print(json.dumps({'gate':gate,'eligible':all_summary['eligible'],'w1':all_summary['w1_active'],'w2':all_summary['w2_returned'],'seconds':round(times['total_seconds'],3)},ensure_ascii=False))
    c.close()
    if gate=='BLOCK': raise SystemExit(2)

if __name__=='__main__':main()

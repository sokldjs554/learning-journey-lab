"""Descriptive associations; learner-cluster bootstrap, not causal estimates."""
import numpy as np


def temporal_split(mart):
    train=mart[mart.code_presentation.str.startswith('2013')].copy()
    holdout=mart[mart.code_presentation.str.startswith('2014') & ~mart.id_student.isin(train.id_student)].copy()
    return train,holdout


def compare(frame, exposure, draws=1000, seed=101):
    groups=[]
    for value in [0,1]:
        s=frame[frame[exposure]==value]; n=len(s); y=int(s.w2_active.sum())
        groups.append({'n':n,'returned':y,'rate':y/n if n else None})
    result={'control':groups[0],'exposed':groups[1], 'difference':None,'ci':None,
            'clusters':int(frame.id_student.nunique()),'bootstrap_draws':draws,'valid_draws':0}
    if not all(g['n'] for g in groups): return result
    result['difference']=groups[1]['rate']-groups[0]['rate']
    if any(frame.loc[frame[exposure]==v,'id_student'].nunique()<2 for v in [0,1]): return result
    f=frame.assign(n0=(frame[exposure]==0).astype(int),n1=(frame[exposure]==1).astype(int))
    f=f.assign(y0=f.n0*f.w2_active,y1=f.n1*f.w2_active)
    a=f.groupby('id_student',sort=True)[['n0','n1','y0','y1']].sum().to_numpy(dtype=float)
    rng=np.random.default_rng(seed); diffs=[]
    for _ in range(draws):
        n0,n1,y0,y1=a[rng.integers(0,len(a),len(a))].sum(axis=0)
        if n0 and n1: diffs.append(y1/n1-y0/n0)
    if diffs: result['ci']=np.quantile(diffs,[.025,.975]).tolist()
    result['valid_draws']=len(diffs)
    return result


def summarize(mart,draws=1000):
    active=mart[mart.w1_days>0].copy()
    active['repeat']=(active.w1_days>=2).astype(int)
    n=len(mart); w1=len(active); w2=int(active.w2_active.sum())
    days=[]
    for day in range(8):
        s=mart[mart.w1_days==day]
        days.append({'days':day,'n':len(s),'returned':int(s.w2_active.sum()),'rate':float(s.w2_active.mean()) if len(s) else None})
    return {'eligible':n,'w1_active':w1,'w2_returned':w2,'return_rate':w2/w1 if w1 else None,
            'unique_learners':int(mart.id_student.nunique()),'days':days,
            'repeat_comparison':compare(active,'repeat',draws),
            'content_comparison':compare(active,'first_content',draws)}

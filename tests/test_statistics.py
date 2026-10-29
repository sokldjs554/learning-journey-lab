import pandas as pd
from journey.statistics import compare, temporal_split


def test_known_risk_difference_and_empty_group():
    d=pd.DataFrame({'id_student':[1,2,3,4], 'exposed':[0,0,1,1], 'w2_active':[0,1,1,1]})
    r=compare(d,'exposed',draws=100,seed=3)
    assert r['control']=={'n':2,'returned':1,'rate':0.5}
    assert r['exposed']=={'n':2,'returned':2,'rate':1.0}
    assert r['difference']==0.5
    assert r['ci'][0]<=0.5<=r['ci'][1]
    assert compare(d[d.exposed==1],'exposed')['difference'] is None


def test_cluster_bootstrap_repeated_enrollment_invariance():
    d=pd.DataFrame({'id_student':[1,2,3,4], 'exposed':[0,0,1,1], 'w2_active':[0,1,0,1]})
    a=compare(d,'exposed',draws=200,seed=19)
    b=compare(pd.concat([d,d]),'exposed',draws=200,seed=19)
    assert a['ci']==b['ci']
    assert a['clusters']==b['clusters']==4


def test_holdout_has_no_earlier_learner():
    d=pd.DataFrame({'id_student':[1,2,1,3], 'code_presentation':['2013B','2013J','2014B','2014J']})
    train, holdout=temporal_split(d)
    assert train.id_student.tolist()==[1,2]
    assert holdout.id_student.tolist()==[3]


def test_single_independent_learner_has_no_inferential_interval():
    d=pd.DataFrame({'id_student':[1,1], 'exposed':[0,1], 'w2_active':[0,1]})
    r=compare(d,'exposed',draws=100)
    assert r['difference']==1
    assert r['ci'] is None
    assert r['valid_draws']==0

"""Independent pandas calculation; does not import production SQL or helpers."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
KEY=['code_module','code_presentation','id_student']

def main():
    r=pd.read_csv(ROOT/'data/raw/studentRegistration.csv',na_values=['?'])
    co=pd.read_csv(ROOT/'data/raw/courses.csv')
    r=r.merge(co,on=['code_module','code_presentation'],validate='many_to_one')
    r=r[(r.date_registration<=0)&(r.date_unregistration.isna()|(r.date_unregistration>=0))&(r.module_presentation_length>=28)]
    sites=pd.read_csv(ROOT/'data/raw/vle.csv')
    pieces=[]
    for chunk in pd.read_csv(ROOT/'data/raw/studentVle.csv',chunksize=500000):
        s=chunk[(chunk.date>=0)&(chunk.date<=27)&(chunk.sum_click>0)]
        s=s.merge(r[KEY],on=KEY,validate='many_to_one').merge(sites[['code_module','code_presentation','id_site']],on=['code_module','code_presentation','id_site'],validate='many_to_one')
        pieces.append(s[KEY+['date']].drop_duplicates())
    days=pd.concat(pieces,ignore_index=True).drop_duplicates()
    results=r[KEY].copy()
    for name,lo,hi in [('w1_days',0,6),('w2_active',7,13),('later_active',14,27)]:
        counts=days[days.date.between(lo,hi)].groupby(KEY).size().rename(name).reset_index()
        results=results.merge(counts,on=KEY,how='left',validate='one_to_one')
        results[name]=results[name].fillna(0).astype(int)
        if name!='w1_days':results[name]=(results[name]>0).astype(int)
    actual=pd.read_csv(ROOT/'work/enrollment_mart.csv')
    cols=KEY+['w1_days','w2_active','later_active']
    a=actual[cols].sort_values(KEY).reset_index(drop=True)
    b=results[cols].sort_values(KEY).reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b,check_dtype=False)
    result={'method':'independent pandas chunked CSV → enrollment/day sets; no production SQL imports',
            'enrollments_compared':len(a),'fields_compared':['w1_days','w2_active','later_active'],'mismatched_rows':0}
    (ROOT/'reports/crosscheck.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()

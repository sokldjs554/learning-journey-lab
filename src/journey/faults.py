"""Entirely generated fault fixtures. No OULAD or CLASS101 rows are used."""
from pathlib import Path
import hashlib
import json
import pandas as pd
import duckdb

ROOT=Path(__file__).resolve().parents[2]


def generate():
    rows=[]
    for day,users in [(0,range(1,11)),(7,range(1,7))]:
        for u in users:
            for kind,offset in [('start',0),('complete',60)]:
                t=day*86400+u*100
                rows.append({'event_id':f'e-{day}-{u}-{kind}','user_id':f'u{u}', 'session_id':f's-{day}-{u}',
                             'event_type':kind,'occurred_at':t+offset,'ingested_at':t+offset+5})
    truth=pd.DataFrame(rows)
    # A valid event-time sequence can arrive out of order.
    truth.loc[truth.event_id=='e-0-2-start','ingested_at']=300
    delivery=truth[~truth.event_id.str.startswith('e-7-5-')].copy()
    delivery.loc[delivery.event_id.str.startswith('e-7-6-'),'ingested_at']=15*86400
    duplicate=delivery[delivery.event_id=='e-7-1-start']
    extras=[]
    for eid,user,session,kind,t in [('bad-null',None,'null-session','start',10),('bad-user','ghost','orphan','start',20),
                                  ('bad-start','u7','inverted','start',2*86400+100),('bad-complete','u7','inverted','complete',2*86400+90)]:
        extras.append(dict(event_id=eid,user_id=user,session_id=session,event_type=kind,occurred_at=t,ingested_at=t+10))
    delivery=pd.concat([delivery,duplicate,duplicate,pd.DataFrame(extras)],ignore_index=True)
    return truth,delivery


def fault_lab(output=None):
    truth,delivery=generate()
    c=duckdb.connect();c.register('source_ledger',truth);c.register('delivery',delivery)
    c.execute("create table learners as select 'u'||i user_id from range(1,13) t(i)")
    c.execute((ROOT/'sql/faults.sql').read_text())
    rules=[
        ('duplicate_id','SELECT count(*)-count(distinct event_id) FROM received','같은 event_id 재수신; 최초 수신 보존'),
        ('null_user','SELECT count(*) FROM received WHERE user_id IS NULL','사용자 키 결측; 격리'),
        ('unknown_user','SELECT count(*) FROM received WHERE user_id IS NOT NULL AND user_id NOT IN(SELECT user_id FROM learners)','등록 키 불일치; 격리'),
        ('semantic_order','SELECT count(*) FROM bad_sessions','완료 시각이 시작보다 빠름; 세션 격리'),
        ('arrival_order',"SELECT count(*) FROM unique_received f JOIN unique_received s USING(session_id) WHERE f.event_type='complete' AND s.event_type='start' AND f.occurred_at>s.occurred_at AND f.ingested_at<s.ingested_at",'수신 순서 역전; 발생 시각으로 정렬'),
        ('missing_manifest_events','SELECT count(*) FROM source_ledger s WHERE NOT EXISTS(SELECT 1 FROM received r WHERE s.event_id=r.event_id)','별도 원천 전송 명세 대조; 재수집 필요')]
    issues=[{'rule_id':rid,'count':c.execute(sql).fetchone()[0],'action':action,'query':sql} for rid,sql,action in rules]
    # Later delivery only recovers delayed events; lost user u5 is not guessed.
    c.execute('CREATE TEMP VIEW late_clean AS SELECT * FROM cleaned UNION ALL SELECT * FROM delivery WHERE ingested_at>=14*86400 AND ingested_at<16*86400')
    stages=[]
    for key,table,title in [('truth','source_ledger','정상 기준'),('observed','received','장애 수신'),('clean','cleaned','중복·키 정리'),('late','late_clean','지연 수신 반영'),('replay','source_ledger','원천 재수집')]:
        starts=c.execute(f"SELECT user_id,occurred_at FROM {table} WHERE event_type='start' AND user_id IN(SELECT user_id FROM learners)").fetchall()
        first={u for u,t in starts if 0<=t<7*86400}; returning={u for u,t in starts if 7*86400<=t<14*86400}&first
        row_returns=sum(1 for u,t in starts if u in first and 7*86400<=t<14*86400)
        missing=c.execute(f'SELECT count(*) FROM source_ledger s WHERE NOT EXISTS(SELECT 1 FROM {table} r WHERE s.event_id=r.event_id)').fetchone()[0]
        stages.append({'id':key,'label':title,'w1':len(first),'w2':len(returning),'rate':len(returning)/len(first),
                       'naive_rate':row_returns/len(first),'missing_events':missing,'gate':'BLOCK' if missing or key=='observed' else 'PASS'})
    payload={'source_type':'synthetic','seed':'deterministic-v1-no-randomness','enrolled':12,'stages':stages,'issues':issues,
             'truth_sha256':hashlib.sha256(truth.to_csv(index=False).encode()).hexdigest(),
             'delivery_sha256':hashlib.sha256(delivery.to_csv(index=False).encode()).hexdigest(),
             'assumption':'원천 전송 명세는 이 생성 실습에서만 존재. OULAD의 누락 건수를 알아낸 것이 아님.'}
    if output:
        folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
        truth.to_csv(folder/'source_ledger.csv',index=False);delivery.to_csv(folder/'delivery.csv',index=False)
        (folder/'README.md').write_text('# 생성 로그\n\n`src/journey/faults.py`가 고정 규칙으로 생성. 실제 사용자·CLASS101·OULAD 데이터 없음. 숫자는 파이프라인 검증용.\n')
    c.close()
    return payload

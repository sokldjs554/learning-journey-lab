#!/usr/bin/env python3
"""Validate locally exported task intervals. Never uploads or writes participant data.
Consistency checks cannot authenticate a participant, attention, or untampered clocks.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

SNAPSHOT = '675dfa6fa3126da0ba74b5a4b4c4222afff4d950297703f3314788f9135a30db'
EXPECTED = [('event_exact_repeat',787170,'review','open'),('registration_missing_date',45,'review','open'),('event_unknown_site',0,'block','clear')]

def require(condition,message):
    if not condition: raise ValueError(message)

def number(value,label):
    require(type(value) in (int,float) and math.isfinite(value) and value>=0,label+' must be finite and nonnegative')
    return value

def evaluate(rows):
    require(isinstance(rows,list) and len(rows)==3,'Exactly three output rows required')
    omissions=errors=unreviewed=0
    for row,(rule,count,severity,status) in zip(rows,EXPECTED):
        require(isinstance(row,dict) and row.get('rule_id')==rule,'Output rules/order mismatch')
        for field,expected in [('count',count),('severity',severity),('status',status)]:
            require(field in row,'Output field missing: '+field)
            val=row[field]
            if val is None or val=='':omissions+=1
            elif field=='count':
                require(type(val) is int and val>=0,'Count must be a nonnegative integer or null')
                errors+=int(val!=expected)
            else:
                require(isinstance(val,str),'Output label must be string')
                errors+=int(val!=expected)
        require(type(row.get('reviewed')) is bool,'Explicit review boolean required')
        unreviewed+=int(not row['reviewed'])
    return dict(omissions=omissions,errors=errors,unreviewed=unreviewed,valid=(omissions+errors+unreviewed==0))

def timing(t):
    require(isinstance(t,dict),'Measured timing required')
    segments=t.get('segments')
    require(isinstance(segments,list) and segments,'Timing segments required')
    cursor=active=excluded=0
    for s in segments:
        require(isinstance(s,dict) and s.get('kind') in ('active','manual_pause','hidden'),'Unknown interval kind')
        start=number(s.get('start_ms'),'start_ms'); end=number(s.get('end_ms'),'end_ms')
        require(abs(start-cursor)<0.01 and end>=start,'Timing gap, overlap, or reversed interval')
        if s['kind']=='active':active+=end-start
        else:excluded+=end-start
        cursor=end
    require(segments[0]['kind']=='active','A trial must start active')
    for name,expected in [('elapsed_ms',cursor),('task_interval_ms',active),('excluded_ms',excluded)]:
        require(abs(number(t.get(name),name)-expected)<0.02,'Timing sum mismatch: '+name)
    require(active>0,'Empty active interval')
    try:
        start=datetime.fromisoformat(t['started_at'].replace('Z','+00:00'))
        end=datetime.fromisoformat(t['finished_at'].replace('Z','+00:00'))
        require(start.tzinfo is not None and end.tzinfo is not None,'Timestamp timezone required')
        require(abs((end-start).total_seconds()*1000-cursor)<2000,'Wall clock and monotonic clock differ; trial invalid')
    except (KeyError,TypeError,AttributeError) as exc:raise ValueError('Invalid timestamps') from exc
    return active

def validate(payload,report_path=None):
    require(isinstance(payload,dict),'JSON object required')
    require(payload.get('schema_version')==1 and payload.get('protocol')=='three-rule-transfer-v1','Unknown protocol')
    require(payload.get('snapshot_sha256')==SNAPSHOT,'Wrong snapshot')
    if report_path:
        raw=Path(report_path).read_bytes();require(hashlib.sha256(raw).hexdigest()==SNAPSHOT,'Local report SHA mismatch')
        checks=json.loads(raw)['quality']['checks']
        for rule,count,severity,_ in EXPECTED:
            found=[r for r in checks if r['rule_id']==rule]
            require(len(found)==1 and found[0]['count']==count and found[0]['severity']==severity,'Local expected values differ')
    require(payload.get('origin') in ('human_self_reported','developer_synthetic'),'Explicit origin required')
    env=payload.get('environment')
    require(isinstance(env,dict) and all(isinstance(env.get(k),str) and env[k].strip() for k in ('user_agent','viewport','context_notes')),'Environment and context notes required')
    number(payload.get('report_load_ms'),'report_load_ms')
    rounds=payload.get('rounds');require(isinstance(rounds,list),'Rounds required')
    practices=[r for r in rounds if isinstance(r,dict) and r.get('phase')=='practice']
    measured=[r for r in rounds if isinstance(r,dict) and r.get('phase')=='measured']
    require(len(rounds)==len(practices)+len(measured),'Unknown round phase')
    require(rounds==practices+measured,'Practice must precede measurement')
    require([r.get('mode') for r in measured]==list('ABBAAB'),'Six measured rounds in ABBAAB order required')
    successes=[]
    for r in practices:
        require(r.get('mode')==('A' if not successes else 'B'),'Practice order mismatch')
        score=evaluate(r.get('outputs'))
        require(all(type(r.get(k)) is type(v) and r[k]==v for k,v in score.items()),'Practice score mismatch')
        require(r.get('timing') is None,'Practice must be untimed')
        if score['valid']:successes.append(r['mode'])
    require(successes==['A','B'],'One successful untimed practice per mode required')
    valid=0
    previous_end=None
    for r in rounds:
        score=evaluate(r.get('outputs'))
        require(all(type(r.get(k)) is type(v) and r[k]==v for k,v in score.items()),'Output evaluation mismatch')
        machine=number(r.get('machine_generation_ms'),'machine_generation_ms')
        require(r.get('mode') in ('A','B') and (r['mode']=='B' or machine==0),'Manual round cannot claim generation time')
        if r['phase']=='measured':
            active=timing(r.get('timing'));require(machine<=active+0.02,'Generation time exceeds task interval')
            start=datetime.fromisoformat(r['timing']['started_at'].replace('Z','+00:00'))
            end=datetime.fromisoformat(r['timing']['finished_at'].replace('Z','+00:00'))
            require(previous_end is None or start>=previous_end,'Measured rounds overlap or go backward')
            previous_end=end
            valid+=int(score['valid'])
    return dict(protocol=payload['protocol'],origin=payload['origin'],human_measurement=payload['origin']=='human_self_reported',valid_measured_rounds=valid,all_measured_rounds_valid=valid==6,comparison_ready=valid==6 and payload['origin']=='human_self_reported',note='Consistency validated only. Human identity/attention and clock authenticity are not verified. No productivity claim inferred.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export',type=Path)
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'web/data/report.json')
    args=parser.parse_args()
    try:
        require(args.export.stat().st_size<=2_000_000,'Export too large')
        result=validate(json.loads(args.export.read_text()),args.report)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        parser.exit(1,'INVALID: '+str(exc)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

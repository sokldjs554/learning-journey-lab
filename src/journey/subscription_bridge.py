"""Small synthetic renewal contract. Never an estimator of CLASS101 outcomes."""
from datetime import datetime, timezone
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    """Deterministic, hand-authored fictional annual cycles and full-refund events."""
    cycles=[];members=[];learning=[];billing=[]
    for n in range(1,9):
        cycle=f'c{n}'
        cycles.append(dict(cycle_id=cycle,subscription_id=f's{n}',payer_id=f'p{n}',
            plan_type='group' if n==5 else 'individual',started_at='2024-01-01T00:00:00+00:00',
            renewal_due_at='2025-02-01T00:00:00+00:00' if n==4 else '2025-01-01T00:00:00+00:00',
            cancel_requested_at='2024-12-20T00:00:00+00:00' if n in [6,7] else None))
        for suffix in (['a','b'] if n==5 else ['a']):
            members.append(dict(cycle_id=cycle,learner_id=f'l{n}{suffix}',
                valid_from='2024-01-01T00:00:00+00:00',valid_to='2025-03-01T00:00:00+00:00'))
    for n,suffix,day in [(1,'a',1),(1,'a',2),(2,'a',1),(3,'a',1),(5,'a',1),(5,'b',2),(7,'a',1),(8,'a',2)]:
        timestamp=f'2024-01-{day:02d}T12:00:00+00:00'
        learning.append(dict(event_id=f'learn{len(learning)+1}',cycle_id=f'c{n}',learner_id=f'l{n}{suffix}',
                             occurred_at=timestamp,ingested_at=timestamp))
    for n,kind,day in [(1,'settled',1),(2,'failed',1),(3,'settled',1),(3,'refunded',3),
                       (5,'settled',1),(6,'settled',1),(8,'settled',9)]:
        timestamp=f'2025-01-{day:02d}T12:00:00+00:00'
        billing.append(dict(event_id=f'pay{n}' if kind!='refunded' else 'refund3',transaction_id=f't{n}',
                            cycle_id=f'c{n}',kind=kind,occurred_at=timestamp,ingested_at=timestamp))
    billing.append(dict(next(r for r in billing if r['event_id']=='pay5')))
    return dict(provenance='100_percent_synthetic',as_of='2025-01-10T00:00:00+00:00',
                watermark='2025-01-10T00:00:00+00:00',cycles=cycles,members=members,learning=learning,billing=billing)


def timestamp(value):
    try:
        parsed=datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError,TypeError):raise ValueError('A timezone-aware timestamp is required') from None


def unique_events(rows):
    seen={}
    for row in rows:
        key=row.get('event_id')
        if not isinstance(key,str) or not key:raise ValueError('Missing event id')
        if key in seen and seen[key]!=row:raise ValueError('conflicting event id: '+key)
        seen[key]=row
    return list(seen.values())


def analyze(data):
    if data.get('provenance')!='100_percent_synthetic':raise ValueError('Only explicitly synthetic fixtures supported')
    as_of=timestamp(data['as_of']);watermark=timestamp(data['watermark'])
    if watermark>as_of:raise ValueError('watermark exceeds receipt cutoff')
    cycles=data['cycles'];members=data['members']
    cycle_ids=[r['cycle_id'] for r in cycles]
    if len(set(cycle_ids))!=len(cycle_ids):raise ValueError('Duplicate cycle id')
    cycle_keys=[(r['subscription_id'],timestamp(r['renewal_due_at'])) for r in cycles]
    if len(set(cycle_keys))!=len(cycle_keys):raise ValueError('Duplicate subscription renewal cycle')
    for row in cycles:
        if any(not isinstance(row.get(k),str) or not row[k] for k in ['cycle_id','subscription_id','payer_id']):
            raise ValueError('Missing cycle key')
        if row['plan_type'] not in ['individual','group']:raise ValueError('Unknown plan type')
        if timestamp(row['started_at'])>=timestamp(row['renewal_due_at']):raise ValueError('Invalid cycle interval')
        if row['cancel_requested_at'] is not None:timestamp(row['cancel_requested_at'])
    member_keys=[]
    for row in members:
        if row['cycle_id'] not in cycle_ids or not row['learner_id']:raise ValueError('Invalid membership key')
        if timestamp(row['valid_from'])>=timestamp(row['valid_to']):raise ValueError('Invalid membership interval')
        for old in members[:len(member_keys)]:
            if (old['cycle_id'],old['learner_id'])==(row['cycle_id'],row['learner_id']):
                if max(timestamp(old['valid_from']),timestamp(row['valid_from']))<min(timestamp(old['valid_to']),timestamp(row['valid_to'])):
                    raise ValueError('Overlapping membership intervals')
        member_keys.append((row['cycle_id'],row['learner_id']))
    billing=unique_events(data['billing']);learning=unique_events(data['learning'])
    for row in billing+learning:
        if row['cycle_id'] not in cycle_ids:raise ValueError('Unknown event cycle')
        occurred=timestamp(row['occurred_at']);received=timestamp(row['ingested_at'])
        if received<occurred:raise ValueError('Receipt before occurrence')
        if occurred<watermark and received>as_of:raise ValueError('Known late event contradicts watermark')
    transactions={}
    for row in billing:
        if row['kind'] not in ['settled','failed','refunded']:raise ValueError('Unsupported billing event')
        key=row['transaction_id']
        if not isinstance(key,str) or not key:raise ValueError('Missing transaction id')
        if key in transactions and transactions[key]!=row['cycle_id']:raise ValueError('transaction crosses cycles')
        transactions[key]=row['cycle_id']
        if row['kind']=='refunded' and not any(
            old['transaction_id']==key and old['kind']=='settled' and timestamp(old['occurred_at'])<=timestamp(row['occurred_at'])
            for old in billing):raise ValueError('Full refund without prior settlement')
    for row in learning:
        matches=[m for m in members if (m['cycle_id'],m['learner_id'])==(row['cycle_id'],row['learner_id'])
                 and timestamp(m['valid_from'])<=timestamp(row['occurred_at'])<timestamp(m['valid_to'])]
        if len(matches)!=1:raise ValueError('Learning event has no unique valid membership')
    schemas={
        'cycles':{'cycle_id':'VARCHAR','subscription_id':'VARCHAR','payer_id':'VARCHAR','plan_type':'VARCHAR',
                  'started_at':'TIMESTAMPTZ','renewal_due_at':'TIMESTAMPTZ','cancel_requested_at':'TIMESTAMPTZ'},
        'members':{'cycle_id':'VARCHAR','learner_id':'VARCHAR','valid_from':'TIMESTAMPTZ','valid_to':'TIMESTAMPTZ'},
        'learning':{'event_id':'VARCHAR','cycle_id':'VARCHAR','learner_id':'VARCHAR','occurred_at':'TIMESTAMPTZ','ingested_at':'TIMESTAMPTZ'},
        'billing':{'event_id':'VARCHAR','transaction_id':'VARCHAR','cycle_id':'VARCHAR','kind':'VARCHAR','occurred_at':'TIMESTAMPTZ','ingested_at':'TIMESTAMPTZ'}}
    with duckdb.connect() as db:
        db.execute("SET TimeZone='UTC'")
        for table,rows in [('cycles',cycles),('members',members),('learning',learning),('billing',billing)]:
            schema=schemas[table]
            db.execute(f"CREATE TABLE {table} ({','.join(k+' '+v for k,v in schema.items())})")
            if rows:db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in schema)})",[[r[k] for k in schema] for r in rows])
        cursor=db.execute((ROOT/'sql/subscription_bridge.sql').read_text(),{'as_of':as_of,'watermark':watermark})
        names=[c[0] for c in cursor.description]
        rows=[dict(zip(names,r)) for r in cursor.fetchall()]
    mature=sum(r['renewed'] is not None for r in rows);renewed=sum(r['renewed'] or 0 for r in rows)
    return dict(provenance='100_percent_synthetic',as_of=data['as_of'],watermark=data['watermark'],
                unit='subscription renewal cycle; not learner',mature_cycles=mature,renewed_cycles=renewed,
                renewal_rate=renewed/mature if mature else None,cycles=rows,
                interpretation='Contract demonstration only. Not observed retention, revenue, uplift or validated leading indicator.')

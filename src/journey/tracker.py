"""Rule-level issue history; identical observations never append duplicates."""
from copy import deepcopy

def update_issues(previous, checks, snapshot):
    records={x['rule_id']:deepcopy(x) for x in previous}
    for check in checks:
        rid=check['rule_id'];count=check['count'];old=records.get(rid)
        if old is None:
            records[rid]={**check,'issue_id':'OULAD-'+rid,'status':'open' if count else 'clear',
                          'first_seen':snapshot if count else None,
                          'history':[{'snapshot':snapshot,'count':count}]}
        elif old['count']!=count or old['severity']!=check['severity']:
            old.update(check);old['status']='open' if count else 'resolved'
            if count and old['first_seen'] is None:old['first_seen']=snapshot
            old['history'].append({'snapshot':snapshot,'count':count})
    return [records[k] for k in sorted(records)]

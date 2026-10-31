"""OULAD 전체 운영 비교: 단계별 직접 기록(A)과 일괄 실행·자동 채움(B)."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
EXPECTED_REPORT = '675dfa6fa3126da0ba74b5a4b4c4222afff4d950297703f3314788f9135a30db'
STAGES = ['source_load','quality','marts','overall','cohorts','temporal',
          'sensitivity','fault_lab','report_issues','crosscheck','build','verify']
STAGE_TITLES = dict(zip(STAGES, ['원본 해시·불러오기','품질 규칙 20개','기본·엄격 기준 분석표','전체 통계','개설기 22개 통계','시기 분리 검증','활동일·클릭 민감도','가상 장애 실습','보고서·분석표·이력','독립 대조','웹 자료 빌드','최종 일관성 검사']))
FIELD_LABELS = {'registration_required_null': '등록 필수키 결측', 'site_required_null': '콘텐츠 필수값 결측', 'course_required_null': '개설기 필수키 결측', 'course_invalid_length': '개설 기간 유효성', 'registration_unknown_course': '등록→개설기 참조', 'site_unknown_course': '콘텐츠→개설기 참조', 'event_exact_repeat': '동일 값 반복', 'event_daily_key_repeat': '일별 복합키 반복', 'registration_missing_date': '등록일 결측', 'event_after_withdrawal': '탈퇴일 이후 활동', 'event_after_course': '개설 기간 이후 활동', 'event_before_registration': '등록일 이전 활동', 'event_required_null': '활동 필수값 결측', 'event_nonpositive_click': '0 이하 클릭', 'event_unknown_student': '미등록 학습자 키', 'event_unknown_site': '콘텐츠 키 불일치', 'registration_inverted_dates': '등록·탈퇴 시점 역전', 'registration_key_repeat': '등록 키 유일성', 'site_key_repeat': '콘텐츠 키 유일성', 'course_key_repeat': '개설기 키 유일성'}
FIELD_LABELS.update({'source_files':'원본 파일 수','archive_sha256':'원본 압축파일 SHA-256','eligible':'분석 대상','w1_active':'첫 주 활동','w2_returned':'다음 주 재방문','strict_w1_active':'탈퇴 이후 제외: 첫 주 활동','strict_w2_returned':'탈퇴 이후 제외: 다음 주 재방문','repeat_bootstrap_draws':'반복 활동 비교: 유효 재표집 수','content_bootstrap_draws':'콘텐츠 비교: 유효 재표집 수','first_day_strata':'첫 활동일 집단 수','source_type':'자료 유형','report_sha256':'보고서 SHA-256','mart_rows':'분석표 행 수','issue_records':'이슈 수','issue_history_entries':'이슈 이력 수','enrollments_compared':'독립 대조 행 수','fields_compared':'독립 대조 항목 수','mismatched_rows':'불일치 행 수','release':'빌드 상태','consistency':'일관성 결과'})
PROVENANCES = ['human_self_reported','developer_synthetic']
OUTPUTS = ['reports/report.json','work/enrollment_mart.csv','reports/issues.json',
           'reports/crosscheck.json','web/data/report.json','web/data/operations.json',
           'web/data/release.json','data/synthetic/source_ledger.csv','data/synthetic/delivery.csv']


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def hashes(root, paths):
    return {name:digest(root/name) for name in sorted(paths)}


def assert_digests(root, expected):
    for name, value in expected.items():
        if not (root/name).is_file() or digest(root/name)!=value:
            raise ValueError('Fixed digest mismatch: '+name)


def fingerprint():
    paths=['requirements.txt']
    for folder in ['scripts','src','sql']:
        paths.extend(str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*')
                     if p.is_file() and p.suffix in ['.py','.sql'])
    return {'code_sha256':hashes(ROOT, paths), 'python':platform.python_version(),
            'platform':platform.platform(), 'packages':{p:importlib.metadata.version(p)
            for p in ['duckdb','numpy','pandas','scipy']}}


def next_slot(rows):
    schedule=[('practice',1,'A'),('practice',2,'B')]+[('measured',i,c) for i,c in enumerate('ABBAAB',1)]
    for phase,slot,condition in schedule:
        if not any(r['status']=='complete' and (r['phase'],r['slot'],r['condition'])==(phase,slot,condition) for r in rows):
            return phase,slot,condition
    return None


def parse_field(raw, expected):
    if isinstance(expected,str): value=raw.strip()
    else:
        try: value=json.loads(raw,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        except (ValueError,TypeError): raise ValueError('표시된 형식의 값을 입력하세요. 숫자는 쉼표 없이 입력하며 NaN·무한대는 허용하지 않습니다') from None
    if type(value) is not type(expected) or value!=expected:
        raise ValueError('입력값이 표시된 결과와 다릅니다')
    if isinstance(value,float) and not math.isfinite(value):raise ValueError('Non-finite value')
    return value


def fields_for(stage,p):
    if stage=='source_load':return p
    if stage=='quality':return {x['rule_id']:x['count'] for x in p['checks']}
    if stage=='overall':return {k:p[k] for k in ['eligible','w1_active','w2_returned']} | {
        'repeat_bootstrap_draws':p['repeat_comparison']['valid_draws'],
        'content_bootstrap_draws':p['content_comparison']['valid_draws']}
    if stage=='cohorts':return {f"{c['module']}_{c['term']}_eligible":c['eligible'] for c in p['cohorts']}
    if stage=='temporal':return {f"{c['id']}_{k}":c[k] for c in p['temporal'] for k in ['eligible','w1_active','w2_returned']}
    if stage=='sensitivity':return {'first_day_strata':len(p['first_day_strata']),
        **{f"click_{c['threshold']}_raw_vs_max_changed":c['raw_vs_max_changed'] for c in p['click_sensitivity']},
        **{f"transition_{c['w1']}_{c['w2']}":c['n'] for c in p['transition']}}
    if stage=='fault_lab':return {'source_type':p['source_type'],**{x['rule_id']:x['count'] for x in p['issues']}}
    if stage=='crosscheck':return {'enrollments_compared':p['enrollments_compared'],
        'fields_compared':len(p['fields_compared']),'mismatched_rows':p['mismatched_rows']}
    return p


def show_review(stage, payload, path):
    fields=fields_for(stage,payload)
    print(f'\n[{STAGES.index(stage)+1}/12] {STAGE_TITLES[stage]} — 확인·기록 {len(fields)}항목')
    print('전체 계산 결과 파일:',path)
    print('아래 항목과 비교 요약을 확인하세요. 전체 JSON을 모두 읽는 과제는 아닙니다.')
    for name,value in fields.items():
        print(f'  {FIELD_LABELS.get(name,name)} [{name}]: {value}')
    def comparison(c):
        if c['difference'] is None:return '비교 불가'
        interval='계산 불가' if c['ci'] is None else f"{100*c['ci'][0]:.3f}~{100*c['ci'][1]:.3f}"
        return f"차이 {100*c['difference']:.3f}%p / 95% 구간 {interval}%p"
    summaries=[]
    if stage=='overall':summaries=[('전체',payload)]
    elif stage=='cohorts':summaries=[(f"{c['module']}-{c['term']}",c) for c in payload['cohorts']]
    elif stage=='temporal':summaries=[(c['label'],c) for c in payload['temporal']]
    for label,summary in summaries:
        print(f"  {label}: 반복 활동 {comparison(summary['repeat_comparison'])}; 콘텐츠 {comparison(summary['content_comparison'])}")
    if stage=='sensitivity':
        for item in payload['first_day_strata']:
            print(f"  첫 활동 {item['first_day']}일: {comparison(item['comparison'])}")
    if stage=='quality':
        blocking=[r['rule_id'] for r in payload['checks'] if r['count'] and r['severity']=='block']
        print('  집계 차단 규칙:',', '.join(blocking) if blocking else '검출 없음 (검토 필요 규칙과 구분)')
    if stage=='fault_lab':
        for item in payload['stages']:
            print(f"  {item['label']}: 첫 주 {item['w1']}, 다음 주 {item['w2']}, 누락 {item['missing_events']}, {item['gate']}")


class StageRecorder:
    def __init__(self,root,condition,event,review,advance=None,expected_stages=None):
        self.root,self.condition,self.event,self.review=root,condition,event,review
        self.expected_stages=expected_stages
        self.batch_reviewed=False
        self.advance=advance
        self.seen=[];self.pending=None;self.machine_seconds=0.;self.artifacts=[]

    def before(self,stage):
        if stage in self.seen:raise ValueError('Stage already executed: '+stage)
        if self.pending is not None:raise ValueError('Previous stage not finished')
        if self.condition=='A' and self.advance:self.advance(stage)
        self.pending=stage;self.seen.append(stage)
        self.event('machine_start',stage=stage)
        self.started=time.perf_counter()

    def after(self,stage,payload):
        if self.pending!=stage:raise ValueError('Unexpected stage completion')
        elapsed=time.perf_counter()-self.started;self.machine_seconds+=elapsed
        self.event('machine_finish',stage=stage,seconds=elapsed)
        self.pending=None
        path=self.root/'stages'/f'{len(self.seen):02d}-{stage}.json'
        write_json(path,payload)
        if self.expected_stages is not None:
            name=str(path.relative_to(self.root))
            if name not in self.expected_stages:raise ValueError('Unexpected stage digest: '+name)
            assert_digests(self.root,{name:self.expected_stages[name]})
        self.artifacts.append((stage,payload))
        if self.condition=='A':self.review(stage,payload)

    def review_batch(self):
        if self.batch_reviewed:raise ValueError('Batch review already completed')
        self.batch_reviewed=True
        if self.condition=='B':
            for stage,payload in self.artifacts:self.review(stage,payload)


def pipeline(root,recorder):
    from scripts import analyze,crosscheck,build,verify
    analyze.main(ROOT=root,checkpoint=recorder)
    for stage,module,function in [('crosscheck',crosscheck,'main'),('build',build,'build'),('verify',verify,'main')]:
        recorder.before(stage)
        original=module.ROOT
        try:
            module.ROOT=root
            getattr(module,function)()
        finally:module.ROOT=original
        if stage=='crosscheck':payload=json.loads((root/'reports/crosscheck.json').read_text())
        elif stage=='build':payload={'report_sha256':digest(root/'web/data/report.json'),'release':'built'}
        else:payload={'report_sha256':digest(root/'reports/report.json'),'consistency':'PASS'}
        recorder.after(stage,payload)
    if recorder.seen!=STAGES:raise ValueError('Incomplete or reordered pipeline')
    if digest(root/'reports/report.json')!=EXPECTED_REPORT:raise ValueError('Reference report digest mismatch')


def prepare(root, snapshot, raw, create=True):
    if create:root.mkdir(parents=True,exist_ok=False)
    for name in ['reports','sql']:
        shutil.copytree(snapshot/name,root/name)
    shutil.copy2(snapshot/'README.md',root/'README.md')
    (root/'data').mkdir();(root/'work').mkdir();(root/'web/data').mkdir(parents=True)
    shutil.copy2(snapshot/'data/manifest.json',root/'data/manifest.json')
    (root/'data/raw').symlink_to(raw,target_is_directory=True)


def initialize(study,raw,provenance):
    if provenance not in PROVENANCES:raise ValueError('provenance: human_self_reported 또는 developer_synthetic을 지정하세요')
    raw=raw.resolve()
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    assert_digests(raw,{n:m['sha256'] for n,m in manifest['files'].items()})
    study.mkdir(parents=True,exist_ok=False)
    snapshot=study/'snapshot';snapshot.mkdir()
    for name in ['reports','sql']:shutil.copytree(ROOT/name,snapshot/name)
    (snapshot/'data').mkdir();shutil.copy2(ROOT/'data/manifest.json',snapshot/'data/manifest.json')
    shutil.copy2(ROOT/'README.md',snapshot/'README.md')
    support=hashes(snapshot,[str(p.relative_to(snapshot)) for p in snapshot.rglob('*') if p.is_file()])
    config={'schema_version':1,'created_at':now(),'provenance':provenance,
            'schedule':{'practice':'AB','measured':'ABBAAB'},'raw_dir':str(raw),
            'fingerprint':fingerprint(),'snapshot_sha256':support,
            'source_sha256':{n:m['sha256'] for n,m in manifest['files'].items()},
            'expected_report_sha256':EXPECTED_REPORT}
    write_json(study/'protocol.json',config)
    baseline=study/'calibration'
    prepare(baseline,snapshot,raw)
    print('사전 검증 중: 전체 계산과 독립 대조를 실행합니다. 연습·측정 회차가 아닙니다.',flush=True)
    recorder=StageRecorder(baseline,'B',lambda *a,**k:None,lambda *a:None)
    pipeline(baseline,recorder)
    config['expected_outputs']=hashes(baseline,OUTPUTS)
    config['expected_stages']=hashes(baseline,[str(p.relative_to(baseline)) for p in (baseline/'stages').glob('*.json')])
    config['review_fields_total']=sum(len(fields_for(stage,payload)) for stage,payload in recorder.artifacts)
    write_json(study/'protocol.json',config)
    print('절차가 고정되었습니다. run 명령을 반복하세요: 연습 A/B, 본 측정 A B B A A B.')


@contextmanager
def lock(study):
    with (study/'.lock').open('a') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('다른 측정 명령이 실행 중입니다') from None
        try:yield
        finally:fcntl.flock(handle,fcntl.LOCK_UN)


def records(study):
    rows=[]
    for path in sorted((study/'attempts').glob('*/record.json')):
        try:
            row=json.loads(path.read_text())
            if row['provenance'] not in PROVENANCES:raise ValueError()
            if row['schema_version']!=1 or row['phase'] not in ['practice','measured']:raise ValueError()
            if type(row['slot']) is not int:raise ValueError()
            if type(row['attempt']) is not int or row['attempt']<1:raise ValueError()
            if type(row['invalid_inputs']) is not int or row['invalid_inputs']<0:raise ValueError()
            schedule='AB' if row['phase']=='practice' else 'ABBAAB'
            if not 1<=row['slot']<=len(schedule) or row['condition']!=schedule[row['slot']-1]:raise ValueError()
            if row['status'] not in ['running','complete','aborted','invalid']:raise ValueError()
            for name in ['elapsed_seconds','pause_seconds','machine_seconds','unpaused_seconds','non_machine_unpaused_seconds']:
                value=row.get(name)
                if value is not None and (type(value) not in [int,float] or not math.isfinite(value) or value<0):raise ValueError()
            if row['status']=='complete':
                if row.get('elapsed_seconds') is None:raise ValueError()
                reviews=row['review_records']
                if [r['stage'] for r in reviews]!=STAGES or not all(r['confirmed'] is True for r in reviews):raise ValueError()
                for review in reviews:
                    if set(review['entered'])!=set(review['expected']):raise ValueError()
                    for name,value in review['expected'].items():
                        entry=review['entered'][name]
                        if type(entry['value']) is not type(value) or entry['value']!=value:raise ValueError()
                        if row['condition']=='A' and entry.get('correct') is not True:raise ValueError()
            rows.append(row)
        except (KeyError,TypeError,ValueError,IndexError):
            raise ValueError('Invalid study record: '+str(path)) from None
    return rows


def recover_attempts(study,config):
    """Preserve incomplete setup/start records; never manufacture missing durations."""
    records(study)
    for folder in sorted((study/'attempts').glob('*')):
        if not folder.is_dir():continue
        path=folder/'record.json'
        if not path.exists():
            match=re.fullmatch(r'(\d+)-(practice|measured)-(\d+)-([AB])',folder.name)
            if not match:raise ValueError('알 수 없는 시도 폴더: '+folder.name)
            number,phase,slot,condition=match.groups()
            row={'schema_version':1,'provenance':config['provenance'],
                 'protocol_sha256':digest(study/'protocol.json'),'attempt':int(number),
                 'phase':phase,'slot':int(slot),'condition':condition,'status':'running',
                 'review_records':[],'invalid_inputs':0}
        else:row=json.loads(path.read_text())
        if row['status']=='running':
            row.update(status='aborted',reason='이전 실행 또는 폴더 준비가 종료 기록 없이 끝났습니다. 소요 시간은 알 수 없습니다',
                       recovered_at=now(),elapsed_seconds=None,pause_seconds=None,machine_seconds=None,
                       unpaused_seconds=None,non_machine_unpaused_seconds=None)
            write_json(path,row)
            with (folder/'events.jsonl').open('a') as log:
                log.write(json.dumps({'at':now(),'event':'interruption_recovered','duration_known':False})+'\n')
    records(study)


def run_round(study):
    config=json.loads((study/'protocol.json').read_text())
    if config.get('provenance') not in PROVENANCES:raise ValueError('자료 유형(provenance)이 지정되지 않았습니다')
    if config.get('schema_version')!=1 or config.get('schedule')!={'practice':'AB','measured':'ABBAAB'}:
        raise ValueError('Unsupported protocol schema or schedule')
    if 'expected_outputs' not in config:raise ValueError('사전 검증이 완료되지 않았습니다. 새 study 폴더에서 init을 실행하세요')
    if config['fingerprint']!=fingerprint():raise ValueError('코드 또는 Python 환경이 바뀌었습니다. 새 study 폴더에서 init을 실행하세요')
    assert_digests(study/'snapshot',config['snapshot_sha256'])
    # Preflight hashing is setup time; source_load repeats hashing inside both timed conditions.
    assert_digests(Path(config['raw_dir']),config['source_sha256'])
    recover_attempts(study,config)
    rows=records(study);slot=next_slot(rows)
    if slot is None:print('예정된 8회가 모두 완료되어 추가 회차를 만들지 않았습니다.');return
    phase,number,condition=slot
    attempt=max((r['attempt'] for r in rows),default=0)+1;folder=study/'attempts'/f'{attempt:03d}-{phase}-{number}-{condition}'
    folder.mkdir(parents=True,exist_ok=False)
    row={'schema_version':1,'provenance':config['provenance'],'protocol_sha256':digest(study/'protocol.json'),'attempt':attempt,
         'phase':phase,'slot':number,'condition':condition,'status':'running','prepared_at':now(),
         'review_records':[],'invalid_inputs':0}
    log=folder/'events.jsonl'
    def event(kind,**kw):
        with log.open('a') as f:f.write(json.dumps({'at':now(),'event':kind,**kw},ensure_ascii=False,allow_nan=False)+'\n')
    paused=0.
    def prompt(message):
        nonlocal paused
        while True:
            answer=input(message).strip()
            if answer==':abort':raise KeyboardInterrupt
            if answer==':pause':
                start=time.perf_counter();event('pause_start')
                try:input('일시정지 중입니다. Enter로 재개: ')
                finally:
                    duration=time.perf_counter()-start;paused+=duration;event('pause_finish',seconds=duration)
                continue
            return answer
    def review(stage,payload):
        show_review(stage,payload,folder/'stages'/f'{STAGES.index(stage)+1:02d}-{stage}.json')
        fields=fields_for(stage,payload)
        record={'stage':stage,'expected':fields,'entered':{},'confirmed':False}
        row['review_records'].append(record)
        for name,value in fields.items():
            if condition=='A':
                raw=prompt(f'기록 {name} = ')
                record['entered'][name]={'raw':raw,'correct':False}
                event('manual_entry',stage=stage,field=name,raw=raw)
                try:parsed=parse_field(raw,value)
                except ValueError:
                    row['invalid_inputs']+=1
                    write_json(folder/'record.json',row)
                    raise
                record['entered'][name].update(value=parsed,correct=True)
            else:record['entered'][name]={'value':value,'prefilled':True}
        print('기록 완료. 위 결과와 방금 입력한 값 또는 자동 채움 값을 확인하세요.')
        answer=prompt('A/B 공통 확인: 표시된 항목과 비교 요약을 확인했으면 reviewed 입력: ')
        event('review_confirmation',stage=stage,raw=answer)
        if answer!='reviewed':raise ValueError('확인 문구 reviewed가 입력되지 않았습니다')
        record['confirmed']=True
        write_json(folder/'record.json',row)
    def advance(stage):
        answer=prompt(f'다음 단계 {stage} 실행: run 입력: ')
        event('stage_command',stage=stage,raw=answer)
        if answer!='run':raise ValueError('실행 문구 run이 입력되지 않았습니다')
    recorder=StageRecorder(folder,condition,event,review,advance,config['expected_stages'])
    write_json(folder/'record.json',row)
    log.touch(exist_ok=False)
    event('attempt_preparing')
    print(f'다음: {phase} {number}회, {condition} 방식. A=단계 실행·직접 기록, B=일괄 실행·자동 채움.')
    print(f"자료 유형: {config['provenance']} / 12단계 / 공통 확인 {config['review_fields_total']}항목")
    print('확인 항목은 같습니다. :pause=일시정지, :abort=중단. 잘못 입력하면 이번 시도는 무효로 보존되고 같은 회차를 새로 시작합니다.')
    print('설치·준비·아래 대기는 측정에서 제외합니다. start 입력 직후부터 시간을 잽니다.')
    started=None
    try:
        prepare(folder,study/'snapshot',Path(config['raw_dir']),create=False)
        if prompt('준비됐으면 start 입력: ')!='start':raise ValueError('시작 문구 start가 입력되지 않았습니다')
        paused=0.
        started=time.perf_counter();row['started_at']=now();event('round_start',phase=phase,slot=number,condition=condition)
        write_json(folder/'record.json',row)
        pipeline(folder,recorder)
        assert_digests(folder,config['expected_outputs'])
        assert_digests(folder,config['expected_stages'])
        recorder.review_batch()
        if config['fingerprint']!=fingerprint():raise ValueError('Code/runtime changed during round')
        assert_digests(folder,config['expected_outputs'])
        assert_digests(folder,config['expected_stages'])
        row['status']='complete'
    except (KeyboardInterrupt,EOFError):
        row.update(status='aborted',reason='사용자 중단 또는 입력 종료')
    except (Exception,SystemExit) as error:
        row.update(status='invalid',reason=f'{type(error).__name__}: {error}')
    finally:
        elapsed=time.perf_counter()-started if started is not None else None
        # An interrupted machine interval remains machine waiting, not human work.
        if recorder.pending is not None:
            duration=time.perf_counter()-recorder.started
            recorder.machine_seconds+=duration
            event('machine_interrupted',stage=recorder.pending,seconds=duration)
        row.update(finished_at=now(),elapsed_seconds=elapsed,pause_seconds=paused,
                   machine_seconds=recorder.machine_seconds,
                   unpaused_seconds=None if elapsed is None else max(0.,elapsed-paused),
                   non_machine_unpaused_seconds=None if elapsed is None else max(0.,elapsed-paused-recorder.machine_seconds),
                   output_sha256=hashes(folder,[name for name in OUTPUTS if (folder/name).is_file()]))
        event('round_finish',status=row['status'],elapsed_seconds=elapsed)
        write_json(folder/'record.json',row)
    print(f"{row['status']}: {folder / 'record.json'}")
    if row['status']!='complete':print('시도를 보존했습니다. 다음 run은 같은 예정 회차를 새로 실행합니다. 사유:',row.get('reason'))


def audit_study(study):
    """Read-only validation before sharing; no timing or effectiveness inference."""
    config=json.loads((study/'protocol.json').read_text())
    if config.get('provenance') not in PROVENANCES:raise ValueError('Invalid protocol provenance')
    if set(config['expected_outputs'])!=set(OUTPUTS):raise ValueError('Incomplete output digest contract')
    if config['fingerprint']!=fingerprint():raise ValueError('Code/runtime fingerprint mismatch')
    assert_digests(study/'snapshot',config['snapshot_sha256'])
    assert_digests(Path(config['raw_dir']),config['source_sha256'])
    assert_digests(study/'calibration',config['expected_outputs'])
    assert_digests(study/'calibration',config['expected_stages'])
    rows=records(study);prior=[]
    for path,row in zip(sorted((study/'attempts').glob('*/record.json')),rows):
        folder=path.parent
        if row['provenance']!=config['provenance'] or row['protocol_sha256']!=digest(study/'protocol.json'):
            raise ValueError('Record/protocol provenance or digest mismatch')
        if next_slot(prior)!=(row['phase'],row['slot'],row['condition']):raise ValueError('Attempt schedule mismatch')
        prior.append(row)
        assert_digests(folder,row.get('output_sha256',{}))
        events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
        for event in events:
            datetime.fromisoformat(event['at'])
            for name in ['seconds','elapsed_seconds']:
                value=event.get(name)
                if value is not None and (type(value) not in [int,float] or not math.isfinite(value) or value<0):
                    raise ValueError('Invalid event timing')
        if row['status']!='complete':continue
        assert_digests(folder,config['expected_outputs']);assert_digests(folder,config['expected_stages'])
        if [e['stage'] for e in events if e['event']=='machine_start']!=STAGES:raise ValueError('Stage start events mismatch')
        if [e['stage'] for e in events if e['event']=='machine_finish']!=STAGES:raise ValueError('Stage finish events mismatch')
        commands=[e['stage'] for e in events if e['event']=='stage_command' and e['raw']=='run']
        if commands!=(STAGES if row['condition']=='A' else []):raise ValueError('Stage command events mismatch')
        confirmations=[e['stage'] for e in events if e['event']=='review_confirmation' and e['raw']=='reviewed']
        if confirmations!=STAGES:raise ValueError('Review events mismatch')
        started=[i for i,e in enumerate(events) if e['event']=='round_start']
        finished=[i for i,e in enumerate(events) if e['event']=='round_finish']
        if len(started)!=1 or len(finished)!=1 or started[0]>=finished[0] or events[finished[0]]['status']!='complete':
            raise ValueError('Round events mismatch')
        timed=events[started[0]:finished[0]+1]
        machine=sum(e['seconds'] for e in timed if e['event']=='machine_finish')
        pause=sum(e['seconds'] for e in timed if e['event']=='pause_finish')
        elapsed=row['elapsed_seconds']
        if any(abs(a-b)>1e-6 for a,b in [(machine,row['machine_seconds']),(pause,row['pause_seconds']),
                (elapsed,events[finished[0]]['elapsed_seconds']),
                (max(0.,elapsed-pause),row['unpaused_seconds']),
                (max(0.,elapsed-pause-machine),row['non_machine_unpaused_seconds'])]):
            raise ValueError('Record/event timing mismatch')
        if elapsed+1e-6<pause+machine:raise ValueError('Impossible record timing')
        manual=[]
        for index,review in enumerate(row['review_records'],1):
            payload=json.loads((folder/'stages'/f"{index:02d}-{review['stage']}.json").read_text())
            if review['expected']!=fields_for(review['stage'],payload):raise ValueError('Review fields differ from actual stage')
            if row['condition']=='A':
                for name,expected in review['expected'].items():
                    raw=review['entered'][name]['raw'];parse_field(raw,expected)
                    manual.append((review['stage'],name,raw))
        if manual!=[(e['stage'],e['field'],e['raw']) for e in events if e['event']=='manual_entry']:
            raise ValueError('Manual entry events mismatch')
    return {'schema_version':1,'provenance':config['provenance'],'audit':'PASS',
            'completed_measured':sum(r['status']=='complete' and r['phase']=='measured' for r in rows),
            'invalid_attempts':sum(r['status']=='invalid' for r in rows),
            'aborted_attempts':sum(r['status']=='aborted' for r in rows),
            'next':next_slot(rows),'attempts':[{k:r.get(k) for k in ['attempt','phase','slot','condition','status',
              'elapsed_seconds','pause_seconds','machine_seconds','unpaused_seconds','non_machine_unpaused_seconds','invalid_inputs']} for r in rows]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['init','run','status','audit'])
    parser.add_argument('--study',type=Path,default=ROOT/'work/full-operations')
    parser.add_argument('--provenance',choices=PROVENANCES,help='init 필수: 실제 사람 기록 또는 개발자 가상 검증')
    parser.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw')
    args=parser.parse_args();study=args.study.resolve()
    try:
        if args.command=='init':initialize(study,args.raw_dir,args.provenance)
        else:
            if not (study/'protocol.json').is_file():raise ValueError('먼저 init으로 절차를 고정하세요')
            with lock(study):
                if args.command=='run':run_round(study)
                elif args.command=='audit':
                    print(json.dumps(audit_study(study),ensure_ascii=False,indent=2))
                else:
                    rows=records(study)
                    for r in rows:print(f"{r['attempt']} | {r['provenance']} | {r['phase']} {r['slot']} {r['condition']} | {r['status']} | {r.get('unpaused_seconds')}초")
                    print('다음 회차:',next_slot(rows))
                    print('원본·기록·시간 검증은 audit 명령으로 실행하세요.')
    except (ValueError,FileExistsError) as error:parser.exit(2,str(error)+'\n')


if __name__=='__main__':main()

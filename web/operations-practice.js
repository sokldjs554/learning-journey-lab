'use strict';
(() => {
  const SHA = '675dfa6fa3126da0ba74b5a4b4c4222afff4d950297703f3314788f9135a30db';
  const IDS = ['event_exact_repeat','registration_missing_date','event_unknown_site'];
  const PLAN = ['A','B','A','B','B','A','A','B'];
  const $ = id => document.getElementById(id);
  let source, step=0, running=false, paused=false, current=null, segmentStart=0, segmentKind='active', startTime=0, loadMs=0;
  const rounds=[];
  let environment, origin;
  const mode=()=>PLAN[step];
  const measured=()=>step>=2;
  const ready=()=>Boolean(source && $('origin').value && $('context-notes').value.trim() && $('scope-confirm').checked);
  const ms=()=>performance.now()-startTime;
  function closeSegment(kind) {
    const end=ms();current.timing.segments.push({kind:segmentKind,start_ms:segmentStart,end_ms:end});segmentStart=end;segmentKind=kind;
  }
  function label(){
    $('round-label').textContent=step<2?`시간을 재지 않는 연습 ${step+1}/2 · ${mode()==='A'?'A 수작업':'B 자동 채움'}`:step<8?`측정 ${step-1}/6 · ${mode()==='A'?'A 수작업':'B 자동 채움'}`:'6회 측정 종료';
  }
  function buildRows(){
    $('source-rows').replaceChildren();$('output-rows').replaceChildren();
    source.forEach((row,i)=>{
      const tr=document.createElement('tr');
      [row.rule_id,row.count.toLocaleString('en-US'),row.severity].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td)});$('source-rows').append(tr);
      const div=document.createElement('div');div.className='output-row';
      // Rule IDs are fixed constants, not imported HTML.
      div.innerHTML=`<strong>${IDS[i]}</strong><label for="count-${i}">건수<input id="count-${i}" type="number" min="0" step="1" inputmode="numeric"></label><label for="severity-${i}">심각도<select id="severity-${i}"><option value="">선택</option><option value="review">review</option><option value="block">block</option></select></label><label for="status-${i}">상태<select id="status-${i}"><option value="">선택</option><option value="open">open</option><option value="clear">clear</option></select></label><label class="check" for="reviewed-${i}"><input id="reviewed-${i}" type="checkbox">이 행의 세 필드를 원문 및 상태 규칙과 대조했습니다.</label>`;
      $('output-rows').append(div);
    });
  }
  function score(outputs){
    let omissions=0,errors=0,unreviewed=0;
    outputs.forEach((r,i)=>{for(const field of ['count','severity','status']){const want=field==='status'?(source[i].count>0?'open':'clear'):source[i][field];if(r[field]===null || r[field]==='')omissions++;else if(r[field]!==want)errors++}if(!r.reviewed)unreviewed++});
    return {omissions,errors,unreviewed,valid:omissions+errors+unreviewed===0};
  }
  function start(){
    if(running || step>=8 || !ready())return;
    if(!environment){origin=$('origin').value;environment={user_agent:navigator.userAgent,viewport:`${innerWidth}x${innerHeight}`,context_notes:$('context-notes').value.trim()};$('setup').disabled=true;}
    buildRows();$('task').hidden=false;$('result').textContent='';$('next').hidden=true;
    startTime=performance.now();segmentStart=0;segmentKind='active';
    current={mode:mode(),phase:measured()?'measured':'practice',machine_generation_ms:0,timing:measured()?{started_at:new Date().toISOString(),segments:[]}:null};
    running=true;paused=false;
    if(mode()==='B'){
      const start=performance.now();source.forEach((r,i)=>{$(`count-${i}`).value=r.count;$(`severity-${i}`).value=r.severity;$(`status-${i}`).value=r.count>0?'open':'clear'});current.machine_generation_ms=performance.now()-start;
    }
    $('output-fields').disabled=false;$('start').disabled=true;$('finish').disabled=false;$('pause').disabled=!measured();$('pause').textContent='일시정지';
    $('run-status').textContent=measured()?'작업 구간 기록 중. 방해가 생기면 일시정지를 누르세요.':'연습 중 · 시간은 기록하지 않습니다.';
    $(`count-0`).focus();
  }
  function setPause(hidden=false){
    if(!running || !measured())return;
    if(!paused){closeSegment(hidden?'hidden':'manual_pause');paused=true;}
    else if(hidden && segmentKind!=='hidden')closeSegment('hidden');
    $('output-fields').disabled=true;$('finish').disabled=true;$('pause').textContent='재개';$('run-status').textContent='정지 중 · 제외 구간으로 기록합니다. 돌아오면 재개를 누르세요.';
  }
  function resume(){
    if(!running || !paused || document.hidden)return;
    closeSegment('active');paused=false;$('output-fields').disabled=false;$('finish').disabled=false;$('pause').textContent='일시정지';$('run-status').textContent='작업 구간 기록 중.';
  }
  function finish(){
    if(!running || paused)return;
    if(measured()){
      closeSegment('active');current.timing.finished_at=new Date().toISOString();
      const segments=current.timing.segments;current.timing.elapsed_ms=segments.at(-1).end_ms;current.timing.task_interval_ms=segments.filter(s=>s.kind==='active').reduce((n,s)=>n+s.end_ms-s.start_ms,0);current.timing.excluded_ms=current.timing.elapsed_ms-current.timing.task_interval_ms;
    }
    current.outputs=source.map((r,i)=>{const value=$(`count-${i}`).value;return {rule_id:r.rule_id,count:value===''?null:Number(value),severity:$(`severity-${i}`).value,status:$(`status-${i}`).value,reviewed:$(`reviewed-${i}`).checked}});
    Object.assign(current,score(current.outputs));rounds.push(current);running=false;
    $('output-fields').disabled=true;$('finish').disabled=true;$('pause').disabled=true;$('run-status').textContent='완료 시점의 입력을 고정했습니다.';
    $('result').textContent=`${current.valid?'유효':'무효'} · 누락 ${current.omissions}개 필드 · 기록 오류 ${current.errors}개 필드 · 대조 미확인 ${current.unreviewed}개 행`;
    const tr=document.createElement('tr');[measured()?`측정 ${step-1}`:'연습',mode(),current.timing?`${(current.timing.task_interval_ms/1000).toFixed(2)}초`:'시간 미기록',current.timing?`${(current.timing.excluded_ms/1000).toFixed(2)}초`:'—',mode()==='B'?`${current.machine_generation_ms.toFixed(2)}ms`:'—',current.valid?'유효':'무효'].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});$('history-rows').append(tr);$('history').hidden=false;
    if(step===7){step++;label();$('export').disabled=false;$('export').focus();$('export-note').textContent=`${origin==='developer_synthetic'?'개발자 테스트 기록입니다. 사람 측정으로 사용할 수 없습니다.':'참여자가 직접 수행했다고 선택한 기록입니다. 신원·주의 집중을 인증하지 않습니다.'} 파일을 내려받고 검증 스크립트로 일관성을 확인하세요.`;}
    else{$('next').hidden=false;$('next').textContent=!measured() && !current.valid?'같은 연습 다시':'다음 단계';$('next').focus();}
  }
  function next(){
    if(running)return;
    if(measured() || current.valid)step++;
    $('task').hidden=true;$('next').hidden=true;$('result').textContent='';$('start').disabled=false;$('run-status').textContent='준비되면 시작을 누르세요.';label();$('start').focus();
  }
  function exportJSON(){
    if(step!==8)return;
    const payload={schema_version:1,protocol:'three-rule-transfer-v1',snapshot_sha256:SHA,origin,environment,report_load_ms:loadMs,rounds};
    const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`operations-${origin}-${new Date().toISOString().replace(/[:.]/g,'-')}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function load(){
    source=null;$('loading').hidden=false;$('load-error').hidden=true;$('workspace').hidden=true;$('start').disabled=true;
    try{
      const started=performance.now(), response=await fetch('data/report.json');if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const raw=await response.arrayBuffer();const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),n=>n.toString(16).padStart(2,'0')).join('');if(digest!==SHA)throw new Error('고정 보고서 SHA256 불일치');
      const report=JSON.parse(new TextDecoder().decode(raw));const checks=report?.quality?.checks;if(!Array.isArray(checks))throw new Error('검사 결과 없음');
      source=IDS.map(id=>{const rows=checks.filter(r=>r.rule_id===id);if(rows.length!==1 || !Number.isSafeInteger(rows[0].count) || rows[0].count<0 || !['review','block'].includes(rows[0].severity))throw new Error('규칙 값 또는 키 오류');return rows[0]});
      loadMs=performance.now()-started;$('snapshot').textContent=`보고서 SHA256 ${SHA} · 최초 읽기·검증 ${loadMs.toFixed(2)}ms (반복 작업 구간과 별도)`;$('workspace').hidden=false;label();$('start').disabled=!ready();
    }catch(error){source=null;$('error-detail').textContent=error.message;$('load-error').hidden=false;}finally{$('loading').hidden=true;}
  }
  $('start').addEventListener('click',start);$('pause').addEventListener('click',()=>paused?resume():setPause());$('finish').addEventListener('click',finish);$('next').addEventListener('click',next);$('export').addEventListener('click',exportJSON);$('retry').addEventListener('click',load);
  $('setup').addEventListener('input',()=>{$('start').disabled=!ready()});
  document.addEventListener('visibilitychange',()=>{if(!running || !measured())return;if(document.hidden)setPause(true);else if(paused && segmentKind==='hidden')closeSegment('manual_pause')});
  window.addEventListener('beforeunload',event=>{if(rounds.length || running){event.preventDefault();event.returnValue=''}});
  load();
})();

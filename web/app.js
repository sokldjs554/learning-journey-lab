'use strict';
const $=id=>document.getElementById(id);
const number=n=>new Intl.NumberFormat('ko-KR').format(n);
const percent=n=>n==null?'비교 불가':`${(n*100).toFixed(1)}%`;
const pp=n=>n==null?'비교 불가':`${n>=0?'+':''}${(n*100).toFixed(1)}%p`;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let report;
const ruleText={
 registration_required_null:['등록 필수키 결측','익명 수강 건이 분모에 들어가지 않도록 집계 전에 차단.'],
 site_required_null:['콘텐츠 필수값 결측','식별 키와 콘텐츠 유형의 결측을 차단.'],
 course_required_null:['개설기 필수키 결측','개설기 식별 불가 시 집계 차단.'],
 course_invalid_length:['개설 기간 유효성','결측 또는 0 이하 길이는 집계 전에 차단.'],
 registration_unknown_course:['등록→개설기 참조','존재하지 않는 개설기가 INNER JOIN에서 사라지기 전에 차단.'],
 site_unknown_course:['콘텐츠→개설기 참조','콘텐츠가 참조하는 개설기의 존재 여부 확인.'],
 event_exact_repeat:['동일 값 반복','모든 값이 같은 초과 행. 수신 중복인지 반복 활동 집계인지 미확정. 임의 제거 대신 클릭 민감도를 제시하고 활동일 지표 사용.'],
 event_daily_key_repeat:['일별 복합키 반복','학습자·자료·개설기·날짜가 같은 초과 행. 행을 곧 이벤트로 해석하지 않음.'],
 registration_missing_date:['등록일 결측','분석 분모에서 제외. 등록일을 0으로 대체하지 않음.'],
 event_after_withdrawal:['탈퇴일 이후 활동','동기화 시차·등록 정의 등 원인 미확정. 기본 분석은 보존하고 등록 기간 제한 결과를 별도 비교.'],
 event_after_course:['개설 기간 이후 활동','복습 또는 추출 기준 가능성. 원본은 보존; 첫 28일 분석에 영향 없음.'],
 event_before_registration:['등록일 이전 활동','개강 전 음수 날짜 자체는 오류가 아님. 등록일보다 앞선 기록만 검사.'],
 event_required_null:['활동 필수값 결측','학습자·콘텐츠·개설기·날짜·클릭 수의 결측 검사.'],
 event_nonpositive_click:['0 이하 클릭','활동 지표에서 제외. 원천 정의와 수집 오류 확인 필요.'],
 event_unknown_student:['미등록 학습자 키','복합 등록 키와 일치하지 않는 행. 격리 및 집계 보류.'],
 event_unknown_site:['콘텐츠 키 불일치','개설기까지 포함한 콘텐츠 키 대조.'],
 registration_inverted_dates:['등록·탈퇴 시점 역전','탈퇴일이 등록일보다 빠른 기록 검사.'],
 registration_key_repeat:['등록 키 유일성','중복 차원 키가 있으면 JOIN 전에 실행 중단.'],
 site_key_repeat:['콘텐츠 키 유일성','중복 차원 키가 있으면 JOIN 전에 실행 중단.'],
 course_key_repeat:['개설기 키 유일성','중복 차원 키가 있으면 JOIN 전에 실행 중단.']};
function renderScope(value){
 const c=value==='all'?report.overall:report.cohorts.find(c=>`${c.module}|${c.term}`===value);
 if(!c)return;
 $('eligible').textContent=number(c.eligible);$('w1').textContent=number(c.w1_active);$('return-rate').textContent=percent(c.return_rate);
 $('return-fraction').textContent=`${number(c.w2_returned)} / ${number(c.w1_active)} 수강 건`;
 const comp=c.repeat_comparison;
 $('comparison-bars').innerHTML=[['1일 활동',comp.control,'secondary'],['2일+ 활동',comp.exposed,'']].map(([label,g,cls])=>`<div class="bar-row"><span>${label}<small>n=${number(g.n)}</small></span><div class="bar-track" aria-hidden="true"><div class="bar-fill ${cls}" style="width:${g.rate==null?0:g.rate*100}%"></div></div><strong>${percent(g.rate)}</strong></div>`).join('');
 $('difference').textContent=pp(comp.difference);$('difference-ci').textContent=comp.ci?`95% 군집 부트스트랩 구간 ${pp(comp.ci[0])} ~ ${pp(comp.ci[1])}`:'비교 가능한 두 그룹 부족';
 $('chart-scope').textContent=value==='all'?'전체 · 22개 개설기':value.replace('|',' · ');
 $('day-bars').innerHTML=c.days.map(d=>`<div class="day-col"><strong>${percent(d.rate)}</strong><div class="day-rect" style="height:${d.rate==null?0:d.rate*156}px" aria-hidden="true"></div><span class="day-label">${d.days}일</span><small>n=${number(d.n)}</small></div>`).join('');
}
function renderCohorts(){
 const query=$('cohort-search').value.trim().toLowerCase();
 const rows=report.cohorts.filter(c=>`${c.module} ${c.term}`.toLowerCase().includes(query));
 $('cohort-table').innerHTML=rows.map(c=>`<tr><th scope="row">${esc(c.module)} · ${esc(c.term)}</th><td>${number(c.w1_active)}</td><td>${percent(c.repeat_comparison.control.rate)}</td><td>${percent(c.repeat_comparison.exposed.rate)}</td><td class="positive">${pp(c.repeat_comparison.difference)}</td><td class="${c.content_comparison.difference<0?'negative':'positive'}">${pp(c.content_comparison.difference)}</td></tr>`).join('');
 $('cohort-empty').hidden=rows.length>0;
}
function renderLab(id){
 const s=report.fault_lab.stages.find(s=>s.id===id);if(!s)return;
 document.querySelectorAll('[data-stage]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.stage===id)));
 $('lab-naive').textContent=percent(s.naive_rate);$('lab-rate').textContent=percent(s.rate);$('lab-gate').textContent=s.gate;
 $('lab-fraction').textContent=`${s.w2} / ${s.w1} 가상 학습자`;$('lab-missing').textContent=`원천 명세 대비 미수신 ${s.missing_events}개 이벤트`;
 const explanation={truth:'정상 기준: 첫 주 활성 10명 중 6명이 다음 주 활동. 별도의 원천 장부가 정답을 제공합니다.',observed:'중복 시작 행 2개가 누락된 2명을 가립니다. 행 수 지표는 정상처럼 60%, 학습자 기준은 40%. 원천 명세 대조 없이는 누락을 확정할 수 없습니다.',clean:'같은 event_id와 잘못된 사용자·세션을 정리해도 사라진 이벤트는 돌아오지 않습니다. 40%를 최종 성과로 확정하지 않고 게이트를 유지합니다.',late:'D16 수신 마감으로 지연된 1명의 활동을 회수. 재방문은 50%지만 영구 누락 1명의 이벤트 2개가 남아 판단 보류.',replay:'원천 장부 재수집 후 60% 복원. 누락값 추정이 아닌 재전송의 결과입니다. 실제 서비스에서 실행한 복구 성과가 아닙니다.'};
 $('lab-explanation').textContent=explanation[id];
}
function renderSample(){
 const p=Number($('baseline').value),d=Number($('mde').value);
 const s=report.experiment.samples.find(x=>x.baseline===p&&x.mde===d);
 $('sample-size').textContent=s?`그룹당 ${number(s.per_arm)}명`:'계산 범위 없음';
}
function render(){
 $('cohort').innerHTML='<option value="all">전체 · 22개 개설기</option>'+report.cohorts.map(c=>`<option value="${esc(c.module)}|${esc(c.term)}">${esc(c.module)} · ${esc(c.term)}</option>`).join('');
 renderScope('all');renderCohorts();renderLab('observed');renderSample();
 const q=report.quality.checks;$('quality-gate').textContent=report.quality.gate;
 $('raw-rows').textContent=number(report.inventory.studentVle);
 $('exact-repeats').textContent=number(q.find(x=>x.rule_id==='event_exact_repeat').count);
 $('click-changes').textContent=number(report.click_sensitivity[0].raw_vs_exact_changed);
 $('sensitivity-table').innerHTML=report.click_sensitivity.map(s=>`<tr><th scope="row">${s.threshold}클릭 이상</th><td>${number(s.raw_qualified)}</td><td>${number(s.exact_qualified)}</td><td>${number(s.max_qualified)}</td><td>${number(s.raw_vs_exact_changed)}</td></tr>`).join('');
 $('quality-rules').innerHTML=[...q].sort((a,b)=>b.count-a.count).map(r=>`<details><summary>${esc(ruleText[r.rule_id]?.[0]||r.rule_id)} <span>${number(r.count)} · ${r.count?'검토':'통과'}</span></summary><div><p>${esc(ruleText[r.rule_id]?.[1]||'')}</p><code>${esc(r.rule_id)}</code> · <a href="https://github.com/sokldjs554/learning-journey-lab/blob/main/sql/quality.sql" target="_blank" rel="noopener">검증 SQL ↗</a></div></details>`).join('');
 const e=report.eligibility;
 $('exclusions').textContent=`전체 ${number(e.total)}건 → 등록일 결측 ${number(e.missing_registration)}건 → 개강 후 등록 ${number(e.late_registration)}건 → 개강 전 탈퇴 ${number(e.pre_start_withdrawal)}건 제외 → 분석 ${number(report.overall.eligible)}건. 각 단계는 중복 없이 적용.`;
 $('temporal-results').innerHTML=report.temporal.map(t=>`<div class="temporal-line">${esc(t.label)}<strong>${pp(t.repeat_comparison.difference)}</strong><small>첫 주 활성 ${number(t.w1_active)}건 · 95% 구간 ${t.repeat_comparison.ci?t.repeat_comparison.ci.map(pp).join(' ~ '):'비교 불가'}</small></div>`).join('');
 const negative=report.cohorts.filter(c=>c.content_comparison.difference<0).length;
 $('counterevidence').textContent=`첫날 콘텐츠 접촉 그룹의 전체 차이는 ${pp(report.overall.content_comparison.difference)}. 하지만 ${report.cohorts.length}개 개설기 중 ${negative}개에서는 음의 차이이며, 2013년 탐색 구간은 0을 포함합니다.`;
 $('start-strata').innerHTML=report.first_day_strata.map(s=>`<tr><th scope="row">D${s.first_day}</th><td>${number(s.comparison.control.n)}</td><td>${number(s.comparison.exposed.n)}</td><td>${pp(s.comparison.difference)}</td></tr>`).join('');
 const strict=report.strict_sensitivity;
 $('strict-result').textContent=`탈퇴일 이후 활동을 제외하는 대안: ${number(strict.w2_returned)} / ${number(strict.w1_active)} = ${percent(strict.w2_returned/strict.w1_active)}. 기본 ${percent(report.overall.return_rate)}와 비교. 원인 미확정 자료의 삭제를 정답이라고 보지 않습니다.`;
 $('fault-rules').innerHTML=report.fault_lab.issues.map(r=>`<details><summary>${esc(r.rule_id)} <span>${r.count}</span></summary><p>${esc(r.action)}</p><pre><code>${esc(r.query)}</code></pre></details>`).join('');
 $('cohort').onchange=e=>renderScope(e.target.value);$('cohort-search').oninput=renderCohorts;
 document.querySelectorAll('[data-stage]').forEach(b=>b.onclick=()=>renderLab(b.dataset.stage));
 $('baseline').onchange=renderSample;$('mde').onchange=renderSample;
}
async function load(){
 $('error').hidden=true;$('app').hidden=true;$('loading').hidden=false;
 try{
  const response=await fetch('data/report.json',{cache:'no-cache'});if(!response.ok)throw new Error('HTTP response failed');
  const payload=await response.json();
  validateReport(payload);
  report=payload;render();$('app').hidden=false;
 }catch(error){$('error').hidden=false;}finally{$('loading').hidden=true;}
}
$('retry').onclick=load;load();

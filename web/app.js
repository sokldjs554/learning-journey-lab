'use strict';
const $=id=>document.getElementById(id);
const number=n=>new Intl.NumberFormat('ko-KR').format(n);
const percent=n=>n==null||!Number.isFinite(n)?'비교 불가':`${(n*100).toFixed(1)}%`;
const pp=n=>n==null?'비교 불가':`${n>=0?'+':''}${(n*100).toFixed(1)}%p`;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const repo='https://github.com/sokldjs554/learning-journey-lab/blob/main/';
let report,operations,state;
const allowed=(v,values,fallback)=>values.includes(v)?v:fallback;
const scopeValue=c=>`${c.module}|${c.term}`;
function readState(){
 const p=new URLSearchParams(location.search),rule=allowed(p.get('rule'),operations.rules.map(x=>x.rule_id),'event_exact_repeat');
 const cohort=allowed((p.get('cohort')||'all').replace('.','|'),['all',...report.cohorts.map(scopeValue)],'all');
 return {view:allowed(p.get('view'),Object.keys(viewCopy),'review'),rule,cohort,
  tab:allowed(p.get('tab'),['evidence','impact','decision'],'evidence'),
  stage:allowed(p.get('stage'),report.fault_lab.stages.map(x=>x.id),'observed'),
  detail:p.get('detail')==='1',filter:allowed(p.get('filter'),['open','all','clear'],operations.rules.find(x=>x.rule_id===rule).count?'open':'all'),
  display:allowed(p.get('display'),['chart','table'],'chart')};
}
function stateURL(s){
 const p=new URLSearchParams();p.set('view',s.view);
 if(s.rule!=='event_exact_repeat')p.set('rule',s.rule);
 if(s.tab!=='evidence')p.set('tab',s.tab);
 if(s.cohort!=='all')p.set('cohort',s.cohort.replace('|','.'));
 if(s.stage!=='observed')p.set('stage',s.stage);
 if(s.detail)p.set('detail','1');
 if(s.filter!=='open')p.set('filter',s.filter);
 if(s.display!=='chart')p.set('display',s.display);
 return `${location.pathname}?${p}`;
}
function navigate(patch,{focus=null,replace=false}={}){
 state={...state,...patch};const url=stateURL(state);
 if(url!==location.pathname+location.search)history[replace?'replaceState':'pushState']({},'',url);
 renderPage();
 if(focus){const el=document.querySelector(focus)||(state.view==='review'&&!state.detail?$('rule-search'):$('page-title'));el.focus();}
}
function statusText(rule){return rule.count>0?(rule.severity==='block'?'판단 차단':'검토 필요'):(rule.status==='resolved'?'해결 기록':'통과');}
function ruleConfig(rule){return ReviewCatalog[rule.rule_id]||{question:'집계 전에 필요한 데이터 조건을 확인합니다.',expected:ruleText[rule.rule_id]?.[1]||rule.rule_id,unit:rule.rule_id.endsWith('repeat')?'초과 행':'행',impact:'집계 전 계약 검사',action:rule.count?'근거 확인 후 집계 보류':'현재 검출 없음 · 검사 유지'};}
function renderQueue(){
 const search=$('rule-search').value.trim().toLowerCase();$('rule-filter').value=state.filter;
 const rank=id=>{const n=reviewOrder.indexOf(id);return n<0?100:n;};
 const rows=[...operations.rules].sort((a,b)=>rank(a.rule_id)-rank(b.rule_id)||a.rule_id.localeCompare(b.rule_id)).filter(x=>(state.filter==='all'||(state.filter==='open'?x.count>0:x.count===0))&&`${ruleText[x.rule_id]?.[0]} ${x.rule_id}`.toLowerCase().includes(search));
 $('review-list').innerHTML=rows.map(r=>{const cfg=ruleConfig(r);return `<button type="button" class="review-item" data-rule="${esc(r.rule_id)}" aria-current="${r.rule_id===state.rule}"><span class="review-item-top"><span class="review-item-title">${esc(ruleText[r.rule_id]?.[0]||r.rule_id)}</span><span class="status ${r.count?'review':'clear'}">${statusText(r)}</span></span><small>${number(r.count)} ${esc(cfg.unit)} · ${esc(cfg.impact)}</small><span class="item-next">${esc(cfg.action)} <span aria-hidden="true">→</span></span></button>`;}).join('');
 $('review-empty').hidden=rows.length>0;
}
function table(caption,headers,rows){return `<div class="table-wrap" tabindex="0" role="region" aria-label="${esc(caption)}"><table><caption>${esc(caption)}</caption><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map((c,i)=>i?`<td>${c}</td>`:`<th scope="row">${c}</th>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function sourceBlock(rule){
 const source=operations.sql_files[rule.sql_file];
 return `<div class="source-row"><span>실행에 사용한 SQL · ${rule.sql_line}행</span><a id="sql-link" href="${repo}${rule.sql_file}#L${rule.sql_line}" target="_blank" rel="noopener">${esc(rule.sql_file)} ↗</a></div><details class="sql-details"><summary>SQL 원문 펼치기</summary><pre tabindex="0" role="region" aria-label="SQL 원문"><code>${source.split('\n').map((line,i)=>`<span class="sql-line ${i+1===rule.sql_line?'current':''}"><span class="line-no">${i+1}</span>${esc(line)}</span>`).join('')}</code></pre></details>`;
}
function impactHTML(rule){
 const id=rule.rule_id;
 if(['event_exact_repeat','event_daily_key_repeat'].includes(id)){
  const s=report.click_sensitivity[0];
  return `<div class="impact-lead"><strong>${number(s.raw_vs_exact_changed)} 수강 건</strong><span>첫날 ${s.threshold}클릭 기준 · 원본 합산 ↔ 동일 값 한 번</span></div><p class="caption">분석 범위: 전체 첫 주 활성 수강 건. 세 정책 중 어느 것이 진실인지 원천 ID 없이 확정할 수 없습니다.</p><p id="policy-meaning">${number(s.raw_qualified)} − ${number(s.exact_qualified)} = ${number(s.raw_vs_exact_changed)}건. 처리 정책에 따라 10클릭 기준의 충족 여부가 달라진 수강 건입니다. 같은 사람이 여러 수강 건을 가질 수 있습니다.</p>${table('반복 행 처리 정책별 대상 수강 건',['첫날 기준','원본 합산','동일 값 한 번','자료별 최대','분류 변경¹'],report.click_sensitivity.map(s=>[`${s.threshold}클릭`,number(s.raw_qualified),number(s.exact_qualified),number(s.max_qualified),number(s.raw_vs_exact_changed)]))}<p class="caption">¹ 원본 합산과 동일 값 한 번의 대상 분류 차이. 반복 규칙 간 행 수를 합산하지 않습니다.</p><div class="impact-result"><strong>활동일 지표 사용</strong><p>하루에 유효한 양수 클릭이 있었는지는 세 정책에서 같습니다. 클릭의 절대 횟수에 기대지 않는 지표로 재방문 근거를 확인합니다.</p><a href="?view=analysis&cohort=all" data-all-evidence>활동일별 재방문 근거 →</a></div>`;
 }
 if(id==='event_after_withdrawal'){
  const s=report.strict_sensitivity,o=report.overall;
  return `<h3>등록 기간 정책 비교</h3><p class="caption">전체 분석 대상 유지. 탈퇴 이후 활동의 포함 여부만 변경합니다.</p>${table('탈퇴 이후 활동 포함 여부에 따른 지표',['정책','첫 주 활성','다음 주 재방문','재방문율'],[['기본 · 원본 보존',number(o.w1_active),number(o.w2_returned),percent(o.return_rate)],['대안 · 탈퇴 이후 제외',number(s.w1_active),number(s.w2_returned),percent(s.w2_returned/s.w1_active)]] )}<p>첫 주 활동일 값이 바뀐 수강 건 ${number(s.changed_w1_enrollments)}건, 다음 주 활성 여부가 바뀐 수강 건 ${number(s.changed_w2_enrollments)}건.</p><div class="impact-result"><strong>원본 보존 · 민감도 병기</strong><p>탈퇴 이후 기록을 삭제하는 정책을 정답으로 보지 않습니다. 사후 탈퇴 여부로 분석 대상을 줄이면 미래 정보를 사용하는 문제가 생깁니다.</p></div>`;
 }
 if(id==='registration_missing_date'){
  const e=report.eligibility;let n=e.total;
  return `<h3>분모의 순차 제외</h3>${table('순서대로 적용 · 제외 건수는 중복 없음',['단계','제외','남은 수강 건'],[['전체 등록','—',number(n)],['등록일 결측',number(e.missing_registration),number(n-=e.missing_registration)],['개강 후 등록',number(e.late_registration),number(n-=e.late_registration)],['개강 전 탈퇴',number(e.pre_start_withdrawal),number(n-=e.pre_start_withdrawal)]])}<p>등록일 결측을 0으로 대체하지 않습니다. 개강일까지 등록했고 개강 전에 탈퇴하지 않은 수강 건을 분석합니다.</p>`;
 }
 return `<h3>${id==='event_after_course'?'분석 시간 창과 분리':'판단에 미치는 영향'}</h3><p>${id==='event_after_course'?'이번 개설 기간 밖의 활동은 첫 28일 분석 범위 밖입니다. 원본을 보존하고 복습·접근 권한·추출 기준을 추가 확인해야 합니다.':rule.count?'해당 조건이 충족되지 않아 집계를 보류해야 합니다. 영향 크기를 별도로 추정하지 않았습니다.':'현재 스냅샷에서 위반은 검출되지 않았습니다. 이는 이 규칙에 대한 결과이며 원천 누락이나 전체 데이터의 정확성을 보장하지 않습니다.'}</p><div class="impact-result">${esc(ruleConfig(rule).action)}</div>`;
}
function decisionHTML(rule){
 const cfg=ruleConfig(rule);
 const log=cfg.before?[['초기 접근',cfg.before],['발견',cfg.finding],['수정',cfg.change],['현재 판단',cfg.action],['추가 확인',cfg.next]]:[['검사 목적',ruleText[rule.rule_id]?.[1]||rule.rule_id],['현재 판단',cfg.action],['해석 범위','이 검사의 통과만으로 원천 로그의 완전성을 확인할 수는 없습니다.']];
 return `<ol class="decision-log">${log.map(([label,value])=>`<li><b>${label}</b><p>${esc(value)}</p></li>`).join('')}</ol><div class="source-row"><strong>자동 기록 · 원본 스냅샷 ${rule.history.length}개</strong><a href="?view=runs" data-view-link="runs">실행 기록 →</a></div>${rule.history.map(h=>`<div class="history-entry"><span class="status ${h.count?'review':'clear'}">${h.count?'검토':'0건'}</span><div><p>${number(h.count)} ${esc(cfg.unit)}</p><code title="${esc(h.snapshot)}">${esc(h.snapshot.slice(0,12))}…</code></div></div>`).join('')}<p class="caption">해시는 날짜가 아닙니다. 동일 스냅샷의 반복 실행을 새 장애 이력으로 늘리지 않습니다. 실제 담당자·처리 시간은 기록하지 않았습니다.</p><a class="caption" href="${repo}docs/learning-log.md" target="_blank" rel="noopener">개발·분석 수정 기록 ↗</a>`;
}
function renderDetail(){
 const rule=operations.rules.find(x=>x.rule_id===state.rule),cfg=ruleConfig(rule);
 $('view-review').classList.toggle('mobile-detail',state.detail);
 $('detail-title').textContent=ruleText[rule.rule_id]?.[0]||rule.rule_id;
 $('detail-id').textContent=rule.rule_id;$('detail-question').textContent=cfg.question;
 $('detail-status').textContent=statusText(rule);$('detail-status').className=`status ${rule.count?'review':'clear'}`;
 document.querySelectorAll('[data-tab]').forEach(b=>{const active=b.dataset.tab===state.tab;b.setAttribute('aria-selected',active);b.tabIndex=active?0:-1;});
 $('detail-content').setAttribute('aria-labelledby',`tab-${state.tab}`);
 if(state.tab==='evidence')$('detail-content').innerHTML=`<dl class="evidence-summary"><div><dt>관측값 · 공개 원본 전체</dt><dd class="observed">${number(rule.count)}<small>${esc(cfg.unit)}</small></dd></div><div><dt>검사 조건</dt><dd>${esc(cfg.expected)}</dd></div></dl><p class="statement">${esc(ruleText[rule.rule_id]?.[1]||'')}</p><div class="next-step"><strong>${esc(cfg.action)}</strong><button type="button" class="text-button" data-open-impact>지표 영향 확인 →</button></div>${sourceBlock(rule)}<p class="caption">이 결과는 OULAD 공개 자료 점검입니다. 원천 이벤트 ID·수신 시각이 없어 누락과 일내 순서를 검증할 수 없습니다.</p>`;
 else if(state.tab==='impact')$('detail-content').innerHTML=impactHTML(rule);
 else $('detail-content').innerHTML=decisionHTML(rule);
}
function interval(c){return c.ci?`95% 군집 구간 ${c.ci.map(pp).join(' ~ ')}`:'비교 가능한 구간 없음';}
function renderScope(){
 const c=state.cohort==='all'?report.overall:report.cohorts.find(c=>scopeValue(c)===state.cohort);
 $('cohort').value=state.cohort;
 $('eligible').textContent=number(c.eligible);$('w1').textContent=number(c.w1_active);$('return-rate').textContent=percent(c.return_rate);$('return-fraction').textContent=`${number(c.w2_returned)} / ${number(c.w1_active)} 수강 건`;
 $('return-definition').textContent=`재방문율: 분자 ${number(c.w2_returned)}건 ÷ 분모 ${number(c.w1_active)}건 × 100. 분모는 첫 주 활성 수강 건입니다. 분석 대상 ${number(c.eligible)}건 전체를 분모로 쓰는 비율과 구분합니다.`;
 const comp=c.repeat_comparison;
 $('comparison-bars').innerHTML=[['1일 활동',comp.control,'secondary'],['2일+ 활동',comp.exposed,'']].map(([label,g,cls])=>`<div class="bar-row"><span>${label}<small>n=${number(g.n)}</small></span><div class="bar-track" aria-hidden="true"><div class="bar-fill ${cls}" style="width:${g.rate==null?0:g.rate*100}%"></div></div><strong>${percent(g.rate)}</strong></div>`).join('');
 $('difference').textContent=pp(comp.difference);$('difference-ci').textContent=interval(comp);
 $('chart-scope').textContent=state.cohort==='all'?`전체 · ${report.cohorts.length}개 개설기`:state.cohort.replace('|',' · ');
 const content=c.content_comparison;$('content-diff').textContent=pp(content.difference);$('content-ci').textContent=interval(content);
 $('content-reading').textContent=`콘텐츠 접촉군 − 미접촉군의 재방문율 차이 ${pp(content.difference)}. %p는 두 비율의 차이이며, 접촉이 원인이라는 뜻은 아닙니다.`;
 $('content-status').textContent=content.difference==null?'비교 불가':content.difference<0?'반대 방향':'인과 해석 보류';
 $('content-groups').innerHTML=[['미접촉',content.control],['접촉',content.exposed]].map(([name,g])=>`<div class="group-line"><span>${name} <small>n=${number(g.n)}</small></span><span>${percent(g.rate)} <small>(${number(g.returned)}건)</small></span></div>`).join('');
 $('day-bars').innerHTML=c.days.map(d=>`<div class="day-col"><strong>${percent(d.rate)}</strong><div class="day-rect" style="height:${d.rate==null?0:d.rate*135}px" aria-hidden="true"></div><span class="day-label">${d.days}일</span><small>n=${number(d.n)}</small></div>`).join('');
 $('day-table').innerHTML=c.days.map(d=>`<tr><th scope="row">${d.days}일</th><td>${number(d.n)}</td><td>${number(d.returned)}</td><td>${percent(d.rate)}</td></tr>`).join('');
 $('day-bars').hidden=state.display!=='chart';$('day-table-wrap').hidden=state.display!=='table';$('show-chart').setAttribute('aria-pressed',state.display==='chart');$('show-table').setAttribute('aria-pressed',state.display==='table');
 $('global-evidence').hidden=state.cohort!=='all';$('scoped-global-link').hidden=state.cohort==='all';
 $('exclusions').hidden=state.cohort!=='all';$('scoped-exclusions-note').hidden=state.cohort==='all';
}
function renderCohorts(){
 const q=$('cohort-search').value.trim().toLowerCase();const rows=report.cohorts.filter(c=>`${c.module} ${c.term}`.toLowerCase().includes(q));
 $('cohort-table').innerHTML=rows.map(c=>`<tr><th scope="row"><button type="button" class="table-link" data-cohort="${scopeValue(c)}">${esc(c.module)} · ${esc(c.term)}</button></th><td>${number(c.w1_active)}</td><td>${percent(c.repeat_comparison.control.rate)}</td><td>${percent(c.repeat_comparison.exposed.rate)}</td><td>${pp(c.repeat_comparison.difference)}</td><td>${pp(c.content_comparison.difference)}</td></tr>`).join('');$('cohort-empty').hidden=rows.length>0;
}
function renderLab(){
 const s=report.fault_lab.stages.find(x=>x.id===state.stage);
 document.querySelectorAll('[data-stage]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.stage===state.stage));
 $('lab-naive').textContent=percent(s.naive_rate);$('lab-rate').textContent=percent(s.rate);$('lab-gate').textContent=s.gate;
 $('lab-fraction').textContent=`${s.w2} / ${s.w1} 가상 학습자`;$('lab-missing').textContent=`원천 명세 대비 미수신 ${s.missing_events}개 이벤트`;
 const copy={truth:'정상 기준: 첫 주 활성 10명 중 6명이 다음 주 활동. 별도 원천 장부가 기준값을 제공합니다.',observed:'중복 시작 행 2개가 누락된 2명을 가립니다. 행 수 지표는 정상처럼 60%, 학습자 기준은 40%. 원천 명세 대조 없이는 누락을 확정할 수 없습니다.',clean:'같은 event_id와 잘못된 사용자·세션을 정리해도 사라진 이벤트는 돌아오지 않습니다. 40%를 최종 성과로 확정하지 않습니다.',late:'D16 수신 마감으로 지연된 1명의 활동을 회수합니다. 재방문은 50%지만 영구 누락 1명의 이벤트 2개가 남아 판단을 보류합니다.',replay:'원천 장부 재수집 후 60% 복원. 누락값 추정이 아닌 재전송의 결과입니다. 실제 서비스 복구 성과가 아닙니다.'};$('lab-explanation').textContent=copy[state.stage];
}
function renderSample(){const p=Number($('baseline').value),d=Number($('mde').value),s=report.experiment.samples.find(x=>x.baseline===p&&x.mde===d);$('sample-size').textContent=s?`그룹당 ${number(s.per_arm)}명`:'계산 범위 없음';}
function renderPage(){
 for(const v of Object.keys(viewCopy))$(`view-${v}`).hidden=v!==state.view;
 document.querySelectorAll('[data-view]').forEach(a=>{if(a.dataset.view===state.view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');a.href=stateURL({...state,view:a.dataset.view});});
 $('page-title').textContent=viewCopy[state.view][0];$('page-description').textContent=viewCopy[state.view][1];document.title=`${viewCopy[state.view][0]} · Learning Journey Lab`;
 const lab=state.view==='lab';$('real-source').textContent=lab?'생성 데이터 · 가상 장부':'공개 데이터 · OULAD';$('period-label').textContent=lab?'12명 · 고정된 재현 시나리오':'2013–2014 · 일별 학습 활동';$('page-note').textContent=lab?'실제 분석과 분리 · 서비스 장애 사례 아님':'CLASS101 내부 데이터 아님 · 원천 순서·구독 갱신 미관측';
 if(state.view==='review'){renderQueue();renderDetail();}
 if(state.view==='analysis'){renderScope();renderCohorts();}
 if(state.view==='lab')renderLab();
}
function initialize(){
 const checks=report.quality.checks;$('review-counts').textContent=`검토 필요 ${checks.filter(x=>x.count>0&&x.severity==='review').length} · 차단 ${checks.filter(x=>x.count>0&&x.severity==='block').length} · 규칙 ${checks.length}`;
 $('cohort').innerHTML='<option value="all">전체 · 22개 개설기</option>'+report.cohorts.map(c=>`<option value="${scopeValue(c)}">${esc(c.module)} · ${esc(c.term)}</option>`).join('');
 $('temporal-results').innerHTML=report.temporal.map(t=>`<div class="temporal-line"><span>${esc(t.label)}</span><strong>${pp(t.repeat_comparison.difference)}</strong><small>첫 주 활성 ${number(t.w1_active)}건 · ${interval(t.repeat_comparison)}</small></div>`).join('');
 $('counterevidence').textContent=`첫날 콘텐츠 접촉의 전체 차이는 ${pp(report.overall.content_comparison.difference)}. ${report.cohorts.length}개 개설기 중 ${report.cohorts.filter(c=>c.content_comparison.difference<0).length}개는 반대 방향입니다. 그중 ${report.cohorts.filter(c=>c.content_comparison.difference<0&&c.content_comparison.ci&&c.content_comparison.ci[0]<=0&&c.content_comparison.ci[1]>=0).length}개는 95% 구간에 0을 포함합니다. 2013 탐색 구간도 0을 포함합니다. 이 비교는 활동일 횟수가 아닌 콘텐츠 접촉 여부입니다.`;
 $('start-strata').innerHTML=report.first_day_strata.map(s=>`<tr><th scope="row">D${s.first_day}</th><td>${number(s.comparison.control.n)}</td><td>${number(s.comparison.exposed.n)}</td><td>${pp(s.comparison.difference)}</td></tr>`).join('');
 const e=report.eligibility;$('exclusions').textContent=`전체 ${number(e.total)}건 → 등록일 결측 ${number(e.missing_registration)}건 → 개강 후 등록 ${number(e.late_registration)}건 → 개강 전 탈퇴 ${number(e.pre_start_withdrawal)}건 제외 → 분석 ${number(report.overall.eligible)}건. 각 단계는 중복 없이 적용합니다. 이후 탈퇴자로 분모를 줄이지 않습니다.`;
 const b=operations.benchmark;$('run-summary').textContent=`결과 해시 동일 · 전체 실행 중앙값 ${b.median_seconds.toFixed(2)}초`;
 $('run-table').innerHTML=b.runs.map((run,i)=>`<tr><th scope="row">${i+1}회</th>${['load_and_hash_seconds','quality_seconds','mart_and_sensitivity_seconds','statistics_seconds','total_seconds'].map(k=>`<td>${run.timings[k].toFixed(2)}초</td>`).join('')}<td>동일 해시</td></tr>`).join('');
 $('snapshot-hash').textContent=operations.snapshot_id;$('report-hash').textContent=operations.report_sha256;
 $('issue-registry').innerHTML=operations.rules.filter(x=>x.status==='open').map(r=>`<a href="?view=review&rule=${r.rule_id}&tab=decision&detail=1" data-issue="${r.rule_id}"><span>${esc(ruleText[r.rule_id]?.[0]||r.rule_id)} <span aria-hidden="true">→</span></span><small>${number(r.count)} ${esc(ruleConfig(r).unit)} · 원본 스냅샷 ${r.history.length}개 · 원인 미확정/검토</small></a>`).join('');
 $('fault-rules').innerHTML=report.fault_lab.issues.map(r=>`<details><summary>${esc(r.rule_id)}<span>${r.count}건</span></summary><p>${esc(r.action)}</p><pre tabindex="0" role="region" aria-label="생성 로그 검증 SQL"><code>${esc(r.query)}</code></pre></details>`).join('');
 renderSample();state=readState();history.replaceState({},'',stateURL(state));renderPage();
}
document.addEventListener('click',e=>{
 const el=e.target.closest('a,button');if(!el||!report||!state)return;
 if(el.matches('a')&&(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||e.button!==0))return;
 if(el.dataset.view||el.dataset.viewLink){e.preventDefault();navigate({view:el.dataset.view||el.dataset.viewLink},{focus:'#page-title'});window.scrollTo(0,0);}
 else if(el.hasAttribute('data-all-evidence')){e.preventDefault();navigate({view:'analysis',cohort:'all'},{focus:'#page-title'});window.scrollTo(0,0);}
 else if(el.dataset.issue){e.preventDefault();navigate({view:'review',rule:el.dataset.issue,tab:'decision',detail:true,filter:'open'},{focus:'#detail-title'});}
 else if(el.dataset.rule)navigate({rule:el.dataset.rule,tab:'evidence',detail:true},{focus:'#detail-title'});
 else if(el.dataset.tab)navigate({tab:el.dataset.tab},{focus:`#tab-${el.dataset.tab}`});
 else if(el.hasAttribute('data-open-impact'))navigate({tab:'impact'},{focus:'#tab-impact'});
 else if(el.dataset.cohort){navigate({cohort:el.dataset.cohort},{focus:'#cohort'});window.scrollTo(0,0);}
 else if(el.dataset.stage)navigate({stage:el.dataset.stage});
});
document.querySelector('.detail-tabs').addEventListener('keydown',e=>{
 if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
 e.preventDefault();const tabs=['evidence','impact','decision'],i=tabs.indexOf(state.tab);
 const n=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;
 navigate({tab:tabs[n]},{focus:`#tab-${tabs[n]}`});
});
$('detail-back').onclick=()=>navigate({detail:false},{focus:`[data-rule="${state.rule}"]`});
$('rule-search').oninput=renderQueue;$('rule-filter').onchange=e=>navigate({filter:e.target.value});
$('reset-search').onclick=()=>{$('rule-search').value='';navigate({filter:'open'});$('rule-search').focus();};
$('cohort').onchange=e=>navigate({cohort:e.target.value});$('cohort-search').oninput=renderCohorts;
$('show-chart').onclick=()=>navigate({display:'chart'});$('show-table').onclick=()=>navigate({display:'table'});
$('baseline').onchange=renderSample;$('mde').onchange=renderSample;
window.addEventListener('popstate',()=>{
 if(!report||!operations)return;
 const previous=state;state=readState();renderPage();
 if(state.view==='review'&&matchMedia('(max-width:699px)').matches&&!state.detail){
  const origin=previous.view==='review'&&previous.detail?previous.rule:state.rule;
  (document.querySelector(`[data-rule="${origin}"]`)||$('rule-search')).focus();
 }else if(state.view==='review')$('detail-title').focus();
 else $('page-title').focus();
});
async function load(){
 const restoreFocus=document.activeElement===$('retry');
 $('error').hidden=true;$('app').hidden=true;$('loading').hidden=false;
 let failure=['근거 파일 불러오기 실패','연결 상태 또는 배포 파일을 확인한 뒤 다시 불러와 주세요.'];
 try{
  const responses=await Promise.all(['report','operations'].map(name=>fetch(`data/${name}.json`,{cache:'no-cache'})));
  if(responses.some(r=>!r.ok))throw new Error('HTTP response failed');
  failure=['근거 정합성 확인 실패','분석 결과·SQL·이슈 이력이 일치하지 않거나 파일 형식이 잘못됐습니다. 확인되지 않은 판단은 표시하지 않습니다.'];
  const [reportBytes,operationsBytes]=await Promise.all(responses.map(r=>r.arrayBuffer()));
  const decode=new TextDecoder();
  const r=JSON.parse(decode.decode(reportBytes)),o=JSON.parse(decode.decode(operationsBytes));
  if(r?.quality?.gate==='BLOCK'){
   failure=['분석 공개 보류','품질 검사에서 차단 조건이 발견됐습니다. 원인을 확인하고 다시 분석하기 전에는 결과를 사용하지 않습니다.'];throw new Error('Blocked evidence');
  }
  if(!['PASS','REVIEW'].includes(r?.quality?.gate)){
   failure=['검증 상태 미확인','품질 검사가 완료됐는지 확인할 수 없습니다. 통과로 간주하지 않고 결과 해석을 보류합니다.'];throw new Error('Unverified evidence');
  }
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',reportBytes)),n=>n.toString(16).padStart(2,'0')).join('');
  if(digest!==o.report_sha256)throw new Error('Report bytes do not match operating evidence');
  validateReport(r);validateOperations(o,r);
  report=r;operations=o;initialize();$('app').hidden=false;
 }catch(error){report=null;operations=null;$('error-title').textContent=failure[0];$('error-description').textContent=failure[1];$('error').hidden=false;}finally{$('loading').hidden=true;if(restoreFocus)(report?$('page-title'):$('retry')).focus();}
}
$('retry').onclick=load;load();

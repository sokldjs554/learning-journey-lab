'use strict';
const EvidenceExtension={
 check(ok){if(!ok)throw new Error('추가 근거 정합성 오류');},
 external(r){
  const ck=this.check;ck(r.analysis_type==='observational_public_data'&&r.manifest.dataset==='EdNet-KT4'&&r.censoring_sensitivity.status==='not_identifiable');
  ck(Number.isInteger(r.sample.users)&&r.sample.users>0&&r.sample.users===r.manifest.sample_users);
  const comparisons=[r.primary,...r.event_definition_sensitivity],count=n=>Number.isInteger(n)&&n>=0;
  ck(JSON.stringify(comparisons.map(c=>c.definition))===JSON.stringify(['submit','entry','ui']));
  for(const c of comparisons){
   ck(JSON.stringify(c.groups.map(g=>g.active_days))===JSON.stringify(['1','2+']));
   ck(count(c.eligible_firstweek_users)&&count(c.excluded_zero_firstweek_users));
   ck(c.groups.length===2&&c.eligible_firstweek_users+c.excluded_zero_firstweek_users===r.sample.users);
   ck(c.groups.reduce((n,g)=>n+g.n,0)===c.eligible_firstweek_users);
   for(const g of c.groups)ck(Number.isInteger(g.n)&&g.n>0&&Number.isInteger(g.recorded_nextweek)&&g.recorded_nextweek>=0&&g.recorded_nextweek<=g.n&&Number.isFinite(g.rate)&&Math.abs(g.rate-g.recorded_nextweek/g.n)<1e-10);
   ck(Number.isFinite(c.difference)&&Math.abs(c.difference-c.groups[1].rate+c.groups[0].rate)<1e-10);
  }
  ck(r.quality.raw_rows===r.sample.raw_rows&&r.quality.raw_rows-r.quality.exact_duplicate_rows===r.quality.deduplicated_rows);
  ck(r.payments.pay_events===r.quality.action_counts.pay&&r.payments.refund_events===r.quality.action_counts.refund&&r.validation.sql_pandas_equal===true);
  for(const [people,events,action] of [['paying_users','pay_events','pay'],['refunding_users','refund_events','refund'],['coupon_users','coupon_events','enroll_coupon']])ck(count(r.payments[people])&&count(r.payments[events])&&r.payments[people]<=Math.min(r.sample.users,r.payments[events])&&r.payments[events]===(r.quality.action_counts[action]||0));
  return r;
 },
 experiment(r){
  this.check(r.type==='synthetic_engineering_validation_not_live_experiment'&&r.actual_participants===0&&r.actual_service_effect===null&&r.actual_service_baseline===null&&r.actual_daily_eligible===null);
  for(const c of Object.values(r.synthetic_cases))this.check(['hold','ready_for_review'].includes(c.status)&&(c.status!=='hold'||c.difference===null));
  for(const x of r.recruitment_scenarios)this.check(x.maturation_days===14&&x.late_buffer_days===1&&x.raw_recruitment_days===Math.ceil(2*x.per_arm/x.hypothetical_daily_eligible)&&x.recruitment_days===Math.max(7,7*Math.ceil(x.raw_recruitment_days/7))&&x.total_days_upper_bound===x.recruitment_days+15);
  return r;
 },
 async load(name,kind){
  const [response,release]=await Promise.all([fetch('data/'+name,{cache:'no-cache'}),fetch('data/release.json',{cache:'no-cache'})]);
  this.check(response.ok&&release.ok);const bytes=await response.arrayBuffer(),metadata=await release.json();
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  this.check(metadata.extensions?.[name]===hash);return this[kind](JSON.parse(new TextDecoder().decode(bytes)));
 }
};

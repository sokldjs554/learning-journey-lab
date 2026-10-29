'use strict';
// Reject malformed evidence before any affirmative decision appears.
function validateReport(r){
 const fail=()=>{throw new Error('Invalid evidence contract');};
 const count=n=>Number.isInteger(n)&&n>=0;
 const rate=n=>n===null||(typeof n==='number'&&Number.isFinite(n)&&n>=0&&n<=1);
 const eq=(a,b)=>typeof a==='number'&&typeof b==='number'&&Math.abs(a-b)<1e-10;
 function group(g){if(!g||!count(g.n)||!count(g.returned)||g.returned>g.n||!rate(g.rate)||(g.n? !eq(g.rate,g.returned/g.n):g.rate!==null))fail();}
 function comparison(c){
  if(!c)fail();group(c.control);group(c.exposed);
  if(c.control.n&&c.exposed.n){if(!eq(c.difference,c.exposed.rate-c.control.rate))fail();}
  else if(c.difference!==null)fail();
  if(c.ci!==null&&(!Array.isArray(c.ci)||c.ci.length!==2||!c.ci.every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=-1&&v<=1)||c.ci[0]>c.ci[1]))fail();
 }
 function summary(s){
  if(!s||![s.eligible,s.w1_active,s.w2_returned].every(count)||s.w2_returned>s.w1_active||s.w1_active>s.eligible||!rate(s.return_rate)||(s.w1_active?!eq(s.return_rate,s.w2_returned/s.w1_active):s.return_rate!==null))fail();
  if(!Array.isArray(s.days)||s.days.length!==8)fail();
  s.days.forEach((d,i)=>{if(d.days!==i)fail();group(d);});
  if(s.days.reduce((n,d)=>n+d.n,0)!==s.eligible||s.days.slice(1).reduce((n,d)=>n+d.n,0)!==s.w1_active||s.days.slice(1).reduce((n,d)=>n+d.returned,0)!==s.w2_returned)fail();
  comparison(s.repeat_comparison);comparison(s.content_comparison);
  for(const c of [s.repeat_comparison,s.content_comparison])if(c.control.n+c.exposed.n!==s.w1_active)fail();
 }
 if(!r||r.schema_version!==1||r.source_type!=='public'||r.fault_lab?.source_type!=='synthetic'||!['PASS','REVIEW'].includes(r.quality?.gate))fail();
 summary(r.overall);
 if(!Array.isArray(r.cohorts)||!r.cohorts.length)fail();r.cohorts.forEach(summary);
 if(r.cohorts.reduce((n,c)=>n+c.eligible,0)!==r.overall.eligible)fail();
 if(!Array.isArray(r.temporal)||r.temporal.length!==2)fail();r.temporal.forEach(summary);
 if(!Array.isArray(r.quality.checks)||!r.quality.checks.length||r.quality.checks.some(c=>!count(c.count)||!['block','review'].includes(c.severity)||(c.severity==='block'&&c.count>0)))fail();
 if(!Array.isArray(r.first_day_strata))fail();r.first_day_strata.forEach(s=>comparison(s.comparison));
 if(!Array.isArray(r.click_sensitivity)||r.click_sensitivity.some(s=>!Object.values(s).every(count)))fail();
 if(!r.inventory||!Object.values(r.inventory).every(count)||!r.eligibility||!Object.values(r.eligibility).every(count))fail();
 if(!r.strict_sensitivity||!Object.values(r.strict_sensitivity).every(count))fail();
 if(!Array.isArray(r.fault_lab.stages)||r.fault_lab.stages.length!==5)fail();
 r.fault_lab.stages.forEach(s=>{if(![s.w1,s.w2,s.missing_events].every(count)||s.w1===0||s.w2>s.w1||!eq(s.rate,s.w2/s.w1)||!Number.isFinite(s.naive_rate)||s.naive_rate<0||!['PASS','BLOCK'].includes(s.gate))fail();});
 if(!Array.isArray(r.experiment?.samples)||r.experiment.samples.some(s=>!rate(s.baseline)||!rate(s.mde)||!count(s.per_arm)||s.per_arm===0))fail();
 return r;
}

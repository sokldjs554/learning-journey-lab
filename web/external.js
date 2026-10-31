'use strict';
const byId=id=>document.getElementById(id),num=n=>new Intl.NumberFormat('ko-KR').format(n),pct=n=>(n*100).toFixed(1)+'%',diff=n=>(n>=0?'+':'')+(n*100).toFixed(1)+'%p';let extra;
function draw(){
 const k=byId('event-definition').value,c=[extra.primary,...extra.event_definition_sensitivity].find(x=>x.definition===k);
 byId('external-denominator').textContent=`선택 이벤트로 첫 주 활동한 ${num(c.eligible_firstweek_users)}명 기준 · 첫 주 해당 이벤트가 없는 ${num(c.excluded_zero_firstweek_users)}명 제외`;
 byId('external-groups').innerHTML=c.groups.map(g=>`<tr><th scope="row">${g.active_days==='1'?'1일':'2일 이상'}</th><td>${num(g.n)}명</td><td>${num(g.recorded_nextweek)}명</td><td>${pct(g.rate)}</td></tr>`).join('');
 byId('external-difference').textContent=`기록 비율 차이 ${diff(c.difference)} · 95% 사용자 재추출 구간 ${c.ci95.map(diff).join(' ~ ')}. 이 구간은 관찰 누락·교란·서비스 차이를 보정하지 않습니다.`;
}
async function load(){
 const restoreFocus=document.activeElement===byId('external-retry');
 byId('external-app').hidden=true;byId('external-error').hidden=true;byId('external-loading').hidden=false;
 try{
  extra=await EvidenceExtension.load('ednet_report.json','external');const r=extra,q=r.quality,p=r.payments,m=r.manifest;
  byId('external-summary').textContent=`파일명 해시로 선정한 ${num(r.sample.users)}명의 전체 제공 이력 · ${num(r.sample.raw_rows)}행. OULAD와 합산하지 않은 별도 관찰 분석입니다.`;
  byId('definition-impact').textContent=`문제 제출 대신 모든 이벤트를 활동으로 세면, ‘첫 주 2일 이상’ 분류가 ${num(q.firstweek_activity_group_changed_submit_vs_all_ui)}명, 다음 주 기록 여부가 ${num(q.nextweek_flag_changed_submit_vs_all_ui)}명 달라집니다. 모든 이벤트에는 구매·환불도 포함되므로 학습과 같은 뜻으로 쓰지 않습니다.`;
  byId('external-quality').innerHTML=[['동일 값 반복 초과',num(q.exact_duplicate_rows)+'행','원본 보존 · 제거 민감도 비교'],['동일 값 한 번 처리 후 활동 지표 변경',num(q.raw_vs_dedup_changed_users)+'명','일별 존재 지표는 이 표본에서 유지'],['필수 키·시각 오류',num(q.invalid_required_fields)+'행','기본 계약 검사'],['플랫폼 결측',num(q.missing_platform_rows)+'행','구매·환불·쿠폰 이벤트에 집중 · 학습 로그와 구분'],['비어 있지 않은 미등록 플랫폼',num(q.unknown_nonempty_platform_rows)+'행','결측과 잘못된 값 구분'],['구매·환불의 없는 상품 키',num(p.unknown_payment_key_events)+'행','실제 카탈로그와 대조']].map(row=>'<tr>'+row.map((v,i)=>i?`<td>${v}</td>`:`<th scope="row">${v}</th>`).join('')+'</tr>').join('');
  byId('payment-summary').textContent=`전체 제공 이력에서 구매 ${num(p.pay_events)}행 / ${num(p.paying_users)}명, 환불 ${num(p.refund_events)}행 / ${num(p.refunding_users)}명, 쿠폰 등록 ${num(p.coupon_events)}행 / ${num(p.coupon_users)}명. 서로 다른 사건의 단순 건수이며 거래·갱신 건수로 확정하지 않습니다.`;
  byId('coverage-summary').textContent=`첫 관측 후 14일 이후 이벤트가 있는 이력은 ${num(r.sample.users_with_event_at_or_after_day14)}명, 없는 이력은 ${num(r.sample.users_without_event_at_or_after_day14)}명입니다. 후자의 마지막 활동일을 관측 종료일로 간주하지 않습니다.`;
  byId('source-summary').textContent=`공식 ZIP의 ${num(m.population_user_files)}개 사용자 파일에서 행동을 보기 전에 고정한 해시로 ${num(m.sample_users)}명을 선정했습니다. 사용자별 일부 행이 아니라 해당 파일 전체를 확보했습니다. KT4 수집 시작은 공식 설명상 2018-08-27이며 공개 시각은 이동되어 실제 달력일·개인별 관찰 종료는 확인되지 않습니다.`;
  byId('external-validation').textContent=`SQL과 별도 pandas 계산으로 ${num(r.validation.compared_user_rows)}명 대조, 불일치 없음. 전체 보고서 반복 실행 일치. 선택된 파일의 SHA256과 ZIP CRC를 검사했으며 원본 ZIP 전체 SHA256을 확인했다고 주장하지 않습니다.`;
  draw();byId('external-app').hidden=false;
 }catch(e){extra=null;byId('external-error').hidden=false;}finally{byId('external-loading').hidden=true;if(restoreFocus)(extra?byId('external-title'):byId('external-retry')).focus();}
}
byId('event-definition').onchange=draw;byId('external-retry').onclick=load;load();

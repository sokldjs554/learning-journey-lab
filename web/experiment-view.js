'use strict';
let readiness;
function renderRecruitment(){
 if(!readiness)return;
 const p=Number(document.getElementById('baseline').value),d=Number(document.getElementById('mde').value);
 const rows=readiness.recruitment_scenarios.filter(x=>x.baseline===p&&x.mde===d);
 document.getElementById('recruitment-scenarios').innerHTML=`<div class="table-wrap" tabindex="0" role="region" aria-label="가상 유입별 모집 기간"><table><caption>실제 유입 미측정 · 주간 단위 모집 + 14일 관찰 + 가상 지연 유예 1일</caption><thead><tr><th>가상 일일 적격 유입</th><th>모집</th><th>관찰·유예 포함</th></tr></thead><tbody>${rows.map(x=>`<tr><th scope="row">${x.hypothetical_daily_eligible}명</th><td>${x.recruitment_days}일</td><td>${x.total_days_upper_bound}일</td></tr>`).join('')}</tbody></table></div>`;
}
async function loadReadiness(){
 const box=document.getElementById('experiment-checks');
 const restoreFocus=box.contains(document.activeElement);
 try{
  readiness=await EvidenceExtension.load('experiment-readiness.json','experiment');
  const labels={clean:'정상 계약',cross_variant:'동일 계정 교차군 배정',late_arrival:'유예 초과 지연 수신'};
  box.innerHTML=`<ul>${Object.entries(readiness.synthetic_cases).map(([key,c])=>`<li>${labels[key]||key}: <strong>${c.status==='hold'?'판정 보류 · 차이 숨김':'합성 입력 검사 통과'}</strong></li>`).join('')}</ul><p>실제 서비스 실험 참여자 0명 · 재방문 개선 효과 미측정. 위 통과는 배포 승인이나 실제 실험 성과를 의미하지 않습니다.</p>`;
  renderRecruitment();
 }catch(e){readiness=null;box.textContent='실험 검사 근거를 확인할 수 없습니다. 실제 실험 준비가 완료된 것으로 간주하지 않습니다.';const retry=document.createElement('button');retry.type='button';retry.textContent='검사 근거 다시 불러오기';retry.onclick=loadReadiness;box.append(retry);document.getElementById('recruitment-scenarios').textContent='모집 시나리오 확인 불가';}
 finally{if(restoreFocus)(box.querySelector('button')||box).focus();}
}
document.getElementById('baseline').addEventListener('change',renderRecruitment);document.getElementById('mde').addEventListener('change',renderRecruitment);loadReadiness();

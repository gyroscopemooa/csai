
async function specialPreviewPage(){
  if(!me.sample_tools||me.demo_view!=='developer')return pageTop('SPECIAL 패키지','개발 검수 전용 화면입니다.');
  const x=await api('/api/special/preview');
  const packages=[
    ['special_intelligence','고급 지능 패키지','Advanced Intelligence','고객과 사업에 대한 기억 및 복합 정보 이해 확장.',['능동형 정보 탐색 (Agentic RAG)','관계형 지식 분석 (GraphRAG)','장기·시간 기반 기억','멀티모달 정보 처리']],
    ['special_learning','고급 교육 패키지','Advanced Learning','상담 역량을 진단하고 교육 개선 방향을 제안.',['교육자료 심층 분석','지식 부족 및 충돌 탐지','모의 상담 및 역량 평가','교육 전후 성능 비교']],
    ['special_automation','고급 업무 패키지','Advanced Automation','여러 업무를 판단하고 연결하여 처리.',['역할별 AI 협업 (Multi-Agent)','외부 업무 도구 연결 (MCP)','다단계 업무 수행','업무 처리 및 결과 검증']]
  ];
  return pageTop('SPECIAL 패키지','개발 검수 · 출시 전 구성 미리보기')+
    '<div class="sp-preview">'+
    '<section class="sp-section"><div class="sp-heading"><div><small>Special All-in-One</small><h2>스페셜 올인원 패키지</h2></div><strong>'+e(money(x.packages.special_all))+'<small> / 월 추가</small></strong></div><p>지능, 기억, 정밀 교육, 업무 수행 능력을 통합 확장하는 패키지.</p><ul>'+packages.flatMap(p=>p[4]).map(f=>'<li>'+e(f)+'</li>').join('')+'<li>종합 성장 대시보드 및 통합 보고서</li><li>특화 신규 기술 (미공개)</li></ul><div class="sp-note">개별 합계 '+e(money(x.individual_total))+' · 월 '+e(money(x.individual_total-x.packages.special_all))+' 절약 · 구매 비활성화</div></section>'+
    '<div class="sp-grid">'+packages.map(p=>'<section class="sp-section"><small>'+e(p[2])+'</small><h3>'+e(p[1])+'</h3><strong>'+e(money(x.packages[p[0]]))+'<small> / 월 추가</small></strong><p>'+e(p[3])+'</p><ul>'+p[4].map(f=>'<li>'+e(f)+'</li>').join('')+'</ul></section>').join('')+'</div>'+
    specialFixtureReport(x.report)+specialApprovedDiagnostics(x.diagnostics)+specialLookupPanel()+
    '<p class="sp-note">기존 요금제 및 기능은 유지됩니다. 신규 기능은 개발 중이며 현재 구매하거나 실행할 수 없습니다.</p></div>';
}

function specialFixtureReport(r){
  const latest=r?.latest, comparison=r?.comparison;
  const rows=[['평가 사례 수',latest?latest.evaluated_cases:'미측정'],['검증 통과율',latest?(latest.check_pass_rate*100).toFixed(1)+'%':'미측정'],['교육 전후 개선 사례',comparison?comparison.improved_cases:'비교 자료 없음']];
  const trend=(r?.trend||[]).filter(p=>Number.isInteger(p.total)&&p.total>0&&Number.isInteger(p.passed)&&p.passed>=0&&p.passed<=p.total);
  return '<section class="sp-section"><h2>검색 검수 결과 및 이력</h2><p class="sp-note">고정된 가상 FAQ를 이용한 실제 검색 검사 결과입니다. 고객 상담 품질 또는 실제 AI 성장 점수가 아닙니다.</p><button type="button" class="primary" onclick="runSpecialFixture(this)">무료 검색 검수 실행</button><div class="sp-table-wrap"><table><thead><tr><th>평가 항목</th><th>측정 결과</th></tr></thead><tbody>'+rows.map(([k,v])=>'<tr><td>'+e(k)+'</td><td>'+e(String(v))+'</td></tr>').join('')+'</tbody></table></div>'+ (trend.length?'<div class="sp-trend">'+trend.map(p=>'<div><span>'+e(new Date(p.finished_at*1000).toISOString().slice(0,10))+'</span><progress max="'+p.total+'" value="'+p.passed+'"></progress><span>'+p.passed+'/'+p.total+'</span></div>').join('')+'</div>':'<p>아직 측정된 결과가 없습니다.</p>')+'<p class="sp-note">하루 1회 기록 · 별도 로컬 저장소 · API 사용 및 결제 없음</p></section>';
}
async function runSpecialFixture(button){
  button.disabled=true;
  try{await api('/api/special/preview/evaluate',{});await render();}
  catch(err){button.disabled=false;const p=document.createElement('p');p.setAttribute('role','alert');p.textContent=err.message;button.after(p);}
}

function specialApprovedDiagnostics(d){
  const items=[['승인된 FAQ 항목','total'],['서로 다른 질문','distinct_questions'],['중복 항목','duplicate_count'],['확인 필요 답변 그룹','review_group_count'],['잘못된 형식','invalid_count']];
  const measured=d?.status==='measured'&&items.every(([,k])=>Number.isSafeInteger(d[k])&&d[k]>=0);
  return '<section class="sp-section"><h2>승인된 교육자료 진단</h2><p>현재 업체의 공개 승인된 FAQ만 읽어 중복과 검토가 필요한 답변을 확인합니다.</p><div class="sp-table-wrap"><table><thead><tr><th>진단 항목</th><th>결과</th></tr></thead><tbody>'+items.map(([label,key])=>'<tr><td>'+e(label)+'</td><td>'+e(measured?String(d[key]):'미측정')+'</td></tr>').join('')+'</tbody></table></div><p class="sp-note">동일하게 정규화된 질문에 다른 답변이 있는 경우 검토 대상으로 집계합니다. 실제 오류를 확정하거나 교육자료를 자동 변경하지 않습니다.</p></section>';
}

function specialLookupPanel(){
  return '<section class="sp-section"><h2>승인 FAQ 검색 비교</h2><p>현재 업체의 승인 FAQ를 대상으로 문자 기반 검색과 확장 검색의 후보 질문을 비교합니다. 실제 고객 답변 또는 의미 기반 벡터 검색이 아닙니다.</p><form onsubmit="runSpecialLookup(this);return false"><label for="special-lookup-query">검수 질문</label><input id="special-lookup-query" name="query" maxlength="200" required placeholder="예: 물건 언제 와요?"><button class="primary" type="submit">검색 비교</button></form><div class="sp-lookup-result" aria-live="polite"></div><p class="sp-note">외부 API 호출 및 질문 저장 없음 · 승인 FAQ 질문만 표시</p></section>';
}
async function runSpecialLookup(form){
  const button=form.querySelector('button'),out=form.parentElement.querySelector('.sp-lookup-result');
  button.disabled=true;out.textContent='검색 중';
  try{
    const r=await api('/api/special/preview/lookup',{query:form.elements.query.value});
    if(r.status!=='compared'){out.textContent='현재 비교할 수 없습니다.';return;}
    const cols=[['기존 문자 검색',r.legacy],['확장 검색',r.pilot]];
    out.innerHTML='<p>검수 대상 '+e(String(r.approved_count))+'개</p><div class="sp-table-wrap"><table><thead><tr><th>검색 방식</th><th>후보 질문</th></tr></thead><tbody>'+cols.map(([name,rows])=>'<tr><td>'+e(name)+'</td><td>'+((rows||[]).length?rows.map(s=>e(s)).join('<br>'):'후보 없음')+'</td></tr>').join('')+'</tbody></table></div>';
  }catch(err){out.textContent=err.message;}finally{button.disabled=false;}
}

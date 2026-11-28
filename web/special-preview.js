
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
    '<section class="sp-section"><h2>교육 성과 및 성장 이력</h2><div class="sp-table-wrap"><table><thead><tr><th>평가 항목</th><th>측정 결과</th></tr></thead><tbody>'+['평가 사례 수','검증 통과율','교육 전후 개선 사례','성장 추이'].map(t=>'<tr><td>'+e(t)+'</td><td>미측정</td></tr>').join('')+'</tbody></table></div><p class="sp-note">현재 결과 저장소와 화면은 연결되지 않았습니다. 실제 측정값이 생성되기 전에는 점수 또는 그래프를 표시하지 않습니다.</p></section>'+
    '<p class="sp-note">기존 요금제 및 기능은 유지됩니다. 신규 기능은 개발 중이며 현재 구매하거나 실행할 수 없습니다.</p></div>';
}

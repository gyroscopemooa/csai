/* Public-facing document collection. No AI, account or billing mutations. */
let spSelectedDocument='intro';
const spDocuments={
 intro:{title:'서비스 소개서',english:'SERVICE INTRODUCTION',headline:'나처럼 상담하고,\n함께 성장하는 직원.',lead:'사업주가 직접 교육하고 고객 상담부터 예약과 업무 관리까지 연결하는 CS AI.',notice:'기능별 이용 가능 여부는 가입 유형, 설정, 개발 및 외부 연동 상태에 따라 달라질 수 있습니다.',chapters:[
 {title:'사업주를 대신하는 상담직원',lead:'고객에게 일관된 답변을 제공하고, 사업주는 중요한 일에 집중할 수 있도록 돕습니다.',groups:[['나의 응대 방식','인사, 말투, 상품 설명, 운영 정책을 교육해 업체에 맞는 상담원을 구성합니다.'],['고객 접점 확대','상담 링크와 웹 채팅을 이용하고, 지원되는 외부 채널은 별도 연동 조건에 따라 연결합니다.'],['필요한 순간에 직접 응대','복잡하거나 확인이 필요한 문의는 담당자가 직접 상담하고 답변을 보완할 수 있도록 설계합니다.']]},
 {title:'직접 교육하고 확인하는 과정',lead:'사업주가 관리하는 교육자료를 중심으로 상담원의 지식을 구성합니다.',groups:[['자료 등록','상품 정보, 영업시간, 정책, FAQ와 지원되는 문서 등을 등록합니다.'],['교육 내용 검토','분석 결과를 확인하고 필요하면 수정합니다.'],['승인 및 상담 테스트','승인한 내용으로 상담을 시험하고, 부족한 답변을 다시 교육할 수 있습니다.']]},
 {title:'문의부터 업무까지 연결',lead:'상담의 목적을 파악하고 적절한 업무 흐름으로 연결하는 서비스입니다.',groups:[['통합 상담함','문의와 상담 기록을 모아 보고 담당자 응대를 관리합니다.'],['예약 및 일정','설정한 영업시간, 담당자, 예약 조건을 바탕으로 일정 확인과 신청을 지원합니다.'],['고객·업무 관리','견적 요청, 민원, 후속 업무, 고객 정보를 관리하는 기능을 제공합니다.']]},
 {title:'다양한 업종에 맞는 활용',lead:'업종과 사업장 규모에 따라 교육할 정보와 업무 범위를 선택할 수 있습니다.',groups:[['온라인 쇼핑몰','상품, 옵션, 배송, 교환·환불 안내. 실제 주문 조회는 권한과 연동 여부에 따릅니다.'],['예약형 서비스','미용, 촬영, 교육, 상담 등 일정과 이용 조건 안내 및 예약 접수.'],['전문 서비스 및 소규모 사업장','서비스 소개, 상담 신청, 견적 문의, 반복 질문에 대한 안내.']]},
 {title:'계속 발전하는 서비스',lead:'현재 교육·상담 체계를 유지하면서 고객 경험을 높이는 기술을 단계적으로 검토합니다.',groups:[['더 정확한 답변','의미 기반 자료 검색, 맥락 이해와 답변 근거 검증을 강화할 계획입니다.'],['더 자연스러운 기억','허용된 고객 이력과 업체의 최신 정책을 구분하여 참고하도록 발전시킵니다.'],['더 넓은 업무 연결','모의 상담, 교육 개선 제안, 전문 역할과 외부 업무 도구의 지원 범위를 확장할 계획입니다.']]}
 ]},
 proposal:{title:'사업 도입 제안서',english:'BUSINESS PROPOSAL',headline:'고객 상담의 새로운 기준,\n우리 사업에 맞는 AI.',lead:'반복 상담은 효율적으로, 중요한 고객과 업무는 더욱 세심하게. CS AI 도입 제안.',notice:'일반적인 사업장 도입 제안이며, 실제 계약·가격·제공 기능과 성과는 개별 협의 및 검증을 따릅니다.',chapters:[
 {title:'사업장의 과제와 도입 목적',lead:'고객 문의가 늘어날수록 상담, 일정, 고객 정보와 후속 업무를 함께 관리할 필요가 있습니다.',groups:[['반복 문의 부담','동일한 상품 정보나 영업시간, 이용 절차를 여러 번 안내하는 부담을 줄입니다.'],['업무시간 외 문의','영업 종료 후에도 허용된 범위의 안내와 문의 접수를 지원합니다.'],['응대 일관성','업체별 승인 교육자료에 기반해 직원 간 안내 차이를 줄이는 것을 목표로 합니다.']]},
 {title:'제안하는 운영 구조',lead:'사업주가 운영 기준을 정하고 AI와 담당자가 역할을 분담합니다.',groups:[['AI 상담원','등록된 자료를 참고해 반복 문의와 일반적인 안내를 처리합니다.'],['담당자','확인이 필요한 문의, 예외 조건, 분쟁, 중요 업무를 검토합니다.'],['사업주','교육자료, 서비스 정책, 담당자 권한과 업무 기준을 관리합니다.']]},
 {title:'업종별 적용 시나리오',lead:'업체가 실제로 운영하는 서비스와 정책을 바탕으로 도입 범위를 구성합니다.',groups:[['판매업','상품 문의에서 구매 안내로 연결하고 고객 문의 이력을 관리합니다.'],['예약업','이용 조건 안내, 가능 일정 확인, 예약 접수 및 변경 요청 관리.'],['서비스업','상담 신청, 견적 요청, 고객 요구사항과 후속 업무 관리.']]},
 {title:'단계별 도입 절차',lead:'처음부터 모든 기능을 도입할 필요는 없습니다.',groups:[['01 · 요구사항 확인','업종, 고객 채널, 주요 문의, 예약·견적 등 필요한 업무를 확인합니다.'],['02 · 교육 및 설정','상품·서비스 자료를 등록하고 말투, 응대 범위, 담당자 전환 조건을 설정합니다.'],['03 · 시범 운영','실제와 유사한 질문을 시험하여 정확도, 예외 응대, 업무 흐름을 확인합니다.'],['04 · 운영 및 개선','확인된 기능부터 운영하고 미학습 문의와 담당자 피드백을 바탕으로 교육을 보완합니다.']]},
 {title:'도입 효과 및 검증 방법',lead:'실제 상담 데이터를 기반으로 도입 전후를 비교하며 효과를 확인합니다.',groups:[['상담 대응','첫 응답까지 걸리는 시간과 반복 문의 처리 비율을 비교합니다.'],['업무 연결','예약·견적·후속 업무의 누락 여부와 담당자 연결을 확인합니다.'],['고객 경험','답변 정확성, 만족도, 재문의 및 예외 대응을 점검합니다.'],['사업주 업무','직접 상담에 필요한 시간과 교육·관리 편의성을 확인합니다.']]},
 {title:'도입 범위 및 이용 조건',lead:'필요한 기능과 운영 환경을 확인하여 업체별로 적합한 이용 구성을 제안합니다.',groups:[['기본 상담 구성','업체 교육, 상담원 설정, 상담 링크 및 상담 기록 관리.'],['선택 구성','예약, 추가 상담원, 다국어, 업무 관리 및 지원되는 외부 채널 연동 등.'],['이용 안내','현재 제공되는 기능과 이용 요금은 로그인 후 요금제 및 전체 기능 메뉴에서 확인할 수 있습니다.'],['협의 및 확인','필요한 경우 도입 범위, 외부 연동 조건, 이용 지원 및 검증 기준을 개별적으로 정합니다.']]}
 ]},
 tech:{title:'기술 및 발전 계획서',english:'TECHNOLOGY & ROADMAP',headline:'더 정확하게 이해하고,\n더 넓게 연결하는 상담.',lead:'지식 검색, 기억, 교육, 업무 연결을 단계적으로 발전시키는 기술 방향.',notice:'현재 기능의 기본 방향과 향후 도입을 검토하는 기술을 설명합니다. 계획 기능의 출시 시기와 제공 범위는 개발·검증 조건에 따라 달라질 수 있습니다.',chapters:[
 {title:'나의 사업을 이해하는 상담직원',lead:'사업주가 직접 가르치고, 자신의 업무 방식에 맞춰 운영하는 AI 상담원입니다.',groups:[
 ['AI 교육','상품, 가격, 영업시간, 응대 방식, 정책, 자주 묻는 질문을 교육합니다. 교육 내용을 검토하고 승인한 뒤 상담에 반영하는 방식입니다.'],
 ['맞춤형 상담','업체별 교육자료와 말투를 참고해 고객 문의에 답변합니다. 확인할 수 없는 정보는 추측하지 않고 담당자 확인으로 연결합니다.'],
 ['통합 상담과 업무','고객 문의, 예약, 견적, 민원, 후속 업무를 한곳에서 관리하는 방향으로 제공합니다. 실제 이용 가능 범위는 계정 및 연결 상태에 따라 다릅니다.'],
 ['기존 교육 체계 유지','기존 교육 방식과 승인 절차, 상담원 설정 및 크레딧 체계를 바꾸지 않습니다. 이후 기술은 기존 상담원을 보완하는 방식으로 단계적으로 도입합니다.']]},
 {title:'필요한 정보를 정확하게 찾아 답변',lead:'교육자료가 많아져도 고객에게 필요한 정보만 찾아 참고하는 지식 검색 기술의 도입 계획입니다.',groups:[
 ['RAG · 검색 증강 생성','고객이 질문하면 등록된 자료에서 관련 정보를 먼저 찾고, 이를 참고해 답변하는 방식입니다.'],
 ['Vector / Hybrid RAG · 의미·혼합 검색','문자 그대로 일치하는 상품번호와 의미가 같은 질문을 함께 검색합니다. 예: “물건 언제 와요?”와 “배송 소요 기간”.'],
 ['Contextual RAG · 맥락 검색','환불 기간뿐 아니라 해당 규정이 적용되는 상품, 구매 방식, 정책을 함께 찾아 혼동을 줄이는 기술입니다.'],
 ['Reranking · 검색 결과 재정렬','검색한 자료 가운데 현재 문의와 가장 관련 있는 자료를 다시 선별해 답변에 활용합니다.'],
 ['Adaptive / Agentic RAG · 적응형·능동 검색','간단한 문의는 바로 처리하고, 복잡한 질문은 필요한 정보를 추가로 찾아 비교합니다. 추가 검색은 필요한 경우에만 실행합니다.'],
 ['GraphRAG · 관계 기반 검색','상품, 옵션, 가격, 배송, 환불 규정 사이의 관계를 연결해 복합 질문을 처리하는 기술입니다. 실제 필요성이 확인되는 분야부터 검토합니다.'],
 ['Multimodal RAG · 문서·이미지 검색','텍스트뿐 아니라 표, PDF, 사진, 매뉴얼의 관련 정보를 찾아 응대에 활용하는 기능을 단계적으로 확장합니다.']]},
 {title:'고객과 업무를 기억하는 상담원',lead:'현재 상담뿐 아니라 허용된 이전 상담과 업체 지식을 참고할 수 있도록 기억 체계를 확장할 계획입니다.',groups:[
 ['Short-term Memory · 단기 기억','현재 고객과 나누는 대화의 흐름과 직전 질문을 참고합니다.'],
 ['Long-term / Episodic Memory · 장기·경험 기억','본인 확인과 허용 범위 내에서 고객의 과거 문의와 해결 이력을 참고할 수 있도록 합니다.'],
 ['Semantic / Procedural Memory · 지식·업무 기억','상품, 규정, 응대 방식, 예약 절차 등 업체별 사실과 업무 순서를 구분해 관리합니다.'],
 ['Temporal Memory · 시간 기반 기억','변경 전 가격과 최신 가격, 과거 정책과 현재 정책을 구분합니다.'],
 ['Memory Consolidation · 기억 통합','중복 기억을 정리하고 긴 상담을 요약하여 필요한 정보만 활용합니다.'],
 ['Knowledge Versioning · 지식 버전 관리','교육자료의 변경·승인·복원 이력을 관리하고 최신 승인 정보를 우선합니다.']]},
 {title:'효율적으로 응대하는 상담 기술',lead:'기존 품질을 기준으로 검증하며 반복적인 작업을 줄이고 상담의 일관성과 처리 효율을 높이는 기술 계획입니다.',groups:[
 ['Exact / Semantic Cache · 답변 재사용','동일한 질문 또는 조건이 동일한 유사 질문에 승인된 답변을 재사용합니다. 업체·상품·정책 변경을 구분하고 개인 주문·실시간 정보는 제외합니다.'],
 ['Prompt Caching · 반복 지침 최적화','공통 상담 지침을 효율적으로 처리해 반복 작업을 줄입니다.'],
 ['Context Compression · 맥락 압축','답변에 필요한 대화와 자료를 남겨 불필요한 정보 전달을 줄입니다.'],
 ['Intelligent Routing · 지능형 처리 경로','간단한 문의와 복잡한 문의의 처리 방식을 구분합니다. 기존 품질을 유지할 수 있는 경우에만 적용합니다.'],
 ['Incremental Indexing · 자료 갱신','변경된 교육자료를 신속하게 검색에 반영합니다.'],
 ['Deterministic Processing / Batch Processing · 규칙·일괄 처리','가격 계산, 일정 충돌 확인처럼 정확한 규칙이 있는 일은 서버에서 검증하고, 즉시 응답이 필요 없는 작업은 일괄 처리합니다.']]},
 {title:'교육받고 성장하는 AI 상담원',lead:'AI가 임의로 정책을 바꾸는 것이 아니라, 실제 상담에서 부족한 부분을 찾아 사업주가 개선할 수 있도록 지원하는 계획입니다.',groups:[
 ['Active Learning / Feedback Learning · 개선 후보 수집','미학습 질문, 상담 실패, 고객 평가, 상담원의 수정 답변을 모아 교육 후보로 제안합니다.'],
 ['Human-in-the-loop · 사업주 검토','새로운 답변이나 정책은 검토와 승인을 거쳐 반영합니다. 기존 교육 및 승인 절차를 유지합니다.'],
 ['Knowledge Gap / Conflict Detection · 지식 누락·충돌 검사','빠진 자료와 서로 다른 정책을 찾아 확인을 요청합니다.'],
 ['Synthetic Data / 모의 상담','가상의 고객 질문으로 다양한 상황을 시험해 실제 상담 전 부족한 부분을 발견합니다.'],
 ['Regression Testing / 답변 품질 평가','새로운 교육을 추가한 뒤 기존 상담 정확도, 말투, 문제 해결 및 예외 대응이 유지되는지 비교합니다.'],
 ['검증 사례 재활용','검토된 우수 상담 사례와 지침을 활용하여 반복 상담 품질을 개선합니다. 모델 자체를 재학습한다는 의미는 아닙니다.']]},
 {title:'상담에서 실제 업무까지',lead:'상담 중 발견한 고객 요청이 업무로 이어지도록 연결 기술과 처리 권한을 확장할 계획입니다.',groups:[
 ['Function Calling / Structured Outputs · 업무 도구 연결','고객 문의에서 필요한 정보를 정리해 예약, 상품 조회, 견적 등 승인된 기능에 전달합니다.'],
 ['Agentic Workflow · 단계별 업무 처리','문의 접수, 정보 확인, 조건 검증, 고객 확인, 업무 기록 등 정해진 순서에 따라 처리합니다.'],
 ['MCP · 외부 도구 연결 규격','외부 서비스와 AI가 정해진 방식으로 정보를 주고받도록 연결하는 기술입니다. 실제 연동은 제공사 승인과 권한 검증 후 제공합니다.'],
 ['Multi-Agent · 전문 상담 역할','일반 상담, 예약, 상품 안내, 견적, 민원 등 업무에 맞는 지침과 권한을 구분합니다. 반드시 여러 모델을 사용하는 것은 아닙니다.'],
 ['Human Approval / Event-driven Agent · 승인·이벤트 처리','중요 업무는 고객 또는 담당자의 확인을 거치고, 허용된 신규 문의·예약 이벤트에 맞춰 후속 처리를 지원합니다.']]},
 {title:'신뢰할 수 있는 상담과 데이터 관리',lead:'잘못된 답변, 정보 혼동, 무단 업무 실행을 줄이는 검증 체계를 지속적으로 보완합니다.',groups:[
 ['Grounded Generation / Source Attribution · 근거 기반 답변','등록된 자료에 근거하여 답변하고, 사용한 교육자료를 확인할 수 있는 기능을 확장합니다.'],
 ['Guardrails / Confidence Checks · 안전 검증','확인되지 않은 가격, 재고, 환불, 예약 가능 여부를 임의로 확정하지 않도록 검증합니다.'],
 ['Tenant Isolation / Access Control · 업체·권한 분리','업체별 데이터와 직원 권한을 구분하고 고객정보의 접근·보관·삭제 범위를 관리합니다.'],
 ['Prompt Injection / PII Protection · 지침·개인정보 보호','고객 메시지와 문서 속 외부 지시를 신뢰하지 않고 내부 정보와 개인정보 노출을 방지하도록 검증합니다.'],
 ['Audit Logging / Idempotency · 기록·중복 방지','업무 수행 이력을 남기고 예약·결제·요청이 중복 처리되지 않도록 서버에서 검증합니다.'],
 ['Fallback · 담당자 연결','답변 근거가 부족하거나 업무 권한이 없으면 확인을 요청하거나 담당자에게 연결하는 방식으로 처리합니다.']]},
 {title:'단계별 서비스 발전 계획',lead:'기존 기능을 교체하는 계획이 아니라, 현재 교육 및 상담 체계 위에 기능을 추가하고 검증하는 계획입니다.',groups:[
 ['1단계 · 검색 및 효율화','혼합·맥락 검색, 결과 재정렬, 검증된 답변 재사용, 상담 품질 검증, 안전 검증을 우선 검토합니다.'],
 ['2단계 · 기억 및 교육 개선','장기·시간 기반 기억, 상담 요약, 모의 상담, 교육 개선 제안, 충돌 검증, 품질 평가를 확장합니다.'],
 ['3단계 · 고급 상담과 업무 연결','능동형 검색, 문서·이미지 검색, 업무 도구 연결, 전문 상담 역할을 필요한 분야부터 적용합니다.'],
 ['4단계 · 선택적 고급 기술','복잡한 관계형 지식 등 실제 고객 필요와 활용 효과가 검증된 기술을 적용합니다.'],
 ['향후 추가 서비스 검토','모의 상담, 교육자료 정밀 분석, 품질 리포트, 장기 기억, 전문 상담원 등은 별도 제공 여부 및 이용 조건을 검토합니다. 현재 요금이나 크레딧을 변경하는 안내는 아닙니다.'],
 ['공통 원칙','기존 기능과 요금 체계를 임의 변경하지 않습니다. 검색 정확도, 상담 품질, 응답 속도, 개인정보 보호 수준을 검증하고 단계적으로 공개합니다.']]}
 ]}
};
const spVisuals={
 intro:[['flow','업체 교육','맞춤 상담','업무 연결'],['flow','자료 등록','검토·승인','상담 테스트'],['hub','통합 상담','고객 문의','예약·일정','견적·민원','후속 업무'],['tiles','쇼핑몰','예약 사업장','전문 서비스'],['flow','지식 검색','상담 기억','업무 확장']],
 proposal:[['tiles','반복 문의','응대 공백','안내 일관성'],['hub','사업주 기준','AI 상담','담당자 검토','교육 관리','고객 응대'],['tiles','상품 안내','예약 접수','견적 문의'],['flow','요구 확인','교육 설정','시범 운영','운영 개선'],['tiles','응답 시간','처리 품질','업무 연결','고객 경험'],['flow','기본 상담','선택 기능','도입 협의']],
 tech:[['flow','업체 지식','맞춤 상담','업무 연결'],['flow','고객 질문','관련 자료 검색','근거 선별','답변'],['hub','상담 기억','현재 대화','이전 문의','업체 지식','최신 정책'],['flow','고객 질문','검증 답변 확인','필요한 정보 처리','상담 응답'],['cycle','상담','개선 후보','사업주 승인','교육 반영'],['hub','업무 연결','예약','상품 조회','견적','담당자 확인'],['flow','자료 확인','권한 검증','답변·업무','기록'],['flow','검색·검증','기억·교육','업무 확장','선택 기술']]
};
function spEscape(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function spDiagram(spec,cover=false){
 const [kind,...labels]=spec;
 const t=(x,y,s,size=15)=>'<text x="'+x+'" y="'+y+'" font-size="'+size+'" font-weight="600" text-anchor="middle" fill="#203d60">'+spEscape(s)+'</text>';
 const rect=(x,y,w,h,s,fill='#f1f6fb')=>'<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" rx="11" fill="'+fill+'" stroke="#b5c8dc"/>'+t(x+w/2,y+h/2+5,s,labels.length>3?13:15);
 const line=(x1,y1,x2,y2)=>'<path d="M'+x1+' '+y1+' L'+x2+' '+y2+'" fill="none" stroke="#7997b6" stroke-width="2"/>';
 let parts='',height=124;
 if(kind==='hub'||kind==='cycle'){
  height=178;
  const cx=350,cy=89,ps=[[115,34],[585,34],[115,143],[585,143]];
  if(kind==='hub'){parts=ps.map(([x,y])=>line(cx,cy,x,y)).join('')+ps.map(([x,y],i)=>rect(x-86,y-23,172,46,labels[i+1])).join('')+rect(265,63,170,52,labels[0],'#dceaf9');}
  else{parts=line(115,34,585,34)+line(585,34,585,143)+line(585,143,115,143)+line(115,143,115,34)+ps.map(([x,y],i)=>rect(x-86,y-23,172,46,labels[[0,1,3,2][i]])).join('')+t(350,94,'지속적 개선',19)+t(350,29,'→',20)+t(590,94,'↓',20)+t(350,164,'←',20)+t(110,94,'↑',20);}
 }else{
  const n=labels.length,w=(660-(n-1)*24)/n;
  parts=labels.map((s,i)=>{const x=20+i*(w+24);return rect(x,35,w,54,s,i===n-1?'#dceaf9':'#f1f6fb')+(i<n-1&&kind==='flow'?t(x+w+12,68,'→',19):'');}).join('');
 }
 const label=labels.join(' / ');
 return '<figure class="sp-figure'+(cover?' sp-cover-figure':'')+'"><svg viewBox="0 0 700 '+height+'" role="img" aria-label="'+spEscape(label)+'" xmlns="http://www.w3.org/2000/svg">'+parts+'</svg><figcaption>개념도 · '+spEscape(label)+'</figcaption></figure>';
}
function spCoverIllustration(key){
 const title=key==='proposal'?'사업 운영의 연결':key==='tech'?'지식과 업무의 연결':'업체와 고객의 연결';
 return '<figure class="sp-illustration"><svg viewBox="0 0 700 210" role="img" aria-label="'+title+'" xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="700" height="210" rx="14" fill="#edf4fb"/><path d="M166 106H282M418 106H534" stroke="#7896b7" stroke-width="2" stroke-dasharray="5 5"/><rect x="46" y="47" width="120" height="118" rx="13" fill="#fff" stroke="#b4c9df"/><path d="M68 75h76M68 91h51M68 119h76M68 135h58" stroke="#7896b7" stroke-width="5" stroke-linecap="round"/><rect x="282" y="39" width="136" height="132" rx="16" fill="#284f7b"/><rect x="303" y="63" width="94" height="74" rx="10" fill="#f1f6fc"/><path d="M315 82h70M315 98h50M315 114h61" stroke="#7999b9" stroke-width="5" stroke-linecap="round"/><text x="350" y="157" text-anchor="middle" fill="#fff" font-size="13" font-weight="700">CS AI</text><rect x="534" y="46" width="120" height="82" rx="13" fill="#fff" stroke="#b4c9df"/><path d="M550 67h88M550 84h58M550 101h75" stroke="#7896b7" stroke-width="5" stroke-linecap="round"/><rect x="557" y="137" width="97" height="37" rx="9" fill="#dceaf9" stroke="#b4c9df"/><path d="M570 155l7 6 10-12M594 155h43" stroke="#426b99" stroke-width="3" fill="none" stroke-linecap="round"/><text x="106" y="190" text-anchor="middle" fill="#315577" font-size="12">업체 교육</text><text x="594" y="190" text-anchor="middle" fill="#315577" font-size="12">고객 상담 · 업무</text></svg><figcaption>'+title+' · 서비스 개념 일러스트</figcaption></figure>';
}
function selectServiceDocument(key){
 if(!Object.prototype.hasOwnProperty.call(spDocuments,key))return;
 spSelectedDocument=key;
 const view=document.querySelector('.sp-view');
 if(!view)return;
 view.outerHTML=servicePlanPage();
 const active=document.querySelector('.sp-view [data-sp-doc="'+key+'"]');
 active?.focus({preventScroll:true});
 document.querySelector('.sp-view')?.scrollIntoView({block:'start'});
}
function servicePlanPage(){
 const key=spSelectedDocument,doc=spDocuments[key],chapters=doc.chapters,total=chapters.length+1;
 const footer=n=>'<footer class="sp-page-footer"><span>CS AI · '+doc.title+'</span><span>'+String(n).padStart(2,'0')+' / '+String(total).padStart(2,'0')+'</span></footer>';
 const index=chapters.map((ch,i)=>'<li><a href="#service-plan" onclick="document.getElementById(\'sp-ch-'+(i+1)+'\').scrollIntoView({block:\'start\'});return false"><span>'+String(i+1).padStart(2,'0')+'</span>'+spEscape(ch.title)+'</a></li>').join('');
 const pages=chapters.map((ch,i)=>'<section class="sp-sheet sp-chapter" id="sp-ch-'+(i+1)+'" aria-labelledby="sp-title-'+(i+1)+'"><div class="sp-kicker">CS AI / '+doc.english+' / '+String(i+1).padStart(2,'0')+'</div><h2 id="sp-title-'+(i+1)+'">'+spEscape(ch.title)+'</h2><p class="sp-lead">'+spEscape(ch.lead)+'</p>'+spDiagram(spVisuals[key][i])+'<dl class="sp-definitions">'+ch.groups.map(([name,desc])=>'<div><dt>'+spEscape(name)+'</dt><dd>'+spEscape(desc)+'</dd></div>').join('')+'</dl>'+footer(i+2)+'</section>').join('');
 const tabs=Object.entries(spDocuments).map(([id,d])=>'<button type="button" data-sp-doc="'+id+'" aria-pressed="'+(id===key)+'" onclick="selectServiceDocument(\''+id+'\')">'+d.title+'</button>').join('');
 return '<div class="sp-view"><header class="sp-toolbar"><div><h1>서비스 자료실</h1><p>서비스 소개, 사업 도입 제안, 기술 발전 계획을 확인하세요.</p></div><button type="button" class="ui-button" onclick="window.print()">인쇄 / PDF 저장</button></header><nav class="sp-doc-tabs" aria-label="자료 선택">'+tabs+'</nav><article class="sp-document" aria-label="'+doc.title+'"><section class="sp-sheet sp-cover"><div class="sp-kicker">CS AI / '+doc.english+'</div><div class="sp-cover-main"><p class="sp-cover-brand">CS AI</p><h2>'+spEscape(doc.headline).replace(/\n/g,'<br>')+'</h2><p class="sp-lead">'+spEscape(doc.lead)+'</p>'+spCoverIllustration(key)+'<div class="sp-notice"><strong>'+doc.title+'</strong><p>'+spEscape(doc.notice)+'</p></div></div><h3>목차</h3><ol class="sp-contents">'+index+'</ol>'+footer(1)+'</section>'+pages+'</article></div>';
}

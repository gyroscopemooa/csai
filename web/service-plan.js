/* Customer-facing service plan. Static presentation only; no engine or billing changes. */
function servicePlanPage(){
 const chapters=[
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
 ['Adaptive / Agentic RAG · 적응형·능동 검색','간단한 문의는 바로 처리하고, 복잡한 질문은 필요한 정보를 추가로 찾아 비교합니다. 검색 횟수와 비용은 제한합니다.'],
 ['GraphRAG · 관계 기반 검색','상품, 옵션, 가격, 배송, 환불 규정 사이의 관계를 연결해 복합 질문을 처리하는 기술입니다. 실제 필요성이 확인되는 분야부터 검토합니다.'],
 ['Multimodal RAG · 문서·이미지 검색','텍스트뿐 아니라 표, PDF, 사진, 매뉴얼의 관련 정보를 찾아 응대에 활용하는 기능을 단계적으로 확장합니다.']]},
 {title:'고객과 업무를 기억하는 상담원',lead:'현재 상담뿐 아니라 허용된 이전 상담과 업체 지식을 참고할 수 있도록 기억 체계를 확장할 계획입니다.',groups:[
 ['Short-term Memory · 단기 기억','현재 고객과 나누는 대화의 흐름과 직전 질문을 참고합니다.'],
 ['Long-term / Episodic Memory · 장기·경험 기억','본인 확인과 허용 범위 내에서 고객의 과거 문의와 해결 이력을 참고할 수 있도록 합니다.'],
 ['Semantic / Procedural Memory · 지식·업무 기억','상품, 규정, 응대 방식, 예약 절차 등 업체별 사실과 업무 순서를 구분해 관리합니다.'],
 ['Temporal Memory · 시간 기반 기억','변경 전 가격과 최신 가격, 과거 정책과 현재 정책을 구분합니다.'],
 ['Memory Consolidation · 기억 통합','중복 기억을 정리하고 긴 상담을 요약하여 필요한 정보만 활용합니다.'],
 ['Knowledge Versioning · 지식 버전 관리','교육자료의 변경·승인·복원 이력을 관리하고 최신 승인 정보를 우선합니다.']]},
 {title:'효율적으로 응대하는 상담 기술',lead:'기존 품질을 기준으로 검증하며 반복적인 작업과 불필요한 처리 비용을 줄이는 기술 계획입니다.',groups:[
 ['Exact / Semantic Cache · 답변 재사용','동일한 질문 또는 조건이 동일한 유사 질문에 승인된 답변을 재사용합니다. 업체·상품·정책 변경을 구분하고 개인 주문·실시간 정보는 제외합니다.'],
 ['Prompt Caching · 반복 지침 최적화','공통 상담 지침을 효율적으로 처리해 반복 작업을 줄입니다.'],
 ['Context Compression · 맥락 압축','답변에 필요한 대화와 자료를 남겨 불필요한 정보 전달을 줄입니다.'],
 ['Intelligent Routing · 지능형 처리 경로','간단한 문의와 복잡한 문의의 처리 방식을 구분합니다. 기존 품질을 유지할 수 있는 경우에만 적용합니다.'],
 ['Dynamic Budget / Incremental Indexing · 효율적 처리','문의별 처리 한도를 설정하고 변경된 교육자료만 다시 검색 가능하도록 갱신합니다.'],
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
 ['1단계 · 검색 및 효율화','혼합·맥락 검색, 결과 재정렬, 검증된 답변 재사용, 처리 비용 및 품질 측정, 안전 검증을 우선 검토합니다.'],
 ['2단계 · 기억 및 교육 개선','장기·시간 기반 기억, 상담 요약, 모의 상담, 교육 개선 제안, 충돌 검증, 품질 평가를 확장합니다.'],
 ['3단계 · 고급 상담과 업무 연결','능동형 검색, 문서·이미지 검색, 업무 도구 연결, 전문 상담 역할을 필요한 분야부터 적용합니다.'],
 ['4단계 · 선택적 고급 기술','복잡한 관계형 지식 등 실제 고객 필요와 비용 대비 효과가 검증된 기술을 적용합니다.'],
 ['향후 추가 서비스 검토','모의 상담, 교육자료 정밀 분석, 품질 리포트, 장기 기억, 전문 상담원 등은 별도 제공 여부 및 이용 조건을 검토합니다. 현재 요금이나 크레딧을 변경하는 안내는 아닙니다.'],
 ['공통 원칙','기존 기능과 요금 체계를 임의 변경하지 않습니다. 검색 정확도, 상담 품질, 응답 속도, 개인정보 보호, 운영 원가를 검증하고 단계적으로 공개합니다.']]}
 ];
 const index=chapters.map((ch,i)=>'<li><a href="#service-plan" onclick="document.getElementById(\'sp-ch-'+(i+1)+'\').scrollIntoView({block:\'start\'});return false"><span>'+String(i+1).padStart(2,'0')+'</span>'+ch.title+'</a></li>').join('');
 const pages=chapters.map((ch,i)=>'<section class="sp-sheet sp-chapter" id="sp-ch-'+(i+1)+'" aria-labelledby="sp-title-'+(i+1)+'"><div class="sp-kicker">CS AI / SERVICE DEVELOPMENT PLAN / '+String(i+1).padStart(2,'0')+'</div><h2 id="sp-title-'+(i+1)+'">'+ch.title+'</h2><p class="sp-lead">'+ch.lead+'</p><dl class="sp-definitions">'+ch.groups.map(([name,desc])=>'<div><dt>'+name+'</dt><dd>'+desc+'</dd></div>').join('')+'</dl><footer class="sp-page-footer"><span>CS AI · 서비스 소개 및 발전 계획</span><span>'+String(i+2).padStart(2,'0')+' / '+String(chapters.length+1).padStart(2,'0')+'</span></footer></section>').join('');
 return '<div class="sp-view"><header class="sp-toolbar"><div><h1>서비스 소개서</h1><p>CS AI의 서비스와 향후 기술 발전 방향을 확인하세요.</p></div><button type="button" class="ui-button" onclick="window.print()">인쇄 / PDF 저장</button></header><article class="sp-document" aria-label="CS AI 서비스 소개 및 발전 계획"><section class="sp-sheet sp-cover"><div class="sp-kicker">CS AI / SERVICE DEVELOPMENT PLAN</div><div class="sp-cover-main"><p class="sp-cover-brand">CS AI</p><h2>나를 이해하고,<br>함께 성장하는 상담직원.</h2><p class="sp-lead">업체별 교육과 기억, 지식 검색, 상담 및 업무 연결을 하나로.</p><div class="sp-notice"><strong>서비스 소개 및 발전 계획</strong><p>이 문서는 현재 서비스의 기본 방향과 향후 도입을 검토하는 기술을 설명합니다. 계획 기능의 출시 시기와 제공 범위는 개발·검증 및 연동 조건에 따라 달라질 수 있습니다.</p></div></div><h3>목차</h3><ol class="sp-contents">'+index+'</ol><footer class="sp-page-footer"><span>CS AI · 서비스 소개 및 발전 계획</span><span>01 / '+String(chapters.length+1).padStart(2,'0')+'</span></footer></section>'+pages+'</article></div>';
}

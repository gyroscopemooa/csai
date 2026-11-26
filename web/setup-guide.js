'use strict';
// Rule-based onboarding and subscription estimate. No LLM, provider calls, or entitlement changes.
const CSAISetup=(()=>{
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const won=v=>Number(v).toLocaleString('ko-KR')+'원';
 const index=cat=>Object.fromEntries([...cat.addons,...cat.packages].map(x=>[x.id,x]));
 function normalize(cat,ids){
  const by=index(cat),a=new Set(ids.filter(k=>by[k])),covered=new Set();
  const packs=cat.packages.filter(p=>a.has(p.id)).sort((x,y)=>y.includes.length-x.includes.length);
  for(const p of packs){if(p.includes.every(k=>covered.has(k))){a.delete(p.id);continue;}if(p.includes.some(k=>covered.has(k)))throw Error('중복 패키지를 함께 선택할 수 없습니다.');p.includes.forEach(k=>covered.add(k));}
  covered.forEach(k=>a.delete(k));
  if(covered.has('naver')&&covered.has('kakao'))a.delete('channels');
  else if(a.has('channels')){if(covered.has('naver')||covered.has('kakao'))throw Error('채널 옵션과 패키지가 중복됩니다.');a.delete('naver');a.delete('kakao');}
  for(const k of [...a])for(const dep of by[k].requires||[])if(!covered.has(dep))a.add(dep);
  const keys=[...a].sort(),discount=a.has('naver')&&a.has('kakao')?by.naver.price+by.kakao.price-by.channels.price:0;
  const features=new Set(covered);for(const k of keys)if(!by[k].includes){features.add(k);if(k==='channels'){features.add('naver');features.add('kakao');}}
  return {keys,features,discount,amount:keys.reduce((n,k)=>n+by[k].price,0)-discount};
 }
 function featureSet(x){const s=new Set(x.features);if(s.has('channels')){s.delete('channels');s.add('naver');s.add('kakao');}return s;}
 function cheaper(cat,ids){
  const current=normalize(cat,ids),need=featureSet(current);let best=null;
  const packs=cat.packages.filter(p=>p.includes.some(k=>need.has(k)));
  for(let mask=1;mask<(1<<packs.length);mask++){
   const selected=packs.filter((_,i)=>mask&(1<<i)),covered=new Set(selected.flatMap(p=>p.includes));
   const keys=[...selected.map(p=>p.id),...[...need].filter(k=>!covered.has(k))];
   try{const candidate=normalize(cat,keys);if([...need].every(k=>featureSet(candidate).has(k))&&candidate.amount<current.amount&&(!best||candidate.amount<best.amount))best=candidate;}catch{}
  }
  return best?{keys:best.keys,amount:best.amount,saving:current.amount-best.amount}:null;
 }
 const rules={
  education:['교육할 자료가 있나요? 기존 상담 내역, 문서, 홈페이지 또는 ChatGPT 내보내기 파일을 사용할 수 있습니다.','교육 방식 보기','education'],
  preview:['실제 고객처럼 질문해 상담원의 답변을 확인할 수 있습니다. 무료 제공량 이후에는 상담량이 차감됩니다.','상담 테스트','test'],
  test:['답변이 마음에 들지 않으면 교육 화면에서 수정해 주세요.','교육 수정','education'],
  calendar:['예약이 많은 사업이라면 일정표와 자동 예약을 구성할 수 있습니다.','자동 예약 알아보기','auto_booking'],
  fields:['예약 접수에 필요한 항목을 정리해 보세요.','일정표 알아보기','calendar'],
  'booking-settings':['예약 확인을 자동화하고 싶으신가요? 실제 자동 확정은 권한과 위험 안내 동의가 필요합니다.','자동 예약 알아보기','auto_booking'],
  customers:['상담을 고객·업무 기록으로 남기고 관리할 수 있습니다.','고객 CRM 알아보기','crm'],
  channels:['홈페이지에 상담창을 설치하면 고객이 별도 앱 없이 상담할 수 있습니다.','홈페이지 위젯 알아보기','widget'],
  agents:['서비스마다 상담원과 교육 자료를 독립적으로 운영할 수 있습니다.','추가 브랜드 상담원 알아보기','extra_agent'],
  settings:['브랜드와 고객 응대 방식을 설정할 수 있습니다.','고급 디자인 알아보기','design'],
  alerts:['새로운 상담을 놓치지 않도록 알림을 설정할 수 있습니다.','신규 상담 알림 알아보기','new_alert'],
  developer:['기존 서비스와 상담 기능을 서버 API로 연결할 수 있습니다.','외부 API 알아보기','external_api'],
  inbox:['상담 기록에서 잘못된 답변이나 미학습 질문을 찾아 교육을 보완할 수 있습니다.','교육 화면','education'],
  credits:['교육 크레딧은 월 구독료와 별도입니다. 실제 분석 전에 비용을 확인하세요.','크레딧 요금 보기','credits'],
  pricing:['필요한 기능만 선택하세요. 구독 구성표에서 예상 요금과 더 저렴한 패키지를 확인할 수 있습니다.','구독 구성표 열기','receipt'],
  orders:['주문과 구독 내역을 확인할 수 있습니다. 실제 결제 연동 여부는 결제 화면을 기준으로 확인하세요.','구독 구성표 열기','receipt']
 };
 const routes={widget:'channels',naver:'channels',kakao:'channels',channels:'channels',multilingual:'settings',extra_agent:'agents',design:'settings',unbrand:'settings',custom_url:'settings',domain:'channels',calendar:'calendar',auto_booking:'booking-settings',change_booking:'calendar',google_calendar:'channels',booking_alert:'alerts',crm:'customers',quote:'customers',tasks:'customers',leads:'customers',complaints:'customers',stats:'customers',export:'customers',retention:'inbox',external_api:'developer',custom_integration:'developer',push:'alerts',email:'alerts',unknown_alert:'alerts',new_alert:'alerts',report:'alerts'};
 const descriptions={calendar:'일정표에서 예약을 확인하고 수동으로 관리합니다.',auto_booking:'고객에게 예약 가능 시간을 안내하고 설정에 따라 접수 또는 확정합니다.',widget:'기존 홈페이지 안에 상담창을 설치합니다.',crm:'고객 문의와 업무 기록을 정리합니다.',extra_agent:'별도 상담 링크와 교육 지식을 가진 상담원을 구성합니다.',design:'채팅 테마와 색상 등 상담창 외형을 설정합니다.',new_alert:'신규 상담이 들어왔을 때 알림을 받습니다.',external_api:'구매한 기능을 서버 API로 호출합니다.'};
 let state=null,verified=null,pendingKey='',failedKey='',serial=0;
 const storageKey=()=> 'csai-setup-v1:'+me.slug;
 const all=()=>index(cfg.catalog);
 function save(){if(!state)return;try{sessionStorage.setItem(storageKey(),JSON.stringify({plan:selectedPlan,ids:[...selectedAdd],brandCount:selectedBrandCount,receipt:state.receipt,guide:state.guide,dismissed:[...state.dismissed],seen:[...state.seen],messages:state.messages.slice(-20)}));}catch{}}
 function initialize(){
  if(state?.slug===me.slug)return;
  serial++;verified=null;pendingKey='';failedKey='';
  state={slug:me.slug,receipt:false,guide:false,dismissed:new Set(),seen:new Set(),messages:[]};
  selectedPlan=me.plan==='free'?'lite':me.plan;selectedAdd=new Set(me.addons||[]);selectedBrandCount=me.brand_quantity||1;
  try{const d=JSON.parse(sessionStorage.getItem(storageKey())||'null');if(d){if(cfg.catalog.plans.some(p=>p.id===d.plan&&p.price>0))selectedPlan=d.plan;if(Array.isArray(d.ids))selectedAdd=new Set(d.ids.filter(k=>Object.hasOwn(all(),k)));if(Number.isInteger(d.brandCount)&&d.brandCount>=1&&d.brandCount<=1000)selectedBrandCount=d.brandCount;state.receipt=!!d.receipt;state.guide=!!d.guide;state.dismissed=new Set(d.dismissed||[]);state.seen=new Set(d.seen||[]);state.messages=Array.isArray(d.messages)?d.messages.filter(m=>['user','guide'].includes(m.role)&&typeof m.text==='string').slice(-20):[];}}catch{}
 }
 function current(){return normalize(cfg.catalog,[...selectedAdd]);}
 function plan(){return cfg.catalog.plans.find(p=>p.id===selectedPlan)||cfg.catalog.plans.find(p=>p.id==='lite');}
 function prompt(){
  let r=rules[route]||['필요한 기능을 둘러보고 구독 구성표에서 예상 요금을 확인할 수 있습니다.','구독 구성표 열기','receipt'];
  if(route==='education'&&Object.keys(me.published||{}).length)r=['교육이 반영되었습니다. 실제 고객처럼 질문해 상담을 테스트해 보세요.','상담 테스트','test'];
  if(route==='preview'&&me.enabled)r=['상담원이 공개되었습니다. 홈페이지 위젯이나 외부 채널을 연결할 수 있습니다.','채널 연결 보기','route:channels'];
  if(route==='settings'&&!me.settings?.desired_work?.length)r=['여러 업종과 필요한 업무를 선택해 주세요. 선택만으로 결제되지는 않습니다.','업종·업무 설정','settings'];
  if(route==='inbox'&&me.settings?.consultation_mode==='staff')r=['직접 상담한 기록을 검토한 뒤 교육 자료로 활용할 수 있습니다. 교육 분석에는 크레딧이 필요합니다.','교육 방식 보기','education'];
  if(route==='calendar'&&has('calendar')&&!has('auto_booking'))r=['일정표를 사용 중이시네요. AI가 예약 접수까지 맡도록 구성할 수도 있습니다.','자동 예약 알아보기','auto_booking'];
  if(route==='calendar'&&has('auto_booking')&&!has('booking_alert'))r=['자동 예약을 사용 중이시네요. 예약 안내 알림도 설정할 수 있습니다.','예약 알림 알아보기','booking_alert'];
  if(all()[r[2]]&&featureSet(current()).has(r[2]))return [r[0],'구독 구성표 열기','receipt'];
  return r;
 }
 const button=(label,action,value='')=>'<button type="button" data-setup-action="'+escape(action)+'" data-setup-value="'+escape(value)+'">'+escape(label)+'</button>';
 const line=(name,price,other='')=>'<div class="setup-line"><span>'+escape(name)+'</span><b>'+escape(price)+'</b>'+other+'</div>';
 function receipt(){
  const el=document.getElementById('setup-receipt');if(!el)return;
  let result;try{result=current();}catch(err){el.innerHTML='<p>'+escape(err.message)+'</p>';return;}
  const p=plan(),by=all(),brandExtra=result.keys.includes('extra_agent')?(selectedBrandCount-1)*by.extra_agent.price:0,amount=p.price+result.amount+brandExtra,old=cfg.catalog.plans.find(x=>x.id===me.plan),oldAmount=(old?.price||0)+(me.plan==='free'?0:normalize(cfg.catalog,me.addons||[]).amount+Math.max(0,(me.brand_quantity||0)-1)*by.extra_agent.price),delta=amount-oldAmount;
  const key=JSON.stringify([p.id,result.keys,selectedBrandCount]),matched=verified?.key===key;
  const recommendation=cheaper(cfg.catalog,result.keys);
  let content='<div class="setup-receipt-head"><strong>나의 구독 구성</strong><span>예상 월 <b>'+won(matched?verified.amount:amount)+'</b></span>'+button(state.receipt?'접기':'구성표 보기','receipt')+'</div>';
  if(state.receipt){
   content+='<div class="setup-receipt-body"><p class="muted">선택한 상품만 반영됩니다. 아직 결제되지 않았습니다.</p><label>기본 상담 요금제<select data-setup-plan>'+cfg.catalog.plans.map(x=>'<option value="'+escape(x.id)+'" '+(p.id===x.id?'selected':'')+'>'+escape(x.name+' · '+x.quantity.toLocaleString()+'회 · '+won(x.price))+'</option>').join('')+'</select></label>'+line(p.name+' 기본 상담',won(p.price));
   content+=result.keys.length?result.keys.map(k=>line(by[k].name+(k==='extra_agent'?' × '+selectedBrandCount:''),won(by[k].price*(k==='extra_agent'?selectedBrandCount:1)),button('제외','remove',k))).join(''):'<p class="muted">추가한 기능이 없습니다.</p>';
   if(result.discount)content+=line('채널 묶음 할인','-'+won(result.discount));
   content+='<div class="setup-total">'+line('추가 기능 합계',won(result.amount+brandExtra))+line('예상 월 구독료',won(matched?verified.amount:amount))+'</div>';
   if(me.plan!=='free')content+=line('현재 구성의 카탈로그 기준 요금',won(oldAmount))+line('예상 차액',(delta>0?'+':delta<0?'-':'')+won(Math.abs(delta)))+'<small>실제 기존 청구액·일할 계산과 다를 수 있습니다.</small>';
   content+='<small>교육 크레딧, 이전 이용권, 문자 충전 별도 · '+(!p.price?'무료 요금제 · 추가 기능은 유료 요금제 필요':matched?'서버 견적 확인 완료':failedKey===key?'서버 견적 확인 실패. 다시 시도해 주세요.':'서버 견적 확인 중 또는 미확인')+'</small>';
   if(recommendation)content+='<div class="setup-suggestion"><b>패키지 적용 시 월 '+won(recommendation.saving)+' 절약 가능</b><small>선택한 기능을 모두 유지하는 구성입니다. 준비 중 기능의 실제 제공 여부는 별도 확인하세요.</small>'+button('절약 구성 확인·적용','optimize')+'</div>';
   content+='<div class="setup-actions">'+button('요금제 및 결제 확인','navigate','pricing')+(failedKey===key?button('견적 다시 확인','retry'):'')+'</div></div>';
  }
  el.innerHTML=content;
 }
 function quote(){
  const p=plan(),r=current();if(!p.price)return;
  const key=JSON.stringify([p.id,r.keys,selectedBrandCount]);if(verified?.key===key||pendingKey===key||failedKey===key)return;
  const request=++serial;pendingKey=key;
  api('/api/billing/quote',{kind:'subscription',plan:p.id,addons:r.keys,brand_quantity:r.keys.includes('extra_agent')?selectedBrandCount:0}).then(q=>{if(request!==serial||JSON.stringify([plan().id,current().keys,selectedBrandCount])!==key)return;verified={key,amount:q.amount};}).catch(()=>{if(request===serial&&JSON.stringify([plan().id,current().keys,selectedBrandCount])===key)failedKey=key;}).finally(()=>{if(request!==serial)return;pendingKey='';receipt();if(state?.receipt)quote();});
 }
 function guide(){
  const el=document.getElementById('setup-guide');if(!el)return;
  const r=prompt(),key=route+':'+r[2],active=!state.dismissed.has(key);
  let html='<div class="setup-guide-head"><strong>설정 도우미</strong>'+button(state.guide?'접기':'도움 받기','guide')+'</div>';
  if(state.guide){
   if(active&&!state.seen.has(key)){state.seen.add(key);state.messages.push({role:'guide',text:r[0]});}
   html+='<div class="setup-dialogue" role="log" aria-label="설정 안내 대화">'+state.messages.slice(-20).map(m=>'<div class="setup-message '+(m.role==='user'?'setup-user':'')+'">'+escape(m.text)+'</div>').join('')+'</div>';
   html+='<div class="setup-replies">'+(active?button(r[1],'reply',r[2])+button('나중에 할게요','dismiss',key):button('현재 페이지 안내 다시 보기','reopen',key))+button('전체 요금제 보기','navigate','pricing')+'</div><small>상황별 자동 안내 · AI 크레딧 차감 없음</small>';
  }
  el.innerHTML=html;const log=el.querySelector('.setup-dialogue');if(log)log.scrollTop=log.scrollHeight;
 }
 function redraw(){receipt();guide();save();if(state.receipt)quote();}
 function changed(){failedKey='';if(plan().id==='free'&&selectedAdd.size)selectedPlan='lite';redraw();if(route==='pricing')render();}
 function add(k){
  initialize();if(!all()[k])return;
  const old=current(),wanted=featureSet(old);
  if(k==='channels'){wanted.add('naver');wanted.add('kakao');}else wanted.add(k);
  // Preserve every selected feature, including features in an existing package.
  if(!featureSet(old).has(k)&&!(k==='channels'&&old.features.has('naver')&&old.features.has('kakao'))){
   let candidate=[...old.keys,k];try{const next=normalize(cfg.catalog,candidate);if([...wanted].some(id=>!featureSet(next).has(id)))throw Error('coverage');selectedAdd=new Set(next.keys);}catch{selectedAdd=new Set(normalize(cfg.catalog,[...wanted]).keys);}
  }
  state.receipt=true;toast('구독 구성에 추가했습니다. 아직 결제되지 않았습니다.');changed();
 }
 function preview(k){
  const a=all()[k];if(!a)return;
  const demo={calendar:'11월 30일 14:00 · 샘플 예약 · 승인 대기',auto_booking:'고객: 오후 2시 가능한가요? → 예약 가능 시간 안내 → 담당자 승인 또는 자동 확정',crm:'샘플 고객 · 문의 접수 → 담당자 지정 → 처리 완료',widget:'홈페이지 방문자 → 상담창 열기 → 질문 입력',extra_agent:'기본 브랜드 상담원 / 다른 브랜드 전용 상담원',design:'상담창 테마 · 색상 · 메시지 간격 설정'}[k]||'이 기능의 적용 범위와 이용 조건을 확인한 뒤 구독 구성에 추가할 수 있습니다.';
  modal(a.name+' 미리보기','<p>'+escape(descriptions[k]||a.name+' 기능입니다.')+'</p><div class="setup-demo"><b>가상 이용 예시</b><p>'+escape(demo)+'</p></div><p>월 '+won(a.price)+' · '+(a.local?'서비스 활성화는 구매 후 가능':'외부 연동 검증 준비 중')+'</p><p class="muted">실제 고객 데이터, 외부 서비스, AI 호출 또는 발송은 사용하지 않습니다.</p><div class="row"><button type="button" class="primary" onclick="CSAISetup.add(\''+k+'\');this.closest(\'.modal\').remove()">구독 구성에 추가</button><button type="button" onclick="this.closest(\'.modal\').remove();go(\''+(routes[k]||'pricing')+'\')">관련 페이지 보기</button></div>');
 }
 function event(ev){
  const b=ev.target.closest('[data-setup-action]');if(!b)return;
  const action=b.dataset.setupAction,v=b.dataset.setupValue;
  if(action==='receipt')state.receipt=!state.receipt;
  else if(action==='guide')state.guide=!state.guide;
  else if(action==='navigate'){if(v==='receipt')state.receipt=true;else go(v);}
  else if(action==='reply'){const r=prompt();state.messages.push({role:'user',text:r[1]});if(all()[v]){state.messages.push({role:'guide',text:(descriptions[v]||all()[v].name+' 기능을 확인할 수 있습니다.')+' 월 '+won(all()[v].price)+'입니다. 원하시면 구독 구성에 추가하세요.'});preview(v);}else if(v==='receipt'){state.receipt=true;state.messages.push({role:'guide',text:'선택 내역과 월 요금을 구성표에서 확인하세요.'});}else go(v.startsWith('route:')?v.slice(6):v);}
  else if(action==='dismiss'){state.dismissed.add(v);state.messages.push({role:'user',text:'나중에 할게요'},{role:'guide',text:'필요해지면 언제든 다시 확인할 수 있습니다.'});}
  else if(action==='reopen'){state.dismissed.delete(v);state.seen.delete(v);}
  else if(action==='remove'){
   let old=current(),ids=old.keys.filter(k=>k!==v),next=normalize(cfg.catalog,ids);
   if(next.keys.includes(v)){toast('다른 선택 기능에 필요한 항목입니다. 관련 기능을 먼저 제외해 주세요.');return;}
   selectedAdd=new Set(next.keys);changed();return;
  }else if(action==='optimize'){const rec=cheaper(cfg.catalog,current().keys);if(rec&&confirm('선택한 기능을 유지하면서 월 '+won(rec.saving)+' 절약되는 패키지 구성으로 변경할까요?')){selectedAdd=new Set(rec.keys);changed();return;}}
  else if(action==='retry'){failedKey='';verified=null;}
  redraw();
 }
 function mount(){
  if(publicMode||!me||!me.policy?.accepted)return;
  const main=document.querySelector('.layout main');if(!main)return;
  initialize();
  let el=document.getElementById('setup-receipt');if(!el){el=document.createElement('section');el.id='setup-receipt';el.setAttribute('aria-label','구독 구성표');main.prepend(el);el.addEventListener('click',event);el.addEventListener('change',ev=>{if(ev.target.matches('[data-setup-plan]')){selectedPlan=ev.target.value;changed();}});}
  el=document.getElementById('setup-guide');if(!el){el=document.createElement('aside');el.id='setup-guide';el.setAttribute('aria-label','설정 도우미');main.append(el);el.addEventListener('click',event);}
  redraw();
 }
 function afterPurchase(){if(!state||state.slug!==me.slug)return;selectedPlan=me.plan==='free'?'lite':me.plan;selectedAdd=new Set(me.addons||[]);selectedBrandCount=me.brand_quantity||1;verified=null;failedKey='';pendingKey='';serial++;save();}
 return {normalize,cheaper,mount,add,preview,afterPurchase,initialize};
})();

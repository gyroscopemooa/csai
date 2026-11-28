'use strict';
const $=s=>document.querySelector(s), e=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])), money=x=>Number(x).toLocaleString('ko-KR')+'원', enc=encodeURIComponent;
let cfg,me,route='education',chatSession=null,chatMessages=[],threadId=null,files=[],estimate=null,fields=null,selectedDate=null,calendarMonth=new Date(),selectedPlan='lite',selectedAdd=new Set(),allPlan='basic',allEducation='',pub=null,renderId=0,publicMode=location.pathname.startsWith('/c/')||location.pathname.startsWith('/widget/'),slug=location.pathname.split('/')[2];
const btn=(text,fn,cls='')=>`<button type="button" class="ui-button ${cls||'secondary'}" onclick="${fn}">${e(text)}</button>`, card=(title,body)=>`<section class="card app-card"><h2>${e(title)}</h2>${body}</section>`, input=(id,v='',type='text',ph='')=>`<input id="${id}" type="${type}" value="${e(v)}" placeholder="${e(ph)}">`, ta=(id,v='')=>`<textarea id="${id}">${e(v)}</textarea>`, select=(id,opts,v)=>`<select id="${id}">${opts.map(([k,n])=>`<option value="${e(k)}" ${k===v?'selected':''}>${e(n)}</option>`).join('')}</select>`, pageTop=(h,s)=>`<div class="top page-heading"><div><h1>${e(h)}</h1><p class="muted">${e(s)}</p></div></div>`, has=k=>me?.entitlements.includes(k), go=p=>location.hash=p, val=id=>$('#'+id).value, checked=id=>$('#'+id).checked;
function stack(content,{gap='default'}={}){
 return `<div class="ui-stack${gap==='default'?'':` ui-stack-${gap}`}">${content}</div>`;
}
function divider(){return '<hr class="ui-divider">';}
function inline(content){return `<div class="ui-inline">${content}</div>`;}
function splitContent(main,side,{balanced=false}={}){
 if(!side)return main;
 return `<div class="ui-split${balanced?' ui-split-balanced':''}"><div class="ui-split-grid">
  <div>${main}</div><div class="ui-split-side">${side}</div>
 </div></div>`;
}
function section(id,title,content,description=''){
 return `<section class="ui-section" aria-labelledby="${id}"><h3 id="${id}">${e(title)}</h3>${description?helperText(description):''}${content}</section>`;
}
function helperText(text,id=''){return `<p class="ui-helper"${id?` id="${id}"`:''}>${e(text)}</p>`;}
function actionGroup(...buttons){
 const keepSize=buttons[0]?.keepSize===true;
 if(keepSize)buttons.shift();
 return buttons.some(Boolean)?`<div class="ui-actions ui-inline${keepSize?' ui-actions-keep-size':''}">${buttons.join('')}</div>`:'';
}
function quickActions(label,items){
 return `<div class="ui-quick-actions"><ul aria-label="${e(label)}">
  ${items.map(([name,icon,action])=>`<li><button type="button" class="ui-quick-action" onclick="${e(action)}">${uiIcon(icon)}<span>${e(name)}</span></button></li>`).join('')}
 </ul></div>`;
}
function actionArea(...buttons){return actionFooter(buttons);}
function settingRow(id,title,description,control){
 return `<div class="ui-setting-row"><div class="ui-setting-copy">
  <label id="${id}-label" for="${id}">${e(title)}</label>
  <p id="${id}-hint">${e(description)}</p>
 </div><div class="ui-setting-control">${control}</div></div>`;
}
function actionFooter(actions,{note='',divided=true}={}){
 if(!note&&!actions.some(Boolean))return '';
 return `<div class="ui-action-footer${divided?' is-divided':''}">${note?`<p>${e(note)}</p>`:''}${actionGroup(...actions)}</div>`;
}
function fileUpload(id,{accept,thumbnail,description='',onChange='',title='',buttonText='파일 선택',multiple=false,required=false,zoneId=''}){
 const hint=description?helperText(description,id+'-hint'):'';
 const button=`<button type="button" class="ui-button secondary ui-sm" aria-describedby="${description?id+'-hint ':''}${id}-status" onclick="this.closest('[data-file-upload]').querySelector('input[type=file]').click()">${e(buttonText)}</button>`;
 const drag='ondragenter="fileUploadDrag(event)" ondragover="fileUploadDrag(event)" ondragleave="fileUploadLeave(event)" ondrop="fileUploadDrop(event)"';
 const upload=`<input type="file" id="${id}" accept="${e(accept)}" tabindex="-1" class="visually-hidden"${multiple?' multiple':''}${required?' required oninvalid="fileUploadInvalid(event)"':''} onchange="fileUploadSelected(this);${e(onChange)}">`;
 const status=`<p id="${id}-status" class="ui-file-status" role="status"></p>`;
 if(title)return `<div class="ui-file-upload-drop" data-file-upload ${drag}${zoneId?` id="${zoneId}"`:''}>
   ${upload}${uiIcon('upload')}<strong${zoneId?` id="${zoneId}-title"`:''}>${e(title)}</strong>
   <p class="ui-helper"${zoneId?` id="${zoneId}-subtitle"`:''}>파일을 선택하거나 이곳으로 끌어오세요.</p>
   ${button}${hint}${status}${zoneId?'<div class="ui-file-progress" aria-hidden="true"><span></span></div>':''}
  </div>`;
 return `<div class="ui-file-upload${thumbnail?' has-thumbnail':''}" data-file-upload ${drag}>
  ${thumbnail?`<div class="ui-file-thumbnail" aria-hidden="true">${thumbnail}</div>`:''}
  <div class="ui-file-details">
   ${upload}${button}${hint}${status}
  </div>
 </div>`;
}
function fileUploadSelected(input){
 const status=document.getElementById(input.id+'-status');
 if(!status)return;
 status.dataset.error='false';
 status.textContent=input.files.length===1?input.files[0].name:input.files.length?`${input.files.length}개 파일 선택됨`:'';
}
function fileUploadError(upload,message){
 const status=upload.querySelector('.ui-file-status');
 status.dataset.error='true';
 status.textContent=message;
}
function fileUploadInvalid(event){
 event.preventDefault();
 const upload=event.target.closest('[data-file-upload]');
 fileUploadError(upload,'파일을 선택하세요.');
 setTimeout(()=>upload.querySelector('button')?.focus(),0);
}
function fileUploadDrag(event){
 if(!Array.from(event.dataTransfer.types).includes('Files'))return;
 event.preventDefault();
 event.currentTarget.classList.add('is-dragging');
}
function fileUploadLeave(event){
 if(!event.currentTarget.contains(event.relatedTarget))event.currentTarget.classList.remove('is-dragging');
}
function fileUploadDrop(event){
 event.preventDefault();
 const upload=event.currentTarget, field=upload.querySelector('input[type=file]'), files=event.dataTransfer.files;
 upload.classList.remove('is-dragging');
 if(!files.length||upload.classList.contains('uploading')||upload.querySelector('button').disabled)return;
 if(!field.multiple&&files.length!==1){fileUploadError(upload,'한 번에 파일 하나를 선택하세요.');return;}
 field.files=files;
 field.dispatchEvent(new Event('change',{bubbles:true}));
}
function colorField(id,title,value){
 const hex=/^#[0-9a-f]{6}$/i.test(value)?value.toUpperCase():'#3182F6';
 return `<div class="ui-field"><label class="label" for="${id}">${e(title)}</label>
  <div class="ui-color-field"><div class="appearance-color-swatch" style="--swatch:${hex}">
   <input type="color" id="${id}" value="${hex}" oninput="updateColorField(this)">
  </div><output for="${id}">${hex}</output></div></div>`;
}
function updateColorField(input){
 const hex=input.value.toUpperCase();
 input.parentElement.style.setProperty('--swatch',hex);
 input.closest('.ui-color-field').querySelector('output').value=hex;
}
function dateRangePicker(prefix,{start='',end='',named=false}={}){
 return `<div class="ui-date-range" role="group" aria-label="기간">
  ${label('시작일',input(prefix+'-start',start,'date').replace('<input',named?'<input name="start"':'<input'))}
  ${label('종료일',input(prefix+'-end',end,'date').replace('<input',named?'<input name="end"':'<input'))}
 </div>`;
}
function emptyState(message,{title='',icon=''}={}){
 return `<div class="ui-empty">${icon?uiIcon(icon):''}${title?`<strong>${e(title)}</strong>`:''}${helperText(message)}</div>`;
}
function statusBadge(text,tone='neutral'){return `<span class="ui-badge" data-tone="${e(tone)}">${e(text)}</span>`;}
function accordion(title,content,{className='',open=false}={}){
 return `<details class="ui-accordion ${className}" ${open?'open':''}><summary><span>${e(title)}</span>${uiIcon('chevron-down')}</summary><div class="ui-accordion-content">${content}</div></details>`;
}
function tooltip(id,description,control){
 return `<span class="ui-tooltip">${control}<span id="${e(id)}" role="tooltip">${e(description)}</span></span>`;
}
function morphTooltipGroup(className,label,controls){
 return `<div class="${e(className)} ui-morph-group" role="group" aria-label="${e(label)}"
  onpointerover="if(event.pointerType!=='touch')showMorphTooltip(event)"
  onfocusin="showMorphTooltip(event)" onclick="showMorphTooltip(event)"
  onpointerleave="if(!this.matches(':has(:focus-visible)'))hideMorphTooltip(this)"
  onfocusout="if(!this.contains(event.relatedTarget))hideMorphTooltip(this)"
  onkeydown="if(event.key==='Escape')hideMorphTooltip(this)">
  ${controls}<span class="ui-morph-tooltip" aria-hidden="true"><span><span></span></span></span>
 </div>`;
}
function showMorphTooltip(event){
 const group=event.currentTarget,control=event.target.closest('button[data-morph-label]');
 if(!control||!group.contains(control))return;
 const tip=group.querySelector('.ui-morph-tooltip'),label=tip.firstElementChild.firstElementChild;
 if(tip.dataset.open&&label.textContent===control.dataset.morphLabel)return;
 label.textContent=control.dataset.morphLabel;
 const box=group.getBoundingClientRect(),anchor=control.getBoundingClientRect();
 const card=group.closest('.app-card')?.getBoundingClientRect();
 const viewportWidth=document.documentElement.clientWidth;
 const min=Math.max(0,card?.left??0)+8,max=Math.min(viewportWidth,card?.right??viewportWidth)-8;
 const width=Math.min(Math.ceil(label.getBoundingClientRect().width)+16,max-min);
 const center=anchor.left+anchor.width/2;
 const left=Math.min(Math.max(center-width/2,min),max-width);
 tip.dataset.morph=String(Boolean(tip.dataset.open));
 tip.style.setProperty('--tip-x',`${left-box.left}px`);
 tip.style.setProperty('--tip-width',`${width}px`);
 tip.style.setProperty('--tip-arrow',`${Math.min(Math.max(center-left,9),width-9)}px`);
 tip.dataset.open='true';
}
function hideMorphTooltip(group){
 const tip=group.querySelector('.ui-morph-tooltip');
 delete tip.dataset.open;
 delete tip.dataset.morph;
}
document.addEventListener('pointerdown',event=>{
 for(const tip of document.querySelectorAll('.ui-morph-tooltip[data-open]')){
  const group=tip.closest('.ui-morph-group');
  if(!group.contains(event.target))hideMorphTooltip(group);
 }
});
function checkbox(id,text,{checked=false,form='',className='',hint=''}={}){
 return `<label class="ui-check ${e(className)}"><input class="ui-choice" id="${e(id)}" type="checkbox"${checked?' checked':''}${form?` form="${e(form)}"`:''}><span>${e(text)}${hint?`<small>${e(hint)}</small>`:''}</span></label>`;
}
function label(text,body,{labelId='',hint=''}={}){
 const field=/^<(?:input|select|textarea)\b[^>]*\bid="([^"]+)"/.exec(body);
 const id=field?.[1];
 const hintId=hint&&id?'hint-'+id:'';
 const control=hintId?body.replace(/^<\w+/,match=>match+` aria-describedby="${e(hintId)}"`):body;
 const meta=hint||(/^<textarea\b/.test(body)&&/\bmaxlength=/.test(body));
 return `<div class="ui-field"><label class="label"${id?` for="${e(id)}"`:''}${labelId?` id="${e(labelId)}"`:''}>${e(text)}</label>${control}
  ${meta?`<div class="ui-field-meta">${hint?`<span class="ui-hint"${hintId?` id="${e(hintId)}"`:''}>${e(hint)}</span>`:''}</div>`:''}</div>`;
}
const names={agents:'AI 상담원 관리',inbox:'통합 상담함','consultation-center':'상담센터',preview:'채팅창 미리보기',education:'AI 교육시키기',calendar:'일정표 보기',customers:'고객·업무 관리',channels:'외부 채널 연동',alerts:'알림',settings:'설정',pricing:'요금제 및 결제',allinone:'올인원 패키지'}, states={open:'진행 중',pending:'승인 대기',pending_payment:'결제 확인 대기',confirmed:'확정',cancelled:'취소',completed:'완료',resolved:'처리 완료',draft:'작성 중'};
async function api(path,body,method){let r=await fetch(path,{method:method||(body===undefined?'GET':'POST'),headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});if(r.status===204)return {};let x=await r.json().catch(()=>({detail:'서버 응답 오류'}));if(!r.ok){let err=new Error(typeof x.detail==='string'?x.detail:JSON.stringify(x.detail));err.status=r.status;throw err}return x}
function toast(text){document.querySelector('.toast')?.remove();let d=document.createElement('div');d.className='toast';d.setAttribute('role','status');d.textContent=text;document.body.append(d);setTimeout(()=>d.remove(),3500)}
const modalDismissals=new WeakMap();
function modal(title,html,{closeLabel='닫기',dismissOnBackdrop=true,canClose,onClose,className=''}={}){
 const previous=$('.modal'),dismissPrevious=modalDismissals.get(previous);
 if(dismissPrevious){if(!dismissPrevious(false))return null;}
 else previous?.remove();
 if(!me&&!publicMode&&!loginRoute()){
  document.body.insertAdjacentHTML('beforeend',`<div class="modal" onclick="if(event.target===this)this.remove()"><div class="card"><h2>${e(title)}</h2>${html}<div style="margin-top:12px"><button onclick="this.closest('.modal').remove()">닫기</button></div></div></div>`);
  return;
 }
 const opener=document.activeElement;
 document.body.insertAdjacentHTML('beforeend',`<div class="modal ui-modal ${e(className)}"><div class="card app-card ui-modal-panel" role="dialog" aria-modal="true" aria-labelledby="ui-modal-title"><h2 id="ui-modal-title">${e(title)}</h2>${html}<div class="ui-modal-footer"><button type="button" class="ui-button secondary" data-modal-dismiss>${e(closeLabel)}</button></div></div></div>`);
 const overlay=$('.ui-modal'),panel=overlay.querySelector('.ui-modal-panel');
 const dismiss=(restoreFocus=true)=>{
  if(canClose&&!canClose())return false;
  overlay.remove();onClose?.();
  if(restoreFocus)opener?.focus({preventScroll:true});
  return true;
 };
 modalDismissals.set(overlay,dismiss);
 panel.tabIndex=-1;
 panel.focus();
 overlay.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&!event.isComposing){
   event.preventDefault();
   dismiss();
   return;
  }
  if(event.key!=='Tab')return;
  const tabbable=[...panel.querySelectorAll('button, input, select, textarea, a[href], summary, [tabindex]')].filter(item=>!item.disabled&&item.tabIndex>=0&&item.getClientRects().length);
  const first=tabbable[0],last=tabbable.at(-1);
  if(!first){event.preventDefault();return;}
  if(document.activeElement===panel&&event.shiftKey){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  else if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
 });
 overlay.addEventListener('click',event=>{
  if(event.target.closest('[data-modal-dismiss]')||(dismissOnBackdrop&&event.target===overlay))dismiss();
 });
 return overlay;
}
async function act(fn){try{await fn()}catch(x){toast(x.message)}}
const seededLocalWorkspaces=new Set();
async function refresh(){me=await api('/api/me');if(me.sample_tools&&!seededLocalWorkspaces.has(me.slug)){try{if(sessionStorage.getItem('csai-hide-samples:'+me.slug)!=='1')await api('/api/demo/samples',{});seededLocalWorkspaces.add(me.slug)}catch(x){console.warn('Local sample setup:',x.message)}}}
async function switchDemoView(mode){if(educationBusy){toast('진행 중인 교육 작업을 마친 뒤 전환해 주세요.');return;}if(!['free','subscriber','subscriber_agent','developer'].includes(mode))return;await act(async()=>{await api('/api/demo/view',{mode});chatSession=null;chatMessages=[];threadId=null;previewAgent='';brandEditor='';inboxAgent='all';qualityAgent='';calendarAgent='';crmAgent='';calendarProfile=null;calendarRange=null;calendarRangeAnchor='';calendarRangeMode=false;selectedDate=null;estimate=null;educationAgent='';trainingChat=[];resetEducationDraft();$('#education-workspace')?.remove();await refresh();await render();toast('로컬 화면을 전환했습니다. 실제 결제는 없습니다.')})}
function freeFeaturePreview(){return !!me&&!me.operator&&!me.trial;}
function previewNotice(key,description,{detailsOnly=false}={}){
 const action=key?`CSAISetup.add('${key}')`:"go('pricing')";
 const addon=key?cfg.catalog.addons.find(a=>a.id===key):null;
 return `<section class="card app-card paid-preview-notice" aria-label="미리보기 안내" data-paid-feature="${e(key||'')}"><div class="paid-preview-copy"><strong>${e(addon?.name||description)}</strong>${addon?`<span class="paid-preview-price">월 ${money(addon.price)}</span>`:''}</div>${actionGroup({keepSize:true},key?(detailsOnly?btn('상세 안내',`CSAISetup.preview('${key}')`):btn('설정 체험',`featureDraft('${key}')`)):'',btn(key?'구독 구성에 추가':'요금제 보기',action,'primary'))}</section>`;
}
function requirePreviewAccess(key){
 if(key?has(key):me.public_access)return true;
 if(key)CSAISetup.preview(key);else go('pricing');
 return false;
}
let fieldsPreviewMode=null;
function locked(key,description){let a=cfg.catalog.addons.find(x=>x.id===key);return previewNotice(key,description)+card(a?.name||'추가 기능',`<p>${e(description)}</p>${btn('기능 미리보기',`CSAISetup.preview('${key}')`)}`)}
const uiIcon=name=>`<span class="ui-icon" style="--icon:url('/assets/icons/${e(name)}.svg')" aria-hidden="true"></span>`;
const copyButtonTimers=new WeakMap();
function copyButton(label,source='',className='secondary'){
 return `<button type="button" class="ui-button ui-copy-button ${e(className)}" aria-label="${e(label)}" data-copy-label="${e(label)}" data-copy-source="${e(source)}" onclick="copyToClipboard(this)">
  <span class="ui-copy-icon" aria-hidden="true">${uiIcon('copy')}<svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6"/></svg></span>
  <span class="ui-copy-clip" aria-hidden="true"><span class="ui-copy-words"><span>${e(label)}</span><span>복사 완료</span></span></span>
 </button>`;
}
function showCopyState(button,copied){
 const clip=button.querySelector('.ui-copy-clip'), labels=button.querySelector('.ui-copy-words').children;
 clip.style.inlineSize=clip.getBoundingClientRect().width+'px';
 const width=labels[copied?1:0].getBoundingClientRect().width;
 button.toggleAttribute('data-copied',copied);
 button.setAttribute('aria-label',copied?'복사 완료':button.dataset.copyLabel);
 clip.style.inlineSize=width+'px';
}
async function copyToClipboard(button){
 try{
  const source=button.dataset.copySource?document.getElementById(button.dataset.copySource):button.closest('.bubble')?.querySelector('[data-chat-copy-text]');
  const text=source?.value??source?.textContent;
  if(!text?.trim())throw Error('복사할 내용이 없습니다.');
  if(!navigator.clipboard?.writeText)throw Error('이 브라우저에서 클립보드를 사용할 수 없습니다.');
  await navigator.clipboard.writeText(text);
  if(!button.isConnected)return;
  clearTimeout(copyButtonTimers.get(button));
  showCopyState(button,true);
  copyButtonTimers.set(button,setTimeout(()=>showCopyState(button,false),1800));
 }catch(error){
  clearTimeout(copyButtonTimers.get(button));
  showCopyState(button,false);
  toast(error.name==='NotAllowedError'?'클립보드 접근이 차단되었습니다. 브라우저 권한을 확인해 주세요.':error.message);
 }
}
function sidebarGroups(){
 const groups=[
  ['사업 현황',[['dashboard','오늘의 사업 현황','list']]],
  ['상담 관리',[['inbox','통합 상담함','messages-square'],['consultation-center','상담센터','message-circle'],['preview','채팅창 미리보기','message-circle'],['chat-page','고객 채팅 페이지','app-window'],['setup','시작 및 교육 개선','list'],['reply-assistant','답장 비서','message-circle'],['education','AI 교육시키기','graduation-cap'],['agents','AI 상담원 관리','bot'],['stats','상담 통계','chart-no-axes-combined'],['reports','일간·주간 리포트','receipt']]],
  ['업무 관리',[['calendar','일정표 보기','calendar-days'],['customers','고객·업무 관리','users-round'],['commerce','온라인 판매 관리','receipt'],['team','직원 관리','users-round'],['staff-desk','직원 상담함','messages-square']]],
  ['서비스 관리',[['channels','외부 채널 연동','plug'],['developer','개발자 센터','external-link'],['alerts','알림','bell'],['settings','설정','settings'],['pricing','요금제 및 결제','wallet'],['features','전체 기능','list'],['service-plan','서비스 자료실','list'],['credits','교육 크레딧','coins'],['addons','추가 기능','puzzle'],['orders','주문·구독 내역','receipt'],['allinone','올인원 패키지','puzzle']]]
 ];
 if(me.operator)groups.push(['운영자 전용',[['invites','초청 및 체험 관리','ticket'],['costs','AI 사용량 및 원가','chart-no-axes-combined']]]);
 return groups;
}
const sidebarOrderKey=()=> 'csai-sidebar-order:'+me.slug;
function orderedSidebarGroups(){
 let saved=[];
 try{const order=JSON.parse(localStorage.getItem(sidebarOrderKey()));if(Array.isArray(order))saved=order;}catch{}
 const rank=new Map(saved.filter(id=>typeof id==='string').map((id,i)=>[id,i]));
 return sidebarGroups().map(([title,items])=>[title,items.sort(([a],[b])=>(rank.get(a)??Infinity)-(rank.get(b)??Infinity))]);
}
function sidebarNavItems(){
 return orderedSidebarGroups().map(([title,items])=>`<div class="nav-group"><div class="nav-title">${e(title)}</div>${items.map(([p,n,icon])=>`<button type="button" data-menu-route="${p}" class="nav-item ${route===p?'active':''} ${p==='allinone'?'nav-allinone':''}" onclick="go('${p}')" ${route===p?'aria-current="page"':''}>${uiIcon(icon)}<span>${e(n)}</span></button>`).join('')}</div>`).join('');
}
function menuOrderRows(items){
 return items.map(([id,name,icon],i)=>`<li class="menu-order-row">
  <span class="menu-order-item">${uiIcon(icon)}<span>${e(name)}</span></span>
  <div class="menu-order-moves">
   <button type="button" data-menu-move="${id}" data-step="-1" aria-label="${e(name)} 위로" ${i===0?'disabled':''}>${uiIcon('chevron-down')}</button>
   <button type="button" data-menu-move="${id}" data-step="1" aria-label="${e(name)} 아래로" ${i===items.length-1?'disabled':''}>${uiIcon('chevron-down')}</button>
  </div>
 </li>`).join('');
}
function editMenuOrder(){
 const dialog=document.createElement('dialog');
 const categories=sidebarGroups().filter(([,items])=>items.length>1);
 let selected=0;
 dialog.className='menu-order-dialog';
 dialog.setAttribute('aria-labelledby','menu-order-title');
 dialog.innerHTML=`<header class="menu-order-header">
  <h2 id="menu-order-title">메뉴 순서 변경</h2>
  <p>그룹을 선택한 뒤 화살표로 메뉴를 옮기세요.</p>
 </header>
 <div class="menu-order-groups ui-tabs" role="group" aria-label="메뉴 그룹">
  ${categories.map(([title],i)=>`<button type="button" data-menu-group="${i}" aria-pressed="${i===selected}">${e(title)}</button>`).join('')}
 </div>
 <div class="menu-order-body"><ul class="menu-order-list"></ul></div>
 <footer class="menu-order-footer">
  <button type="button" data-menu-reset>기본 순서로 복원</button>
  <span role="status">이 브라우저에 자동 저장</span>
  <form method="dialog"><button type="submit" class="primary">완료</button></form>
 </footer>`;
 const list=dialog.querySelector('.menu-order-list'),status=dialog.querySelector('[role="status"]');
 const groupButtons=[...dialog.querySelectorAll('[data-menu-group]')];
 function showGroup(){
  const title=categories[selected][0];
  const [,items]=orderedSidebarGroups().find(([name])=>name===title);
  list.setAttribute('aria-label',title);
  list.innerHTML=menuOrderRows(items);
  groupButtons.forEach((button,i)=>button.setAttribute('aria-pressed',i===selected));
 }
 const opener=document.activeElement;
 dialog.addEventListener('close',()=>{dialog.remove();opener?.focus();},{once:true});
 dialog.addEventListener('click',ev=>{
  if(ev.target===dialog){dialog.close();return;}
  const group=ev.target.closest('[data-menu-group]');
  if(group){selected=Number(group.dataset.menuGroup);showGroup();return;}
  const button=ev.target.closest('[data-menu-move],[data-menu-reset]');
  if(!button)return;
  const id=button.dataset.menuMove,step=Number(button.dataset.step);
  try{
   if(id){
    const groups=orderedSidebarGroups(),items=groups.find(([title])=>title===categories[selected][0])[1];
    const from=items.findIndex(([key])=>key===id),to=from+step;
    if(from<0||to<0||to>=items.length)return;
    [items[from],items[to]]=[items[to],items[from]];
    localStorage.setItem(sidebarOrderKey(),JSON.stringify(groups.flatMap(([,rows])=>rows.map(([key])=>key))));
   }else localStorage.removeItem(sidebarOrderKey());
  }catch{status.textContent='저장할 수 없습니다';return;}
  $('.sidebar-nav-items').innerHTML=sidebarNavItems();
  showGroup();
  status.textContent=id?'순서 저장됨':'기본 순서로 복원됨';
  if(id){
   const controls=[...list.querySelectorAll('[data-menu-move]')].filter(control=>control.dataset.menuMove===id);
   (controls.find(control=>!control.disabled&&Number(control.dataset.step)===step)||controls.find(control=>!control.disabled))?.focus();
  }
 });
 showGroup();
 document.body.append(dialog);
 dialog.showModal();
 groupButtons[0].focus();
}
const serviceNotices=[
 {id:'development-preview',kind:'update',date:'2026-11-28',title:'무료 계정 기능 미리보기 개선',body:'기존 일정표, 고객·업무 관리, 판매 관리, 추가 브랜드 상담원 화면을 구독 전에도 둘러볼 수 있도록 개선하고 있습니다. 실제 등록, 저장 및 연동에는 해당 권한이 필요합니다.',demoOnly:true},
 {id:'setup-consultation',kind:'update',date:'2026-11-28',title:'초기 구축 대행 상담 유형 안내',body:'기본 구축 대행과 맞춤 컨설팅 및 구축 대행의 작업 범위를 비교하고 전화 상담을 신청할 수 있습니다. 표시 금액은 시작 견적입니다.',demoOnly:true},
 {id:'development-notice',kind:'notice',date:'2026-11-28',title:'개발 환경 이용 안내',body:'현재 개발 환경의 기능, 요금 및 외부 연동은 검증 중입니다. 실제 결제 및 발송과 구분하여 이용해 주세요.',demoOnly:true}
];
const serviceNoticeLabels={urgent:'긴급',notice:'공지',update:'업데이트'};
function visibleServiceNotices(){return serviceNotices.filter(n=>!n.demoOnly||cfg.demo);}
let serviceNoticeFilter='all',serviceNoticeOpen='';
function serviceNoticeStrip(){
 const items=visibleServiceNotices(),item=items.find(n=>n.kind==='urgent')||items[0];
 return `<button type="button" class="service-notice-strip" data-kind="${e(item?.kind||'notice')}" onclick="openServiceNotices()" aria-label="공지사항 및 업데이트 전체 보기"><span class="service-notice-kind">${e(item?serviceNoticeLabels[item.kind]:'공지')}</span><span class="service-notice-title">${e(item?.title||'공지사항 및 업데이트')}</span>${uiIcon('chevron-right')}</button>`;
}
function openServiceNotices(){serviceNoticeFilter='all';serviceNoticeOpen='';if(route==='service-notices')render();else go('service-notices');}
function filterServiceNotices(k){if(!['all','notice','update','urgent'].includes(k))return;serviceNoticeFilter=k;serviceNoticeOpen='';render();}
function serviceNoticePage(){
 const items=visibleServiceNotices().filter(n=>serviceNoticeFilter==='all'||n.kind===serviceNoticeFilter).sort((a,b)=>(b.kind==='urgent')-(a.kind==='urgent')||b.date.localeCompare(a.date));
 return pageTop('공지사항 및 업데이트','서비스 안내와 변경 사항을 확인하세요.')+card('서비스 소식',`<div class="ui-tabs calendar-status-filters" role="group" aria-label="소식 유형">${[['all','전체'],['notice','공지사항'],['update','업데이트'],['urgent','긴급사항']].map(([key,label])=>`<button type="button" aria-pressed="${serviceNoticeFilter===key}" onclick="filterServiceNotices('${key}')">${label}</button>`).join('')}</div><div class="service-notice-list">${items.map(n=>`<details class="service-notice-item" ${serviceNoticeOpen===n.id?'open':''}><summary><span class="service-notice-kind-label">${e(serviceNoticeLabels[n.kind])}</span><strong>${e(n.title)}</strong><time datetime="${e(n.date)}">${e(n.date)}</time></summary><p>${e(n.body)}</p></details>`).join('')||emptyState(serviceNoticeFilter==='urgent'?'등록된 긴급사항이 없습니다.':'등록된 소식이 없습니다.')}</div>`);
}
function quickNavOptions(){
 const short={dashboard:'홈',inbox:'상담함','consultation-center':'상담',preview:'채팅 미리보기','chat-page':'채팅 페이지',stats:'상담 통계',reports:'리포트',setup:'시작 설정','reply-assistant':'답장 비서',education:'AI 교육',agents:'상담원',calendar:'일정',customers:'고객 관리',commerce:'판매 관리',team:'직원 관리','staff-desk':'직원 상담',channels:'채널 연동',developer:'개발자',alerts:'알림',settings:'설정',pricing:'요금제',features:'전체 기능','service-plan':'자료실',credits:'크레딧',addons:'추가 기능',orders:'주문 내역',allinone:'올인원',invites:'초청 관리',costs:'원가 통계'};
 return sidebarGroups().flatMap(([,items])=>items).map(([id,name,icon])=>[id,short[id]||name,icon]);
}
function quickNavKey(){return 'csai-mobile-quick-nav:'+me.slug;}
function quickNavDefaults(){return ['dashboard','consultation-center','education','calendar','alerts'];}
function quickNavSelection(){
 const valid=new Set(quickNavOptions().map(([id])=>id));
 try{const saved=JSON.parse(localStorage.getItem(quickNavKey()));if(Array.isArray(saved)){const ids=[...new Set(saved.filter(id=>valid.has(id)))].slice(0,5);if(ids.length>=3)return ids;}}catch{}
 return quickNavDefaults();
}
function mobileQuickNav(){
 const options=new Map(quickNavOptions().map(item=>[item[0],item]));
 const items=quickNavSelection().map(id=>options.get(id)).filter(Boolean);
 return `<nav class="mobile-quick-nav" aria-label="빠른 메뉴" style="grid-template-columns:repeat(${items.length},minmax(0,1fr))">${items.map(([id,name,icon])=>`<button type="button" class="${route===id?'active':''}" ${route===id?'aria-current="page"':''} onclick="quickNavigate('${id}')">${uiIcon(icon)}<span>${e(name)}</span></button>`).join('')}</nav>`;
}
async function quickNavigate(id){
 if(!quickNavOptions().some(item=>item[0]===id))return;
 if(id===route)return;
 if(['inbox','consultation-center'].includes(route)&&threadId){
  if(inboxReplyDraftActive()&&!confirm('작성 중인 내용을 닫고 이동할까요?'))return;
  await leaveTemporary();threadId=null;
 }
 if(inboxDesk()&&id!=='consultation-center'){location.href='/#'+id;return;}
 go(id);
}
function editQuickNav(){
 let ids=quickNavSelection();
 const options=quickNavOptions(),byId=new Map(options.map(item=>[item[0],item]));
 const dialog=document.createElement('dialog'),opener=document.activeElement;
 dialog.className='menu-order-dialog';
 dialog.setAttribute('aria-labelledby','quick-nav-title');
 dialog.innerHTML=`<header class="menu-order-header"><h2 id="quick-nav-title">퀵바 메뉴 변경</h2><p>모바일 하단 메뉴 3~5개를 선택하고 순서를 변경하세요.</p></header><div class="menu-order-body"><ul class="menu-order-list"></ul><label>메뉴 추가<select data-quick-add aria-label="추가할 메뉴"></select></label><button type="button" data-quick-action="add">추가</button></div><footer class="menu-order-footer"><button type="button" data-quick-action="reset">기본 메뉴로 복원</button><span role="status"></span><button type="button" data-quick-action="save" class="primary">저장</button><button type="button" data-quick-action="cancel">취소</button></footer>`;
 const list=dialog.querySelector('.menu-order-list'), selectEl=dialog.querySelector('[data-quick-add]'),status=dialog.querySelector('[role="status"]');
 function repaint(){
  list.innerHTML=ids.map((id,i)=>{const [,name,icon]=byId.get(id);return `<li class="menu-order-row"><span class="menu-order-item">${uiIcon(icon)}<span>${e(name)}</span></span><div class="menu-order-moves"><button type="button" data-quick-action="up" data-index="${i}" aria-label="${e(name)} 위로" ${i===0?'disabled':''}>↑</button><button type="button" data-quick-action="down" data-index="${i}" aria-label="${e(name)} 아래로" ${i===ids.length-1?'disabled':''}>↓</button><button type="button" data-quick-action="remove" data-index="${i}" aria-label="${e(name)} 제거" ${ids.length<=3?'disabled':''}>−</button></div></li>`;}).join('');
  selectEl.innerHTML='<option value="">메뉴 선택</option>'+options.filter(([id])=>!ids.includes(id)).map(([id,name])=>`<option value="${e(id)}">${e(name)}</option>`).join('');
  selectEl.disabled=ids.length>=5;dialog.querySelector('[data-quick-action="add"]').disabled=ids.length>=5;status.textContent=`${ids.length}/5개 · 이 브라우저에 저장`;
 }
 dialog.addEventListener('close',()=>{dialog.remove();opener?.focus();},{once:true});
 dialog.addEventListener('click',ev=>{
  if(ev.target===dialog){dialog.close();return;}
  const button=ev.target.closest('[data-quick-action]');if(!button||button.disabled)return;
  const action=button.dataset.quickAction,i=Number(button.dataset.index);
  if(action==='cancel'){dialog.close();return;}
  if(action==='save'){try{localStorage.setItem(quickNavKey(),JSON.stringify(ids));}catch{status.textContent='저장할 수 없습니다';return;}const nav=document.querySelector('.mobile-quick-nav');if(nav)nav.outerHTML=mobileQuickNav();dialog.close();return;}
  if(action==='reset')ids=quickNavDefaults();
  if(action==='add'&&ids.length<5&&byId.has(selectEl.value)&&!ids.includes(selectEl.value))ids.push(selectEl.value);
  if(action==='remove'&&ids.length>3&&i>=0&&i<ids.length)ids.splice(i,1);
  if(action==='up'&&i>0&&i<ids.length)[ids[i],ids[i-1]]=[ids[i-1],ids[i]];
  if(action==='down'&&i>=0&&i<ids.length-1)[ids[i],ids[i+1]]=[ids[i+1],ids[i]];
  repaint();
 });
 repaint();document.body.append(dialog);dialog.showModal();
}
function shell(body){
 const wordmark=`<span class="sidebar-wordmark">
  <svg class="sidebar-wordmark-filter" width="0" height="0" aria-hidden="true" focusable="false">
   <filter id="sidebar-wordmark-goo" x="-20%" y="-40%" width="140%" height="180%" color-interpolation-filters="sRGB">
    <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 8 -2"/>
   </filter>
  </svg>
  <span class="sidebar-wordmark-ink"><span class="sidebar-wordmark-base"><b>CS</b> AI</span><span class="sidebar-wordmark-tagline" aria-hidden="true">나의 클론 상담직원</span></span>
 </span>`;
 const quota=cfg.catalog.plans.find(x=>x.id===me.plan)?.quantity||1;
 const progress=me.trial||me.operator?'':`<div class="usage-track" role="progressbar" aria-label="이번 달 상담 사용량" aria-valuenow="${Math.max(0,quota-me.remaining)}" aria-valuemax="${quota}"><span style="width:${Math.max(0,Math.min(100,(quota-me.remaining)/quota*100))}%"></span></div>`;
 const demoSelector=me.demo_view?`<div class="demo-view-select"><label for="demo-view">로컬 화면 비교</label><select id="demo-view" onchange="switchDemoView(this.value)">${me.demo_view==='legacy'?'<option value="legacy" selected>기존 로컬 계정</option>':''}<option value="free" ${me.demo_view==='free'?'selected':''}>일반 무료 가입</option><option value="subscriber" ${me.demo_view==='subscriber'?'selected':''}>LITE 유료 구독 예시</option><option value="subscriber_agent" ${me.demo_view==='subscriber_agent'?'selected':''}>LITE + 추가 브랜드 상담원 예시</option><option value="developer" ${me.demo_view==='developer'?'selected':''}>개발 검수 · 기능 미리보기</option></select><small>무료 가입 화면에서 모든 공통 샘플을 실제 무료 유저와 동일하게 확인할 수 있습니다 · 실제 결제 없음</small></div>`:'';
 return `<div class="layout" data-route="${e(route)}"><aside class="app-sidebar"><div class="brand sidebar-brand">${wordmark}<button type="button" class="mobile-toggle" onclick="this.closest('aside').classList.toggle('open')" aria-label="메뉴 열기">${uiIcon('menu')}</button></div>${serviceNoticeStrip()}<div class="sidebar-tenant"><strong>${e(me.settings.brand)}</strong><small>${me.demo_view==='developer'?'개발 검수 · 판매 요금제 아님':me.demo_view==='subscriber_agent'?'LITE · 추가 브랜드 상담원 이용 중':me.operator?'운영자 계정':me.trial?'초청 체험':e(me.plan.toUpperCase()+' 요금제')}</small></div>${demoSelector}<nav aria-label="관리 메뉴"><button type="button" class="menu-order-button" onclick="editMenuOrder()">${uiIcon('list')}<span>메뉴 순서 변경</span></button><button type="button" class="menu-order-button" onclick="editQuickNav()">${uiIcon('settings')}<span>퀵바 메뉴 변경</span></button><div class="sidebar-nav-items">${sidebarNavItems()}</div></nav><div class="sidebar-bottom"><div class="usage-label"><span>남은 상담</span><b>${me.remaining.toLocaleString()}회</b></div>${progress}<div class="usage-label"><span>교육 크레딧</span><b>${me.credits.toLocaleString()} C</b></div>${me.trial?`<p class="sidebar-trial">예약 체험 ${me.trial.bookings_remaining}건 남음</p>`:''}<button type="button" class="usage-link" onclick="go('pricing')">${uiIcon('wallet')} 이용량 및 요금제</button><button type="button" class="sidebar-logout ui-button tertiary" onclick="logout()">${uiIcon('log-out')} 로그아웃</button></div></aside><main><div class="mobile-service-notice">${serviceNoticeStrip()}</div>${cfg.demo?'<div class="demo-note">개발 환경 · 실제 결제 없음 · '+(cfg.ai_connected?'실제 AI API 연결됨':'AI 응답은 로컬 규칙 기반 데모')+'</div>':''}${body}</main>${mobileQuickNav()}</div>`
}
function home(){return `<div class="hero"><div class="hero-inner"><div class="brand"><b>CS</b> AI <span class="brand-subtitle" aria-label="나의 클론 상담사"><span class="brand-typed" aria-hidden="true">나의 클론 상담사</span></span></div><span class="tag">AI 고객 상담 매니저</span><h1>나처럼 상담하는 AI</h1><p class="muted" style="font-size:15px;line-height:1.8;margin:0 0 30px">직접 교육하고, 링크 하나로 시작하세요.<br>당신의 고객 상담을 대신합니다.</p><div class="stack"><button class="google auth-button" onclick="google()"><img src="/assets/google-g.svg" alt=""><span>Google로 시작하기</span></button>${inboxDesk()?'':'<a class="ui-button secondary" href="/?desk=1#consultation-center">기존 회원 · 상담센터 바로 열기</a>'}<button class="naver auth-button" onclick="modal('준비 중','<p>네이버 로그인은 준비 중입니다.</p>')"><img src="/assets/naver-n.svg" alt=""><span>네이버로 시작하기</span></button><button class="kakao auth-button" onclick="modal('준비 중','<p>카카오 로그인은 준비 중입니다.</p>')"><img src="/assets/kakao-talk.svg" alt=""><span>카카오로 시작하기</span></button></div><p class="muted" style="margin-top:24px">개발 환경 · 운영 약관 및 개인정보처리방침은 출시 전 확정</p></div></div>${landingAudience()}${landingBenefits()}${landingUnification()}${landingOwnerLetter()}`}

function landingAudience(){
 return `<section class="landing-audience" aria-labelledby="landing-audience-title"><div class="landing-audience-inner"><p class="landing-benefits-kicker">BUILT FOR YOU</p><h2 id="landing-audience-title"><span>프리랜서를 위한.</span><span>자영업자를 위한.</span><span>온라인 사업자를 위한.</span></h2><p class="landing-audience-copy">혼자 일해도, 혼자 상담할 필요는 없으니까.</p></div></section>`
}
function landingOwnerLetter(){
 return `<section class="landing-owner-letter" aria-labelledby="landing-owner-title"><div class="landing-owner-letter-inner"><p class="landing-benefits-kicker">TO. 사장님께</p><h2 id="landing-owner-title">사장님도 퇴근할 수 있도록.</h2><div class="landing-owner-copy"><p>고객의 문의에 답하느라 하루를 보내는 사장님께.</p><p>이제 상담은 당신의 클론에게 맡기고,<br>당신의 사업과 일상에 집중하세요.</p></div><button type="button" class="landing-owner-action" onclick="google()">나의 클론 상담사 만들기</button></div></section>`
}
function loginRoute(){return location.pathname==='/'&&new URLSearchParams(location.search).get('view')==='login';}
function google(){if(inboxDesk())sessionStorage.setItem('csai-desk-return','1');location.href='/?view=login';}
function startGoogleLogin(){
 if(cfg.google_configured){location.href='/auth/google';return;}
 modal('Google 로그인 준비 중',helperText('Google 로그인 설정을 확인하고 있습니다.'));
}
async function logout(){await act(async()=>{const id=localStorage.getItem('csai-push-id');if(id){await api('/api/push/'+enc(id),undefined,'DELETE');const reg=await navigator.serviceWorker?.getRegistration('/');const sub=await reg?.pushManager.getSubscription();if(sub)await sub.unsubscribe();localStorage.removeItem('csai-push-id')}await api('/api/logout',{});location.replace('/?view=login')})}
function profileAvailable(s){const p=s.chat_profile||{};return !!(p.title||p.message||p.photo||p.links?.length||p.contacts?.length)}
function profileContacts(p){
 return (p.contacts||[]).filter(c=>c.name&&c.value).map(c=>{
  let href='';
  if(c.kind==='phone'&&/^\+?[0-9 ()-]{3,40}$/.test(c.value))href='tel:'+c.value.replace(/[^0-9+]/g,'');
  if(c.kind==='email'&&/^[A-Za-z0-9._+\-]+@[A-Za-z0-9.-]+\.[A-Za-z0-9-]+$/.test(c.value))
   href='mailto:'+encodeURIComponent(c.value).replace('%40','@');
  const value=href?`<a href="${e(href)}">${e(c.value)}</a>`:e(c.value);
  return `<div class="chat-profile-info-row"><dt>${e(c.name)}</dt><dd>${value}</dd></div>`;
 }).join('');
}
function profileLinks(links=[]){
 const rows=links.map(link=>{
  try{
   const url=new URL(link.url);
   if(!link.name||url.protocol!=='https:'||url.username||url.password)return '';
   return `<li><a href="${e(url.href)}" target="_blank" rel="noopener noreferrer">
    <span>${e(link.name)}</span>${uiIcon('external-link')}
   </a></li>`;
  }catch{return '';}
 }).join('');
 return rows?`<ul class="chat-profile-links">${rows}</ul>`:'';
}
function profileManualNotice(s){
 const mode=s.chat_profile?.notice_mode||'manual';
 if(mode!=='manual'&&mode!=='both')return {notice:'',links:[]};
 return {notice:String(s.notice??s.chat_profile?.manual_notice??'').trim(),links:s.links||[]};
}
function profileMarkup(s,{page=false}={}){
 const p=s.chat_profile||{},photo=String(p.photo||'');
 const title=String(p.title||'').trim(),message=String(p.message||'').trim(),hours=String(s.hours||'').trim();
 const {notice,links:official}=page?profileManualNotice(s):{notice:'',links:[]};
 const links=profileLinks([...(p.links||[]),...official]);
 const information=(hours?`<div class="chat-profile-info-row"><dt>영업시간</dt><dd>${e(hours)}</dd></div>`:'')+profileContacts(p);
 return `<section class="chat-profile-details${page?' chat-profile-page':' chat-profile-inline'}" aria-label="업체 정보"${page?' tabindex="0"':''}>
  <header class="chat-profile-hero">
   ${/^data:image\/(?:png|webp);base64,/.test(photo)?`<img class="chat-profile-photo" src="${e(photo)}" alt="업체 프로필 사진">`:''}
   <h3>${e(s.brand||title)}</h3>
   ${s.brand&&title&&title!==s.brand?`<p class="chat-profile-intro-title">${e(title)}</p>`:''}
   ${message?`<p class="chat-profile-copy">${e(message)}</p>`:''}
  </header>
  ${notice?`<section class="chat-profile-detail-section"><h3>공지사항</h3><p class="chat-profile-copy">${e(notice)}</p></section>`:''}
  ${information?`<section class="chat-profile-detail-section"><h3>업체 정보</h3><dl class="chat-profile-info">${information}</dl></section>`:''}
  ${links?`<section class="chat-profile-detail-section"><h3>관련 링크</h3>${links}</section>`:''}
 </section>`;
}
function chatNoticeMarkup(s){
 const mode=s.chat_profile?.notice_mode||'manual';
 const {notice,links}=profileManualNotice(s),official=profileLinks(links);
 const profile=(mode==='profile'||mode==='both')&&profileAvailable(s);
 if(!notice&&!official&&!profile)return '';
 return `<div class="notice"><details><summary>공지사항 및 공식 안내 ${uiIcon('chevron-down')}</summary>
  <div class="chat-notice-content">${notice?`<p class="chat-manual-notice">${e(notice)}</p>`:''}${official}${profile?profileMarkup(s):''}</div>
 </details></div>`;
}
function welcomeMarkup(s){return '<div class="chat-day">오늘</div>'+(s.chat_profile?.show_at_start&&profileAvailable(s)?profileMarkup(s):'')+'<div class="bubble welcome-bubble">'+e(s.welcome)+'</div>'}
let activeChatProfile=null;
function openChatProfile(){
 if(activeChatProfile&&profileAvailable(activeChatProfile))
  modal('업체 프로필',profileMarkup(activeChatProfile,{page:true}),{className:'chat-profile-modal'});
}

const chatDesignDefaults={theme:'dark',color:'#3182F6',density:'normal',bubble_radius:'rounded'};
const chatDesignChoices={
 theme:[['dark','기본'],['toss','토스형'],['messenger','메신저형'],['premium','프리미엄형']],
 density:[['normal','기본'],['compact','촘촘하게'],['roomy','여유롭게']],
 bubble_radius:[['rounded','둥글게'],['square','각지게']],
};
function chatDesign(settings){
 const design={...chatDesignDefaults};
 for(const [key,options] of Object.entries(chatDesignChoices)){
  if(options.some(([value])=>value===settings[key]))design[key]=settings[key];
 }
 if(/^#[0-9a-f]{6}$/i.test(settings.color))design.color=settings.color.toUpperCase();
 return design;
}
function chatDesignClasses({theme,density,bubble_radius}){
 return [`theme-${theme}`,`density-${density}`,`radius-${bubble_radius}`];
}
function chatBrandName(brand,wave){
 return `<strong class="chat-brand-name${wave!==false?' has-name-wave':''}">${e(brand)}<span class="chat-brand-echo" aria-hidden="true" data-name="${e(brand)}"></span></strong>`;
}
function publicChatClass(){return 'public '+(location.pathname.startsWith('/widget/')?'public-chat-widget':'public-chat-page')}
function phone(s,test=false,preview=false){
 activeChatProfile=s;
 const design=chatDesign(s);
 const avatar=s.logo&&s.logo.startsWith('data:image/png;base64,')?`<img src="${e(s.logo)}" alt="업체 로고">`:'<span>CS</span>';
 const suggestions=['가격 안내','예약 문의','위치 안내','예약 취소'].map(x=>`<button type="button" onclick="quickChat('${x}')">${x}</button>`).join('');
 return `<section class="phone ${chatDesignClasses(design).join(' ')} ${publicMode?'':'is-resizable'}" style="--chat-color:${design.color}" aria-label="${e(s.brand)} 채팅창">
  <header class="phone-head"><div class="avatar">${avatar}</div><div class="phone-identity">${chatBrandName(s.brand,s.brand_name_wave)}<div class="chat-online"><span></span> 24시간 상담 가능${test?' · 관리자 테스트':''}</div></div>${profileAvailable(s)?btn('프로필','openChatProfile()','chat-profile-open'):''} </header>
  ${chatNoticeMarkup(s)}
  <div class="messages" id="messages" role="log" aria-live="polite">${welcomeMarkup(s)}${chatMessages.map(m=>photoBubble(m,'customer')).join('')}</div>
  <div class="chat-bottom"><div class="chat-suggestions" aria-label="추천 질문">${suggestions}</div>
   <div class="mention-wrap"><div id="mention-picker" class="mention-picker" role="listbox" aria-label="상담 주제 선택" hidden></div><form class="compose" onsubmit="event.preventDefault();sendChat()"><div class="compose-controls"><textarea id="msg" rows="1" maxlength="2000" placeholder="메시지 입력 · @ 주제 선택" aria-label="메시지 입력" aria-controls="mention-picker" aria-autocomplete="list" oninput="resizeCompose(this);if(!event.isComposing)updateMentionPicker(this)" oncompositionend="updateMentionPicker(this)" onclick="updateMentionPicker(this)" onblur="closeMentionPicker(this)" onkeydown="if(handleMentionKey(event))return;if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();sendChat()}"></textarea><button class="primary" id="send" type="submit" aria-label="전송">${uiIcon('send-horizontal')}</button></div><div class="compose-meta"></div></form></div>
   ${publicMode?`<details class="customer-chat-tools"><summary>상담 도구</summary><div class="chat-actions ui-actions ui-actions-keep-size">${btn('사장님께 알리기','requestStaffHandoff()')}${btn('AI 답변 오류 신고','reportCustomerAnswer()')}${btn('상담 마치기·평가','rateConsultation()')}${btn('이 기기에서 상담 이어가기','rememberChatDevice()')}${btn('새 상담','newPublicChat()')}${s.calendar?btn('내 예약 확인','customerBookings()'):''}${s.requests?.length?btn('업무 요청','customerRequest()'):''}${s.commerce?btn('상품·주문 문의','commerceCustomerModal()')+btn('인증 주문·배송 조회','customerOrderAccess()'):''}${s.photos?btn('사진 첨부',"photoUploadModal('customer')"):''}${s.files?btn('영상·파일 첨부',"photoUploadModal('customer','file')"):''}${s.web_calls?btn('음성·영상통화','chooseWebCall()'):''}</div></details>`:''}
   <div class="phone-foot">${s.unbrand?'AI 상담':'AI 상담원이 응대하고 있습니다.'}${cfg.demo?' · 로컬 검증용':''}${publicMode?'':'<span class="resize-note"> · 오른쪽 아래 모서리를 끌어 크기 조절</span>'}</div>
  </div></section>`
}
function resizeCompose(field){field.style.height='auto';field.style.height=Math.min(field.scrollHeight,100)+'px'}
const mentionTopics=[['가격','가격 안내를 부탁드립니다.'],['예약','예약 가능한 일정을 알려주세요.'],['위치','방문 위치를 알려주세요.'],['취소','예약 취소 방법을 알려주세요.']];
let mentionIndex=0,mentionMatches=[];
function mentionAtCursor(field){
 if(field.selectionStart!==field.selectionEnd)return null;
 return /(?:^|\s)@([^\s@]{0,12})$/.exec(field.value.slice(0,field.selectionStart));
}
function closeMentionPicker(field){
 const picker=$('#mention-picker');
 if(picker)picker.hidden=true;
 field.removeAttribute('aria-activedescendant');
 mentionIndex=0;
 mentionMatches=[];
}
function setMentionActive(field){
 const picker=$('#mention-picker'),options=[...picker.children];
 options.forEach((option,index)=>{
  option.classList.toggle('active',index===mentionIndex);
  option.setAttribute('aria-selected',String(index===mentionIndex));
 });
 const active=options[mentionIndex];
 field.setAttribute('aria-activedescendant',active.id);
 if(active.offsetTop<picker.scrollTop)picker.scrollTop=active.offsetTop;
 if(active.offsetTop+active.offsetHeight>picker.scrollTop+picker.clientHeight)
  picker.scrollTop=active.offsetTop+active.offsetHeight-picker.clientHeight;
}
function updateMentionPicker(field){
 const picker=$('#mention-picker');
 if(!picker)return;
 const match=mentionAtCursor(field);
 if(!match){closeMentionPicker(field);return;}
 mentionMatches=mentionTopics.filter(([name])=>name.includes(match[1]));
 if(!mentionMatches.length){closeMentionPicker(field);return;}
 mentionIndex=0;
 picker.innerHTML=mentionMatches.map(([name,prompt],index)=>
  `<button type="button" role="option" id="mention-option-${index}" tabindex="-1" class="mention-option"
   onpointerdown="event.preventDefault()" onclick="chooseMention(${index})"><strong>@${e(name)}</strong><span>${e(prompt)}</span></button>`
 ).join('');
 picker.hidden=false;
 setMentionActive(field);
}
function handleMentionKey(event){
 if(event.isComposing)return false;
 const field=event.target;
 if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
  requestAnimationFrame(()=>{if(document.activeElement===field)updateMentionPicker(field);});
 }
 const picker=$('#mention-picker');
 if(!picker||picker.hidden)return false;
 if(event.key==='Escape'){event.preventDefault();closeMentionPicker(field);return true;}
 if(event.key==='ArrowDown'||event.key==='ArrowUp'){
  event.preventDefault();
  mentionIndex=(mentionIndex+(event.key==='ArrowDown'?1:-1)+mentionMatches.length)%mentionMatches.length;
  setMentionActive(field);
  return true;
 }
 if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();chooseMention(mentionIndex);return true;}
 return false;
}
function chooseMention(index){
 const field=$('#msg'),topic=mentionMatches[index];
 if(!field||!topic)return;
 const match=mentionAtCursor(field);
 if(!match)return;
 const start=match.index+(match[0].startsWith('@')?0:1),end=field.selectionStart;
 if(field.value.length-(end-start)+topic[1].length>field.maxLength){toast('메시지 글자 수 한도를 확인해 주세요.');return;}
 field.setRangeText(topic[1],start,end,'end');
 closeMentionPicker(field);
 field.focus();
 field.dispatchEvent(new Event('input',{bubbles:true}));
}
function quickChat(text){let field=$('#msg');if(!field||sending)return;field.value=text;field.focus();sendChat()}
function bubble(role,body,allowCopy=false){let text=String(body??'');let parts=text.split(/(https:\/\/[^\s<>"']+)/g);const content=parts.map((x,i)=>{if(i%2===0)return e(x);try{let u=new URL(x);if(u.protocol==='https:')return `<a href="${e(u.href)}" rel="noopener noreferrer" target="_blank">${e(x)}</a>`}catch{}return e(x)}).join('');
 return `<div class="bubble ${role==='user'?'user':''}"><span data-chat-copy-text>${content}</span>${allowCopy&&text.trim()?copyButton('복사','','tertiary ui-copy-message'):''}</div>`;
}
let previewAgent='',brandEditor='',inboxAgent='all',selectedBrandCount=1;
async function getChatSession(){if(chatSession)return chatSession;let saved=publicMode?sessionStorage.getItem('csai-session-'+slug):null;if(saved){try{chatMessages=await api('/api/session/'+enc(saved)+'/messages');chatSession=saved;return saved}catch{sessionStorage.removeItem('csai-session-'+slug)}}let s=await api('/api/session',publicMode?{slug,source:location.pathname.startsWith('/widget/')?'widget':'link'}:{test:true,agent:previewAgent});chatSession=s.token;if(publicMode)sessionStorage.setItem('csai-session-'+slug,chatSession);return chatSession}
let sending=false;
const motionDots='<span class="motion-dots" aria-hidden="true"><i></i><i></i><i></i></span>';
function pendingChat(){let area=$('#messages');if(!area)return null;let node=document.createElement('div');node.className='chat-pending';node.setAttribute('role','status');node.innerHTML=motionDots+'<span class="chat-thinking-label">생각 중</span>';area.append(node);area.scrollTop=area.scrollHeight;return node;}
async function streamReply(node,body){
  if(!node?.isConnected)return;
  if(matchMedia('(prefers-reduced-motion: reduce)').matches){node.outerHTML=bubble('assistant',body,true);return}
  const area=node.parentElement,words=String(body).match(/\S+\s*/g)||[String(body)];
  const {width:initialWidth,height:initialHeight}=node.getBoundingClientRect();
  node.className='bubble streaming-reply';node.removeAttribute('role');node.innerHTML='<div class="stream-text" aria-hidden="true"></div>';
  const content=node.firstChild,make=(x,k,c)=>({x,v:0,t:x,k,c}),width=make(initialWidth,260,26),height=make(initialHeight,260,26),letters=[];
  node.style.width=initialWidth+'px';node.style.height=initialHeight+'px';
  const finalWidth=Math.min(area.clientWidth*.86,390),interval=Math.min(55,1200/words.length);
  let done=false,last=performance.now();
  function frame(now){if(!node.isConnected||done)return;const dt=Math.min((now-last)/1000,1/30)/4;last=now;
    for(let i=0;i<4;i++)for(const s of [width,height,...letters.map(x=>x.spring)]){const a=-s.k*(s.x-s.t)-s.c*s.v;s.v+=a*dt;s.x+=s.v*dt}
    node.style.width=Math.max(80,width.x)+'px';node.style.height=Math.max(36,height.x)+'px';
    for(const item of letters){const v=Math.max(0,Math.min(1,item.spring.x));item.el.style.opacity=v;item.el.style.transform=`translateY(${(1-item.spring.x)*6}px)`;item.el.style.filter=v<.98?`blur(${(1-v)*4}px)`:'none'}
    area.scrollTop=area.scrollHeight;requestAnimationFrame(frame)}
  requestAnimationFrame(frame);width.t=finalWidth;
  for(const word of words){if(!node.isConnected)break;const el=document.createElement('span');el.className='stream-word';el.textContent=word;content.append(el);letters.push({el,spring:make(0,340,26)});letters.at(-1).spring.t=1;height.t=Math.max(40,content.scrollHeight+18);await new Promise(r=>setTimeout(r,interval))}
  await new Promise(r=>setTimeout(r,160));done=true;if(node.isConnected)node.outerHTML=bubble('assistant',body,true);
}
async function sendChat(){
 if(sending)return;
 const field=$('#msg'),text=field?.value.trim();
 if(!text)return;
 sending=true;field.value='';field.dispatchEvent(new Event('input',{bubbles:true}));
 $('#send').disabled=true;
 const area=$('#messages');
 area.insertAdjacentHTML('beforeend',bubble('user',text,true).replace('class="bubble ','class="bubble motion-new '));
 const sent=area.lastElementChild,waiting=pendingChat();
 let delivered=false;
 try{
  const token=await getChatSession();
  const result=await api('/api/chat',{token,message:text,clientMessageId:crypto.randomUUID()});
  chatMessages.push({role:'user',body:text});if(!result.manual||result.ownerHandoff)chatMessages.push({role:'assistant',body:result.reply});delivered=true;
  if(waiting?.isConnected){if(result.manual&&!result.ownerHandoff){waiting.remove();showHandoffStatus(result.reply);}else await streamReply(waiting,result.reply);}
  if(result.booking)await bookingForm(token,result.bookingData||{});
  if(result.workDraft&&publicMode)showWorkDraft(result.workDraft);
  if($('#messages'))$('#messages').scrollTop=$('#messages').scrollHeight;
  if(!publicMode)try{await refresh()}catch{}
 }catch(x){
  if(!delivered){sent?.remove();if(field?.isConnected){field.value=text;field.dispatchEvent(new Event('input',{bubbles:true}))}}
  if(x.status===402&&!publicMode)modal('상담 이용 안내',`<p>${e(x.message)}</p>`+actionGroup({keepSize:true},btn('요금제 보기',"$('.modal').remove();go('pricing')",'primary'),btn('건너뛰기',"$('.modal').remove();go('education')")));
  else toast(x.message);
 }finally{waiting?.remove();sending=false;if($('#send'))$('#send').disabled=false}
}
function flipQrTicket(button){
 const show=button.getAttribute('aria-pressed')!=='true';
 button.setAttribute('aria-pressed',String(show));
 button.style.removeProperty('--qr-x');
 button.style.removeProperty('--qr-y');
}
function tiltQrTicket(button,event){
 if(event.pointerType!=='mouse'||button.getAttribute('aria-pressed')==='true'||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 const rect=button.getBoundingClientRect();
 button.style.setProperty('--qr-x',((0.5-(event.clientY-rect.top)/rect.height)*12)+'deg');
 button.style.setProperty('--qr-y',(((event.clientX-rect.left)/rect.width-0.5)*16)+'deg');
}
async function preview(test=false){
 const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(brand=>brand.available):[];
 const brand=brands.find(item=>item.id===previewAgent);
 if(!brand)previewAgent='';
 const appearance=brand?null:await api('/api/appearance');
 const profile=await api('/api/chat-profile?agent='+enc(brand?.id||''));
 const settings={...(brand?brand.settings:{...me.settings,...appearance}),chat_profile:profile,notice:profile.manual_notice};
 const enabled=brand?brand.enabled:me.enabled;
 const status=enabled?'공개 중':'비공개';
 const link=location.origin+'/c/'+(brand?.slug||me.slug);
 const publicNotice=brand?'비공개 상태에서도 관리자 테스트를 할 수 있습니다.':
  !me.public_access?'유료 구독 후 공개 채팅 및 QR을 사용할 수 있습니다.':
  enabled?'고객은 전용 링크와 QR코드로 상담할 수 있습니다.':'공개로 전환하면 고객이 전용 링크와 QR코드로 상담할 수 있습니다.';
 const publicAction=brand?btn('브랜드 설정',`brandEditor='${brand.id}';go('agents')`):
  btn(enabled?'비공개로 전환':'공개로 전환',"act(async()=>{await api('/api/settings',{enabled:!me.enabled},'PATCH');await refresh();render()})",'primary');
 const qr=!brand&&me.public_access?`<div class="preview-qr">
  <button class="qr-ticket" type="button" aria-label="상담 QR코드 보기" aria-pressed="false" onclick="flipQrTicket(this)" onpointermove="tiltQrTicket(this,event)" onpointerleave="this.style.removeProperty('--qr-x');this.style.removeProperty('--qr-y')">
   <span class="qr-ticket-body"><span class="qr-ticket-front" aria-hidden="true"><strong>${e(me.settings.brand||'CS AI')}</strong><span>상담 QR코드 보기</span></span><span class="qr-ticket-back" aria-hidden="true"><img src="/api/qr" width="144" height="144" alt=""></span></span>
  </button>
  ${tooltip('preview-qr-tip','상담 링크 QR을 PNG 이미지로 저장합니다.','<a href="/api/qr" download="csai-qr.png" aria-describedby="preview-qr-tip">QR 저장</a>')}
 </div>`:'';
 const linkControls=`<div class="ui-section ui-stack">
  <div class="preview-heading"><h3>${brand?'브랜드 전용 상담 링크':'전용 상담 링크'}</h3>${statusBadge(status,enabled?'success':'neutral')}</div>
  <div class="preview-link"><input id="public-link" aria-label="전용 상담 링크" readonly value="${e(link)}">${copyButton('링크 복사','public-link')}</div>
  ${splitContent(stack(helperText(publicNotice)+actionGroup(publicAction)),qr)}
 </div>`;
 const localTest=!brand&&cfg.demo&&!cfg.shared_test&&me.sandbox_allowed&&!me.operator&&me.plan==='free';
 const previewLinks=[
  [test?'미리보기로 돌아가기':'AI 상담 테스트','message-circle',test?"go('preview')":"go('test')"],
  ['채팅창 프로필 설정','contact-badge',brand?`openProfileEditor('${brand.id}')`:'openProfileEditor()'],
 ];
 if(brand)previewLinks.push(['브랜드 디자인','settings',`brandDesign('${brand.id}')`]);
 const actions=`<div class="ui-section ui-stack">
  <h3>테스트 및 프로필</h3>
  ${quickActions('테스트 및 프로필',previewLinks)}
  ${brand?'<p class="muted">브랜드별 예약은 일정표에서 설정할 수 있습니다. CRM·업무 데이터 연동은 일부 준비 중입니다.</p>':''}
 </div>`;
 const usage=`<div class="ui-section ui-stack">
  <h3>${brand?'계정 공통 상담량':'상담 사용량'}</h3><p class="preview-usage">${me.remaining.toLocaleString()}회 남음</p>
  <p class="muted">테스트와 실고객 상담은 동일한 사용량으로 차감됩니다.</p>
  ${localTest?`<p class="muted">여러 대화를 확인하려면 유료 구독 예시로 전환하세요. 실제 결제는 없습니다.</p><div class="ui-actions">${btn('로컬 상담 계속 테스트','enableLocalChatTesting()')}</div>`:''}
 </div>`;
 return pageTop(test?'AI 상담 테스트':'채팅창 미리보기',test?(cfg.demo&&!cfg.ai_connected?'AI API 미연결 · 로컬 규칙 기반 응답으로 테스트합니다.':'상담 답변은 사용량에서 차감됩니다.'):'고객은 로그인 없이 상담합니다.')+
  `<div class="preview-brand">${brandSelect('preview-brand',brands,previewAgent,'choosePreviewBrand(this.value)')}</div>
  <div class="preview-workspace">
   <div class="preview-stage preview-mode-page" data-preview-mode="page"><div class="preview-controls"><div class="preview-mode-switch" aria-label="미리보기 유형"><button type="button" aria-pressed="true" onclick="setPreviewMode('page')">페이지형</button><button type="button" aria-pressed="false" onclick="setPreviewMode('widget')">위젯형</button></div><button type="button" class="preview-expand-button" aria-label="전체 화면 미리보기" aria-expanded="false" title="전체 화면 미리보기" onclick="togglePreviewFull()">${workspaceControlIcon('expand')}</button></div>${phone(settings,test,!test)}</div>
   <div class="preview-settings">${card('공개 및 상담 설정',`<div class="ui-stack">${linkControls}${actions}${usage}</div>`)}${test?'':appearance?previewAppearance(appearance,settings.brand):card('채팅 디자인',chatBrandWaveSetting(settings.brand_name_wave,brand.id))}</div>
  </div>`;
}
function fitPreviewToScreen(){const stage=$('.preview-stage');if(!stage)return;if(!matchMedia('(max-width:700px)').matches){stage.style.removeProperty('--preview-fit-height');return;}if(stage.classList.contains('preview-expanded'))return;const phone=stage.querySelector('.phone');if(phone){const top=phone.getBoundingClientRect().top+window.scrollY;stage.style.setProperty('--preview-fit-height',Math.max(340,window.innerHeight-top-14)+'px');}}
window.addEventListener('resize',fitPreviewToScreen);
function setPreviewMode(mode){if(!['page','widget'].includes(mode))return;const stage=$('.preview-stage');if(!stage)return;stage.dataset.previewMode=mode;stage.classList.toggle('preview-mode-page',mode==='page');stage.classList.toggle('preview-mode-widget',mode==='widget');stage.querySelectorAll('.preview-mode-switch button').forEach((b,i)=>b.setAttribute('aria-pressed',String(i===(mode==='page'?0:1))));requestAnimationFrame(fitPreviewToScreen);}
function workspaceControlIcon(kind){
 const paths={expand:'M8 3H3v5 M16 3h5v5 M21 16v5h-5 M3 16v5h5',collapse:'M3 8h5V3 M21 8h-5V3 M16 21v-5h5 M8 21v-5H3',external:'M13 5h6v6 M19 5l-9 9 M19 13v6H5V5h6',send:'M12 19V5 M6 11l6-6 6 6'};
 return '<svg class="workspace-control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+paths[kind]+'"/></svg>';
}
function togglePreviewFull(){const stage=$('.preview-stage');if(stage){const full=stage.classList.toggle('preview-expanded');const b=stage.querySelector('.preview-expand-button');if(b){b.setAttribute('aria-expanded',String(full));b.setAttribute('aria-label',full?'전체 화면 닫기':'전체 화면 미리보기');b.title=full?'전체 화면 닫기':'전체 화면 미리보기';b.innerHTML=workspaceControlIcon(full?'collapse':'expand');}if(!full)requestAnimationFrame(fitPreviewToScreen);}}
function brandSelect(id,brands,value,handler,includeAll=false){return brands.length?label('관리 브랜드',select(id,[...(includeAll?[['all','전체 브랜드']]:[]),['',me.settings.brand+' · 기본'],...brands.map(a=>[a.id,a.settings.brand])],value).replace('<select','<select onchange="'+handler+'"')):''}
function choosePreviewBrand(id){if(sending){toast('답변 완료 후 브랜드를 변경해 주세요.');return;}previewAgent=id;chatSession=null;chatMessages=[];render()}
async function enableLocalChatTesting(){await act(async()=>{if(me.demo_view==='free')await api('/api/demo/view',{mode:'subscriber'});else await api('/api/demo/billing',{plan:'lite',addons:[]});chatSession=null;chatMessages=[];await refresh();await render();toast('유료 구독 예시로 전환했습니다. 실제 결제는 없습니다.')})}
let memoryTransfer=null;let educationAgent='',trainingChat=[],educationMethod='direct',educationDraft=null,educationBusy=false;
const educationMethods=[['direct','직접 교육','대화·업무 지침 입력','messages-square'],['file','파일 교육','PDF·문서·이미지','list'],['website','웹사이트 교육','공개 홈페이지 URL','external-link'],['memory','외부 AI 기억 이전','ChatGPT 대화 이전','receipt']];
function educationCards(){return '<nav class="education-methods" aria-label="교육 방식">'+educationMethods.map(([id,name,desc,icon])=>`<button type="button" data-education-method="${id}" aria-pressed="${educationMethod===id}" onclick="selectEducationMethod('${id}')">${uiIcon(icon)}<span class="education-method-copy"><strong>${e(name)}</strong><small>${e(desc)}</small></span></button>`).join('')+'</nav>'}
function selectEducationMethod(method){
 if(!educationMethods.some(x=>x[0]===method))return;
 educationMethod=method;
 document.querySelectorAll('[data-education-method]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.educationMethod===method)));
 document.querySelectorAll('[data-education-panel]').forEach(el=>{el.hidden=!el.dataset.educationPanel.split(' ').includes(method)});
}
function resetEducationDraft(){educationDraft=null;educationMethod='direct';educationBusy=false;memoryTransfer=null;}
function captureEducationDraft(){
 const root=$('#education-workspace');if(!root)return;
 const values={};for(const id of ['training-text','training-conversation','faq-q','faq-a','education-url']){const el=root.querySelector('#'+id);if(el)values[id]=el.value;}
 const form=root.querySelector('#memory-file')?.form;
 educationDraft={values,dates:form?['start','end'].map(k=>form.elements[k].value):[],files:[...root.querySelectorAll('.file-check')].map(x=>[x.value,x.checked]),upload:[...(root.querySelector('#upload')?.files||[])],memory:[...(root.querySelector('#memory-file')?.files||[])],preview:root.querySelector('#memory-preview'),open:[...root.querySelectorAll('.training-attachments,.training-more')].map(x=>x.open)};
}
function restoreEducationDraft(){
 const root=$('#education-workspace'),d=educationDraft;if(!root)return;
 if(d){
  for(const [id,value] of Object.entries(d.values)){const el=root.querySelector('#'+id);if(el)el.value=value;}
  const selected=new Map(d.files);root.querySelectorAll('.file-check').forEach(x=>{if(selected.has(x.value))x.checked=selected.get(x.value);});
  for(const [id,items] of [['upload',d.upload],['memory-file',d.memory]]){if(!items.length)continue;const el=root.querySelector('#'+id);if(el&&typeof DataTransfer!=='undefined'){const dt=new DataTransfer();items.forEach(f=>dt.items.add(f));el.files=dt.files;}}
  if(d.upload.length)fileDropSelected();
  if(d.memory.length)fileUploadSelected(root.querySelector('#memory-file'));
  const form=root.querySelector('#memory-file')?.form;if(form)d.dates.forEach((v,i)=>{form.elements[['start','end'][i]].value=v;});
  if(d.preview)root.querySelector('#memory-preview')?.replaceWith(d.preview);

  root.querySelectorAll('.training-attachments,.training-more').forEach((el,i)=>{if(d.open[i]!==undefined)el.open=d.open[i];});
 }
 selectEducationMethod(educationMethod);
 renderEducationQuote();
}
function memoryResume(){
 if(memoryTransfer?.agent!==educationAgent)return '';
 return section('memory-resume-heading','이전 작업',
  actionFooter([btn('진행 중인 이전 작업 열기','openMemoryTransfer()')],{divided:false}),
  '선택한 대화와 이전 구간을 이어서 확인할 수 있습니다.');
}
function memoryImportCard(){
 const guide=accordion('사업 정보만 간단히 가져오는 방법',stack(
  helperText('ChatGPT에서 아래 문구로 사업 정보 문서를 만든 뒤 직접 교육에 붙여넣거나 TXT로 등록하세요. 원본 대화 이전과 별개이며, CSAI에서 교육 분석을 시작하면 일반 교육 크레딧이 차감됩니다.')+
  '<textarea readonly aria-label="사업 정보 정리 요청 문구">내가 제공한 정보 중 확인 가능한 사업체 정보, 상품·가격, 업무 흐름, 운영 정책, 고민과 해결 방향, 고객 응대 원칙을 정리해줘. 확정 사실과 아이디어를 구분하고 모르는 내용은 추측하지 마. 개인정보, 계정 비밀번호, API 키와 불필요한 개인 대화는 제외해줘.</textarea>'
 ));
 const upload=fileUpload('memory-file',{
  accept:'.zip,.json',multiple:true,required:true,title:'ChatGPT ZIP 또는 대화 JSON',
  description:'JSON 파일당 최대 128MiB · 소형 ZIP 최대 25MiB',
 });
 const limits=accordion('파일 제한 및 처리 방식',stack(
  helperText('JSON은 최대 20개, 전체 1GiB까지 선택할 수 있습니다. ZIP은 한 개만 선택할 수 있으며 압축을 푼 대화 JSON 합계가 80MiB 이하여야 합니다.')+
  helperText('큰 ZIP은 압축을 푼 뒤 대화 JSON만 선택하세요. 대형 파일은 PC를 권장합니다. 대화 속 첨부파일은 처리하지 않습니다. 선택 대화의 유료 이전은 테스트 결제 환경에서 이용할 수 있습니다.')
 ));
 const form=`<form onsubmit="event.preventDefault();previewMemoryImport(this)">
  ${stack(
   section('memory-upload-heading','대화 파일 등록',stack(upload+limits))+
   section('memory-range-heading','이전할 대화 기간',stack(memoryRangePicker()+dateRangePicker('memory',{named:true})),'기간을 입력하면 해당 범위의 대화만 확인합니다.')+
   '<label class="ui-check"><input class="ui-choice" type="checkbox" name="consent" required><span>자료 처리 권한이 있으며 JSON은 기기에서, 소형 ZIP은 서버에서 일시 분석하는 데 동의합니다.</span></label>'
  )}
  ${actionFooter(['<button type="submit" class="ui-button primary">파일 사전 확인</button>'],{note:'사전 확인은 무료입니다.'})}
 </form>`;
 return card('외부 AI 기억 이전',stack(
  helperText('ChatGPT에서 축적한 사업 정보, 운영 고민, 상품, 업무 흐름과 의사결정 기준을 가져옵니다. 상담 교육 기록 없이도 이용할 수 있습니다. 계정 자동 동기화는 지원하지 않습니다.')+
  guide+form+`<div id="memory-preview" aria-live="polite"></div><div id="memory-resume">${memoryResume()}</div>`
 ));
}
const memoryRangeCalendars=new WeakMap();
function memoryRangePicker(){
 return `<details class="ui-accordion memory-calendar-picker" ontoggle="mountMemoryRange(this)">
  <summary><span>달력에서 기간 선택</span>${uiIcon('chevron-down')}</summary>
  <div class="ui-accordion-content ui-stack">
   ${helperText('시작일을 누른 뒤 날짜 위에 마우스를 올리면 범위를 미리 볼 수 있습니다. 종료일을 누르거나 날짜를 드래그해 선택하세요.')}
   ${calendarGrid('memory-calendar')}
  </div>
 </details>`;
}
function mountMemoryRange(details){
 memoryRangeCalendars.get(details)?.destroy();
 memoryRangeCalendars.delete(details);
 if(!details.open||!details.isConnected)return;
 const start=details.closest('form').querySelector('#memory-start');
 const end=details.closest('form').querySelector('#memory-end');
 const readRange=()=>({
  start:start.value&&(!end.value||start.value<=end.value)?start.value:'',
  end:start.value&&end.value>=start.value?end.value:'',
 });
 const range=readRange(),today=new Date();
 const [year,month]=range.start?range.start.split('-').map(Number):[today.getFullYear(),today.getMonth()+1];
 const root=details.querySelector('#memory-calendar');
 const calendar=DBMotion.calendar(root,{year,month:month-1,range:true,...range,anchor:!!range.start&&!range.end,counts:{}},state=>{
  start.value=state.start||'';
  end.value=state.end||'';
 });
 const listeners=new AbortController();
 const sync=()=>{
  const range=readRange();
  calendar.setRange(range.start,range.end,{notify:false});
 };
 for(const field of [start,end])field.addEventListener('change',sync,{signal:listeners.signal});
 memoryRangeCalendars.set(details,{destroy(){listeners.abort();calendar.destroy();}});
}
function memoryLocalPreview(files,start,end,progress,ids){
 return new Promise((resolve,reject)=>{
  const worker=new Worker('/assets/memory-preview-worker.js');
  worker.onmessage=event=>{const r=event.data;if(r.progress){progress(r.progress);return;}worker.terminate();if(r.error)reject(Error(r.error));else resolve(r.result);};
  worker.onerror=()=>{worker.terminate();reject(Error('기기에서 JSON을 처리하지 못했습니다. 더 작은 파일로 나누거나 PC에서 다시 시도해 주세요.'));};
  worker.postMessage({files,start,end,ids});
 });
}
function showMemoryCandidates(output,result,sourceFiles){
 const items=result.conversations,selected=new Set();let page=0,query='',category='';
 const size=100,categories=[...new Set(items.flatMap(x=>x.categoryHints||[]))].sort();
 const filters=inline(label('제목 검색','<input id="memory-query" data-memory-query type="search">')+
  label('분류',`<select id="memory-category" data-memory-category><option value="">전체</option>${categories.map(x=>`<option value="${e(x)}">${e(x)}</option>`).join('')}</select>`));
 output.innerHTML=section('memory-results-heading','사전 확인 결과',`<div class="memory-results">${stack(
  helperText(`확인한 대화 ${items.length.toLocaleString()}개 · 중복 ${result.duplicates.toLocaleString()}개 · 제외 ${result.excluded.toLocaleString()}개`)+
  helperText('제목 키워드로 분류했습니다. 개인정보 주의 표시와 선택한 대화 내용을 직접 확인하세요.')+
  filters+actionGroup('<button type="button" class="ui-button secondary" data-memory-select>검색 결과 모두 선택</button>','<button type="button" class="ui-button tertiary" data-memory-clear>선택 초기화</button>')+
  '<p class="ui-helper" data-memory-total></p><div data-memory-list class="scrolltext"></div>'+
  inline('<button type="button" class="ui-button secondary ui-sm" data-memory-prev>이전</button><span data-memory-page></span><button type="button" class="ui-button secondary ui-sm" data-memory-next>다음</button>')
 )}${actionFooter(['<button type="button" class="ui-button primary" data-memory-transfer>선택 대화 이전 준비</button>'])}</div>`);
 const get=key=>output.querySelector('[data-memory-'+key+']');
 const filtered=()=>items.filter(x=>(!query||x.title.toLowerCase().includes(query))&&(!category||(x.categoryHints||[]).includes(category)));
 function draw(){const rows=filtered(),pages=Math.max(1,Math.ceil(rows.length/size));page=Math.min(page,pages-1);get('list').innerHTML=rows.slice(page*size,(page+1)*size).map(x=>`<label class="ui-check"><input class="ui-choice" type="checkbox" data-memory-id="${e(x.id)}" ${selected.has(x.id)?'checked':''}><span>${e([x.title,x.date||'날짜 없음',x.messages+'개 메시지',(x.categoryHints||[]).join(', ')].filter(Boolean).join(' · '))}</span></label>`).join('')||emptyState('기간을 바꾸거나 다른 제목으로 검색하세요.',{title:'표시할 대화가 없습니다'});get('page').textContent=(page+1)+' / '+pages;get('prev').disabled=page===0;get('next').disabled=page+1>=pages;total();}
 function total(){let tokens=0;for(const x of items)if(selected.has(x.id))tokens+=x.approxTokens;get('total').textContent='선택 '+selected.size.toLocaleString()+'개 · 약 '+tokens.toLocaleString()+'토큰 (거친 추정, 결제 견적 아님)';}
 get('query').oninput=()=>{query=get('query').value.toLowerCase();page=0;draw();};get('category').onchange=()=>{category=get('category').value;page=0;draw();};
 get('select').onclick=()=>{for(const x of filtered())selected.add(x.id);draw();};get('clear').onclick=()=>{selected.clear();draw();};get('transfer').onclick=()=>prepareMemorySelection(sourceFiles,[...selected],output);get('prev').onclick=()=>{page--;draw();};get('next').onclick=()=>{page++;draw();};
 output.onchange=ev=>{const id=ev.target.dataset.memoryId;if(id){if(ev.target.checked)selected.add(id);else selected.delete(id);total();}};draw();
}
function memoryProgress(labels){
 const element=document.createElement('details');
 element.className='memory-import-progress ui-accordion';
 element.open=true;
 element.innerHTML=`<summary><span>ChatGPT 대화 가져오기</span><small data-progress-summary>대기</small>${uiIcon('chevron-down')}</summary><ol>${labels.map(text=>`<li data-state="pending"><div class="memory-progress-row"><i aria-hidden="true"></i><span>${e(text)}</span><small>대기</small></div><p hidden></p></li>`).join('')}</ol>`;
 const steps=element.querySelectorAll('li');
 const states={pending:'대기',running:'진행 중',done:'완료',error:'오류'};
 return {element,set(index,state,detail=''){
  const step=steps[index];
  step.dataset.state=state;
  if(state==='running')step.setAttribute('aria-current','step');
  else step.removeAttribute('aria-current');
  step.querySelector('small').textContent=states[state];
  const note=step.querySelector('p');
  note.textContent=detail;note.hidden=!detail;
  const completed=state==='done'&&index===steps.length-1;
  element.querySelector('[data-progress-summary]').textContent=completed?'완료':state==='error'?'오류':'진행 중';
  if(completed)element.open=false;
 }};
}
async function previewMemoryImport(form){
 const output=$('#memory-preview'),button=form.querySelector('[type=submit]'),files=[...$('#memory-file').files];
 if(!files.length||button.disabled||educationBusy)return;if(!form.elements.consent.checked){toast('파일 처리 동의가 필요합니다.');return;}
 const start=form.elements.start.value,end=form.elements.end.value;
 if(start&&end&&start>end){toast('시작일은 종료일보다 늦을 수 없습니다.');return;}
 const local=files.every(f=>/\.json$/i.test(f.name));
 const progress=memoryProgress(['파일 형식 확인',local?'기기에서 대화 목록 읽기':'ZIP 업로드 및 대화 목록 읽기','사전 확인 결과']);
 let step=0;
 button.disabled=true;button.setAttribute('aria-busy','true');educationBusy=true;
 output.replaceChildren(progress.element);
 progress.set(step,'running');
 progress.element.scrollIntoView({block:'nearest'});
 try{
  let result;
  if(!local&&(files.length!==1||!/\.zip$/i.test(files[0].name)))throw Error('JSON 여러 개 또는 ZIP 한 개를 선택하세요.');
  if(!local&&files[0].size>25*1024*1024)throw Error('큰 ZIP은 압축을 푼 뒤 대화 JSON 파일들을 선택하세요.');
  progress.set(step++,'done');
  progress.set(step,'running');
  if(local){
   result=await memoryLocalPreview(files,start,end,p=>progress.set(step,'running',p));
  }else{
   const dates=new URLSearchParams();if(start)dates.set('start',start);if(end)dates.set('end',end);
   const response=await fetch('/api/memory-import/preview?'+dates,{method:'POST',body:files[0]});
   result=await response.json();if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'파일 확인에 실패했습니다.');
  }
  progress.set(step++,'done');
  showMemoryCandidates(output,result,files);
  progress.set(step,'done');
  output.prepend(progress.element);
 }catch(err){
  progress.set(step,'error',err.message);
  if(!output.contains(progress.element))output.prepend(progress.element);
 }
 finally{button.disabled=false;button.removeAttribute('aria-busy');educationBusy=false;}
}
const educationExamples=[
 ['말투와 답변 길이','존댓말로 핵심을 먼저 두 문장 이내로 답해 주세요. 이모지는 쓰지 마세요.'],
 ['상담 시간과 예외','상담은 평일 오후 6시에 종료합니다. 오후 6시 이후에는 다음 영업일에 확인한다고 안내하고, 답변 시각은 약속하지 마세요.'],
 ['가격과 견적','공개된 정가만 안내해 주세요. 맞춤 견적을 물으면 상품과 수량을 먼저 확인하고, 최종 금액은 담당자에게 넘겨 주세요.'],
 ['예약·환불 안내','예약이나 환불을 확정하기 전에 주문 또는 예약 번호를 물어보고, 담당자가 확인한다고 안내해 주세요.'],
 ['자주 묻는 질문과 답변','예약 변경은 어디서 하나요? => 예약 번호와 변경을 원하는 날짜를 알려주시면 담당자가 가능 여부를 확인합니다.'],
 ['모르는 질문의 담당자 연결','교육 자료에서 확인되지 않는 질문은 추측하지 말고, 문의 내용을 한 문장으로 정리한 뒤 담당자 확인을 안내해 주세요.'],
];
function educationExampleGuide(){
 return accordion('교육 입력 예시',helperText('예시 문구를 입력칸에 넣고, 실제 운영 기준에 맞게 고쳐 쓰세요.')+
  `<ul class="education-examples">${educationExamples.map(([title,example],index)=>`<li><strong>${e(title)}</strong>
   <p>${e(example)}</p>${btn('예시 넣기',`addEducationExample(${index})`,'secondary ui-sm')}</li>`).join('')}</ul>`);
}
function addEducationExample(index){
 const field=$('#training-text'),example=educationExamples[index]?.[1];
 if(!field||!example||educationBusy)return;
 const extra=(field.value?'\n':'')+example;
 if(field.value.length+extra.length>field.maxLength){toast('교육 입력 글자 수를 확인하세요.');return;}
 field.setRangeText(extra,field.value.length,field.value.length,'end');
 field.focus();field.dispatchEvent(new Event('input',{bubbles:true}));
}
const responseLevelNames=['수동적','균형','자유롭게'];
const responseLevelHints=['일반 문의에 짧게 답한 뒤 담당자에게 넘깁니다. 진행 중인 예약과 업무 요청은 이어갑니다.','교육한 내용과 기존 상담 기준에 따라 답합니다.','AI가 교육 자료를 바탕으로 필요한 후속 질문이나 선택지를 제안합니다.'];
function responseControl(config){
 const slider=`<div class="response-slider" style="--position:${config.level*50}%">
  <output id="response-level-name" for="response-level">${responseLevelNames[config.level]}</output>
  <input id="response-level" type="range" min="0" max="2" step="1" value="${config.level}" aria-label="상담 주도성" aria-describedby="response-level-hint" aria-valuetext="${responseLevelNames[config.level]}" oninput="updateResponseLevel(this)">
 </div>`;
 return accordion('AI 상담 진행 방식 · '+responseLevelNames[config.level],stack(slider+'<p id="response-level-hint" class="ui-helper">'+responseLevelHints[config.level]+'</p>'+
 checkbox('response-notify','사장님께 알리기',{checked:config.notify,hint:'미학습·민감 문의를 직접 상담으로 넘기고 관리자 알림함에 표시합니다.'})+
 label('고객에게 보낼 문구',ta('response-message',config.message)))+actionFooter([btn('상담 방식 저장','saveResponseControl()','primary')]),{className:'response-control'});
}
function updateResponseLevel(input){
 input.parentElement.style.setProperty('--position',(Number(input.value)*50)+'%');
 const name=responseLevelNames[input.value];input.setAttribute('aria-valuetext',name);
 $('#response-level-name').textContent=name;$('#response-level-hint').textContent=responseLevelHints[input.value];
}
async function saveResponseControl(){await act(async()=>{
 await api('/api/response-style',{agent:educationAgent,level:Number(val('response-level')),notify:checked('response-notify'),message:val('response-message')});$('.response-control summary span').textContent='AI 상담 진행 방식 · '+responseLevelNames[val('response-level')];toast('상담 방식을 저장했습니다.');
})}
async function education(){
 let brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available):[],agent=brands.find(x=>x.id===educationAgent);if(!agent)educationAgent='';
 files=await api('/api/files?agent='+enc(educationAgent));
 let jobs=(await api('/api/training')).filter(j=>(j.agent||'')===educationAgent),faq=agent?[]:await api('/api/faq');
 const upload=fileUpload('upload',{
  title:'교육 자료 파일',zoneId:'file-drop',multiple:true,onChange:'fileDropSelected()',
  accept:'.txt,.md,.csv,.pdf,.png,.jpg,.jpeg,.webp,.docx,.xlsx,.hwpx',
  description:'PDF, 문서, 이미지, 채팅 내보내기 · 여러 파일 선택 가능',
 });
 const materials=card('교육 자료 등록',stack(
  helperText('등록한 파일은 교육 입력에서 선택해 분석할 수 있습니다.')+
  upload+'<ul id="file-drop-list" class="file-drop-list" aria-live="polite"></ul>'+
  helperText('파일당 5MB · PDF 30페이지 · HWPX 지원 · 구형 HWP는 PDF로 변환 · 스크린샷의 개인정보는 먼저 지워주세요.')
 )+actionFooter([btn('선택한 파일 등록','uploadFiles()','primary')]));
 const website=card('웹사이트 자료 등록',helperText('공개 웹페이지 URL을 등록한 뒤 교육 입력에서 자료를 선택해 분석하세요.')+
  label('공개 웹페이지 URL',input('education-url','','url','https://'))+actionFooter([btn('웹페이지 자료 가져오기','importEducationUrl()','primary')]));
 let conversation=`<div class="training-conversation">${label('기존 상담 내역 붙여넣기',`<textarea id="training-conversation" maxlength="30000" placeholder="고객: 예약 가능한 날짜가 언제예요?&#10;나: 원하시는 날짜 알려주시면 일정 확인해드릴게요."></textarea>`)}<p class="muted">고객과 내가 실제로 주고받은 대화를 붙여넣으세요. AI는 내 답변을 말투·응대 예시로 분석합니다. 이름·전화번호·주소 등 개인정보는 먼저 지워주세요.</p></div>`;
 let fileList=files.map(f=>`<div class="row line"><input class="check file-check" type="checkbox" value="${e(f.id)}" aria-label="${e(f.name)} 교육에 포함" checked><span>${e(f.name)} <small>${f.chars}자</small></span>${btn('삭제',`deleteVisibleRow('/api/files/${f.id}?agent='+enc(educationAgent),this)`)}</div>`).join('')||emptyState('등록된 자료가 없습니다. 지침이나 상담 내역만 입력해도 교육할 수 있습니다.');
 let chatLines=`<div class="training-dialogue" role="log" aria-label="AI 교육 대화"><div class="training-turn assistant"><b>CS AI</b><p>안녕하세요. 먼저 어떤 말투로 고객을 상담할지 알려주세요. 예를 들어 “AI 티 안 나게 짧게 답해줘”, “내가 쓰는 말투처럼”, “이모지는 쓰지 마”처럼 편하게 말해 주세요.</p><p>말씀하신 내용을 분석해 교육 초안을 만들고, 확인하신 뒤 상담에 반영할게요.</p></div>${trainingChat.map(t=>`<div class="training-turn ${t.role}"><b>${t.role==='user'?'나':'CS AI'}</b><p>${e(t.text).replace(/\n/g,'<br>')}</p>${t.job?btn('이 결과 검토하기',`document.getElementById('training-results').scrollIntoView({behavior:'smooth'})`):''}</div>`).join('')}</div>`;
 const history=accordion('상담 내역 붙여넣기·등록 자료 선택 (선택)',helperText('고객과 주고받은 대화를 붙여넣거나 등록해 둔 파일·웹사이트 자료를 선택해 이번 분석에 함께 넣을 수 있습니다.')+conversation+fileList,
  {className:'training-attachments'});
 const training=card('교육 입력',`<p class="muted">상담 기준을 입력하고 비용을 확인하세요. 분석을 시작하면 교육 초안이 만들어지고, 검토 후 승인하면 상담에 반영됩니다.</p>
  ${chatLines}
  <form class="training-composer" onsubmit="event.preventDefault();estimateTraining()">
   ${label('상담 방식 또는 업무 지침','<textarea id="training-text" maxlength="30000" placeholder="예: 고객에게 내 말투처럼 짧고 자연스럽게 답해줘."></textarea>')}
   ${actionFooter(['<button class="ui-button primary" type="submit">분석 비용 확인</button>',trainingChat.length?btn('대화 새로 시작','if(!educationBusy){trainingChat=[];estimate=null;render()}'):''],{divided:false,note:'비용 확인만으로는 크레딧이 차감되지 않습니다.'})}
   <div id="estimate" aria-live="polite"></div>
   ${history}
   ${educationExampleGuide()}
  </form>`);

 const testFooter=actionFooter([btn('AI 상담 테스트',"previewAgent=educationAgent;chatSession=null;chatMessages=[];go('test')")],
  {note:'승인한 교육이 실제 답변에 반영되는지 확인하세요.'});
 let results=`<div id="training-results">${card('교육 결과 검토 및 반영',(jobs.filter(j=>j.result).map(j=>`<div class="line"><strong>${e(j.agent?'추가 브랜드 상담원':'기본 상담원')} · ${e(j.state==='published'?'반영 완료':'검토 필요')} · ${j.cost} C</strong><p>${e(j.result.style||'말투 분석 없음')}</p>${j.result.rules?.length?`<ul>${j.result.rules.map(rule=>`<li>${e(rule)}</li>`).join('')}</ul>`:''}${j.result.faq?.length?accordion('모범 질문·답변 '+j.result.faq.length+'개',
   `<dl class="training-faq-preview">${j.result.faq.map(pair=>`<div><dt>${e(pair.q)}</dt><dd>${e(pair.a)}</dd></div>`).join('')}</dl>`):''}${j.result.conflicts?.length?`<p class="muted">확인 필요: ${e(j.result.conflicts.join(' · '))}</p>`:''}${j.state==='review'?actionGroup(btn('초안 직접 수정',`reviewModal('${j.id}')`),btn('승인 및 상담에 반영',`act(async()=>{await api('/api/training/${j.id}/publish',{});await refresh();render()})`,'primary')):''}</div>`).join('')||emptyState('교육을 시작하면 검토할 결과가 표시됩니다. 승인하면 고객 상담에 반영됩니다.',{title:'아직 분석 결과가 없습니다',icon:'list'}))+testFooter)}</div>`;
 let direct=`<p class="muted">고객 질문과 원하는 답변을 알려주세요. 입력과 견적 확인은 무료이고, 교육을 시작하면 교육 크레딧이 차감됩니다. 결과를 검토하고 승인해야 상담에 반영됩니다.</p>${label('고객 질문',input('faq-q','','text','예: 예약은 어떻게 하나요?'))}${label('내가 원하는 답변',ta('faq-a'))}<p class="muted">같은 문장만 찾는 방식은 아닙니다. 실제 AI는 유사한 질문에도 교육한 답변을 참고하지만, 표현이 크게 다르면 놓칠 수 있어 상담 테스트로 확인해 주세요. 로컬 데모는 단순 유사도 판정입니다.</p>${actionArea(btn('교육 비용 확인',"act(async()=>{showEducationQuote(await api('/api/faq',{q:val('faq-q'),a:val('faq-a'),agent:educationAgent}))})",'primary'))}${faq.map(f=>`<div class="line"><b>${e(f.q)}</b><p>${e(f.a)}</p>${btn('삭제',`deleteVisibleRow('/api/faq/${f.id}',this)`)}</div>`).join('')}`;
  return pageTop('AI 교육시키기','교육 방식을 선택하고 결과를 검토한 뒤 상담원에 반영하세요.')+`<div id="education-workspace"><div class="training-credit-summary training-credit-top"><span>교육 크레딧 <strong>${me.credits} C</strong><small>교육 분석을 시작할 때 차감됩니다.</small></span>${btn('크레딧 내역',"go('credits')")}</div>${brandSelect('training-agent',brands,educationAgent,'trainingAgentChanged(this.value)')}${educationCards()}<div id="training-materials" data-education-panel="file" hidden>${materials}</div><div data-education-panel="website" hidden>${website}</div><div data-education-panel="direct file website">${training}</div><div data-education-panel="direct">${card('추가 교육 자료',accordion('모범 답변으로 교육하기',direct,{className:'training-more'}))}</div><div id="memory-import" data-education-panel="memory" hidden>${memoryImportCard()}</div>${results}</div>`;
}

function fileDropSelected(){const files=[...($('#upload')?.files||[])];const list=$('#file-drop-list');if(list)list.innerHTML=files.map(f=>`<li><span>${e(f.name)}</span><small>${(f.size/1048576).toFixed(1)} MB</small></li>`).join('');fileDropState(files.length?'selected':'idle',files.length?`${files.length}개 파일 선택됨`:'파일을 이곳에 놓거나 눌러 선택하세요')}
function fileDropState(state,title,subtitle){const zone=$('#file-drop');if(!zone)return;zone.classList.remove('selected','uploading','success','error');if(state!=='idle')zone.classList.add(state);zone.querySelector('button').disabled=state==='uploading';zone.setAttribute('aria-busy',String(state==='uploading'));if(title)$('#file-drop-title').textContent=title;if(subtitle)$('#file-drop-subtitle').textContent=subtitle}
async function uploadFiles(){await act(async()=>{if(educationBusy)return;const source=$('#upload');let fs=[...source.files];if(!fs.length)throw Error('파일을 선택하세요.');const allowed=/\.(txt|md|csv|pdf|png|jpe?g|webp|docx|xlsx|hwpx)$/i;for(let f of fs){if(f.size>5e6)throw Error('파일당 5MB 이하');if(!allowed.test(f.name))throw Error('지원하지 않는 파일 형식입니다.')}let index=0;educationBusy=true;try{for(let f of fs){index++;fileDropState('uploading',`${index}/${fs.length} · ${f.name}`,'파일을 읽고 있습니다.');let data=await new Promise((resolve,reject)=>{let r=new FileReader();r.onprogress=ev=>{if(ev.lengthComputable){const p=Math.round(ev.loaded/ev.total*100);$('#file-drop')?.style.setProperty('--upload-progress',`${p}%`);if($('#file-drop-subtitle'))$('#file-drop-subtitle').textContent=`파일 읽는 중 · ${p}%`}};r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f)});if($('#file-drop-subtitle'))$('#file-drop-subtitle').textContent='서버에 등록하고 있습니다.';await api('/api/files',{name:f.name,data,agent:educationAgent})}fileDropState('success',`${fs.length}개 파일 등록 완료`,'AI 교육 자료로 사용할 수 있습니다.');source.value='';if(educationDraft)educationDraft.upload=[];const current=$('#upload');if(current)current.value='';toast('자료 등록 완료');if(route==='education')await render()}catch(err){fileDropState('error','등록에 실패했습니다.',err.message||'다시 시도해 주세요.');throw err}finally{educationBusy=false}})}
function renderEducationQuote(){const area=$('#estimate');if(!area)return;if(!estimate){area.innerHTML='';return;}const q=estimate,credits=me?.credits??q.credits;area.innerHTML=educationBusy?'<p role="status">교육 작업이 진행 중입니다.</p>':`<div class="ui-feedback"><h3>교육 비용 확인</h3><p>분석 시작 시 최대 ${q.maxCredits} C를 예약하고 실제 사용분만 차감합니다. 보유 ${credits} C</p><p>초안을 직접 수정·승인하는 데에는 추가로 차감되지 않습니다.</p>${actionGroup(credits>=q.maxCredits?btn('분석 시작','runTraining()','primary'):btn('크레딧 충전',"go('credits')"))}</div>`;}
function trainingAgentChanged(id){if(educationBusy){toast('교육 작업이 진행 중입니다.');const el=$('#training-agent');if(el)el.value=educationAgent;return;}educationAgent=id;trainingChat=[];estimate=null;resetEducationDraft();$('#education-workspace')?.remove();render()}
async function estimateTraining(){await act(async()=>{if(educationBusy)return;const input=$('#training-text');const prompt=input.value.trim(),conversation=val('training-conversation').trim();const selectedFiles=[...document.querySelectorAll('.file-check:checked')];if(!prompt&&!conversation&&!selectedFiles.length)throw Error('상담 기준을 입력하거나 분석 자료를 선택하세요.');const turns=[...trainingChat.filter(t=>t.role==='user').map(t=>t.guidance??t.text),prompt],guidance=turns.filter(Boolean).join('\n');if(guidance.length>30000)throw Error('대화가 길어졌습니다. 새 대화를 시작해 주세요.');const request={text:guidance,conversation,agent:educationAgent,files:selectedFiles.map(x=>x.value)};const submit=input.form.querySelector('button[type=submit]');educationBusy=true;submit.disabled=true;submit.setAttribute('aria-busy','true');try{let quote=await api('/api/training/estimate',request);estimate=quote;trainingChat.push({role:'user',text:prompt||'입력한 상담 내역과 선택한 자료 분석 요청',guidance:prompt});if(input.value.trim()===prompt)input.value='';if(educationDraft?.values['training-text']?.trim()===prompt)educationDraft.values['training-text']='';await refresh();}finally{educationBusy=false;submit.disabled=false;submit.removeAttribute('aria-busy');}if(route==='education')await render();})}
async function runTraining(){await act(async()=>{if(!estimate||educationBusy)return;educationBusy=true;let area=$('#estimate');if(area)area.innerHTML='<div class="training-turn assistant training-pending" role="status">'+motionDots+'<span>말투와 응대 기준을 분석하고 있어요…</span></div>';try{let r=await api('/api/training/'+estimate.id+'/run',{}),result=r.result||{},parts=[];if(result.style)parts.push('말투: '+result.style);if(result.rules?.length)parts.push('응대 기준: '+result.rules.slice(0,3).join(' / '));if(result.conflicts?.length)parts.push('확인 필요: '+result.conflicts.slice(0,2).join(' / '));trainingChat.push({role:'assistant',text:(result.demo?'로컬 데모 분석입니다. 실제 AI 모델 분석은 연결 후 확인할 수 있어요.\n':'')+(parts.join('\n')||'교육 초안을 만들었습니다.')+'\n아래 결과를 검토하고 승인하면 상담에 반영됩니다. 직접 고치려면 결과에서 ‘초안 직접 수정’을 선택하세요. AI 분석을 다시 하려면 먼저 비용을 확인하세요.',job:r.id});estimate=null;toast(`교육 결과 생성 · ${r.cost} C 사용`);await refresh();if(route==='education')await render()}catch(err){estimate=null;throw err}finally{educationBusy=false;renderEducationQuote()}})}
function style(){let s=me.settings;return pageTop('상담 스타일 설정','AI가 답변할 말투와 기준을 설정하세요.')+card('말투 및 표현',`${label('말투',select('tone',['자연스럽고 정중하게','정중하고 전문적으로','친근하고 편안하게','자료의 기존 말투'].map(x=>[x,x]),s.tone))}<p><label><input class="check" id="emoji" type="checkbox" ${s.emoji?'checked':''}> 이모지 사용</label></p><p class="muted">상담 지침은 교육센터에서 크레딧을 사용해 변경할 수 있습니다.</p>${btn('상담 지침 교육',"educationAgent='';go('education')")}${label('첫 인사',input('welcome',s.welcome))}${label('미학습 질문 안내',ta('fallback',s.fallback))}${btn('저장',"saveStyle()",'primary')}`)}
async function saveStyle(){await act(async()=>{await api('/api/settings',{tone:val('tone'),emoji:checked('emoji'),welcome:val('welcome'),fallback:val('fallback')},'PATCH');await refresh();toast('저장 완료')})}
const modeLabels={general:'일반 상담',price:'가격 안내',location:'위치·영업시간',purchase:'구매처·결제 안내',unknown:'새로운 질문',booking:'예약 접수·확정',change:'예약 변경·취소',complaint:'불만 접수',email:'이메일 알림'};
let settingsStackPage='root';
const queuedSettingsMoves=new WeakMap();
const settingsStackItems=[
 ['company','업체 정보','업체명, 공지, 영업시간, 판매처','contact-badge'],
 ['business','업종 및 원하는 업무','사업 업종과 새 고객 상담 방식','shopping-bag'],
 ['permissions','업무별 응대 권한','업무별 자동·수동 응대 설정','settings'],
 ['appearance','채팅창 외형 및 링크','로고, 채팅 디자인, 상담 주소','message-circle'],
 ['automation','AI 자동화 위험 확인','자동화 정책 및 확인 기록','list'],
];
function settingsCompany(s){
 return label('업체명',input('brand',s.brand))+
  label('공지사항',ta('notice',s.notice))+
  label('가격 안내',ta('price',s.price))+
  label('위치 및 지도',ta('location',s.location))+
  label('영업시간',ta('hours',s.hours))+
  label('판매처 링크 (한 줄에 이름 | HTTPS 주소)',ta('links',s.links.map(x=>x.name+' | '+x.url).join('\n')))+
  actionFooter([btn('채팅창 프로필 설정',"openProfileEditor()"),btn('업체 정보 저장','saveSettings()','primary')]);
}
function settingsPermissions(s){
 const fields=Object.entries(modeLabels).map(([key,name])=>settingRow('mode-'+key,name,'',
  select('mode-'+key,[['auto','자동'],['manual','수동'],['off','OFF']],s.modes[key]))).join('');
 return `<div class="ui-setting-list">${fields}</div>`+actionFooter([btn('권한 저장','saveModes()','primary')],
  {note:'외부 환불은 안내만 가능합니다. 예약 자동 확정에는 추가 기능 권한이 필요합니다.'});
}
async function settings(){
 const s=me.settings,r=await api('/api/appearance');
 const panels={
  company:settingsCompany(s),business:businessProfileCard(s),permissions:settingsPermissions(s),
  appearance:settingsAppearance(r),automation:settingsAutomation(),
 };
 const panelAttributes=(id)=>`data-settings-panel="${id}"${settingsStackPage===id?'':' hidden inert'}`;
 const home=`<section class="settings-stack-panel" ${panelAttributes('root')} aria-label="설정 목록">
  <ul class="settings-stack-menu">
   ${settingsStackItems.map(([id,title,hint,icon])=>`<li><button type="button" data-settings-open="${id}" aria-controls="settings-panel-${id}">
    <span class="settings-stack-icon">${uiIcon(icon)}</span>
    <span class="settings-stack-copy"><strong data-settings-label>${title}</strong><small>${hint}</small></span>
    ${uiIcon('chevron-right')}
   </button></li>`).join('')}
  </ul>
 </section>`;
 const pages=settingsStackItems.map(([id,title])=>`<section class="settings-stack-panel settings-stack-detail" ${panelAttributes(id)}
  id="settings-panel-${id}" aria-labelledby="settings-title-${id}">
   <header class="settings-stack-header">
    <button type="button" class="ui-button tertiary ui-sm" data-settings-back aria-label="설정 목록으로 돌아가기">${uiIcon('chevron-right')} 설정 목록</button>
    <h2 id="settings-title-${id}">${title}</h2>
   </header>
   <div class="settings-stack-body">${panels[id]}</div>
 </section>`).join('');
 return pageTop('설정','업체 정보, 공식 구매처 및 업무별 권한을 설정합니다.')+
  `<div class="settings-stack" data-settings-active="${settingsStackPage}">${home}${pages}</div>`;
}
function settingsStackPanel(stack,id){return stack.querySelector(`[data-settings-panel="${id}"]`);}
function moveSettingsStack(stack,next,opener=null,dragOffset=0){
 const active=stack.dataset.settingsActive;
 if(next===active)return;
 if(stack.dataset.moving){queuedSettingsMoves.set(stack,{next,opener});return;}
 const from=settingsStackPanel(stack,active),to=settingsStackPanel(stack,next);
 if(!to)return;
 const fromHeight=from.getBoundingClientRect().height;
 const width=stack.clientWidth,forward=next!=='root';
 const source=opener?.querySelector('[data-settings-label]');
 const origin=source?.getBoundingClientRect();
 const focus=forward?to.querySelector('[data-settings-back]'):stack.querySelector(`[data-settings-open="${active}"]`);
 settingsStackPage=next;stack.dataset.settingsActive=next;
 from.inert=true;to.hidden=false;to.inert=false;
 from.style.transform='';to.style.transform='';stack.style.height='';
 const finish=()=>{
  from.hidden=true;delete stack.dataset.moving;
  const queued=queuedSettingsMoves.get(stack);
  queuedSettingsMoves.delete(stack);
  if(!stack.isConnected)return;
  if(queued){moveSettingsStack(stack,queued.next,queued.opener);return;}
  focus?.focus({preventScroll:forward});
 };
 if(matchMedia('(prefers-reduced-motion: reduce)').matches||!stack.animate||!width){finish();return;}
 stack.dataset.moving='true';
 const toHeight=to.getBoundingClientRect().height;
 const spring={duration:380,easing:'cubic-bezier(.22,.74,.24,1)',fill:'both'};
 const slide=(panel,start,end)=>panel.animate([{transform:`translateX(${start}px)`},{transform:`translateX(${end}px)`}],spring);
 const animations=[
  stack.animate([{height:fromHeight+'px'},{height:toHeight+'px'}],spring),
  slide(from,forward?0:dragOffset,forward?-width*.3:width),
  slide(to,forward?width:(dragOffset-width)*.3,0),
 ];
 if(origin){
  const heading=to.querySelector('h2'),bounds=heading.getBoundingClientRect();
  // The entering panel already contributes the horizontal offset.
  const ratio=parseFloat(getComputedStyle(source).fontSize)/parseFloat(getComputedStyle(heading).fontSize);
  animations.push(heading.animate([
   {transform:`translate(${origin.left-bounds.left}px,${origin.top-bounds.top}px) scale(${ratio})`},
   {transform:'none'},
  ],spring));
  animations.push(source.animate([{opacity:0},{opacity:0}],spring));
 }
 animations[0].onfinish=()=>{animations.forEach(animation=>animation.cancel());finish();};
}
function mountSettingsStack(){
 const stack=$('.settings-stack');
 if(!stack)return;
 stack.addEventListener('click',event=>{
  const opener=event.target.closest('[data-settings-open]');
  if(opener)moveSettingsStack(stack,opener.dataset.settingsOpen,opener);
  else if(event.target.closest('[data-settings-back]'))moveSettingsStack(stack,'root');
 });
 stack.addEventListener('keydown',event=>{
  if(event.key!=='Escape'||stack.dataset.settingsActive==='root')return;
  event.preventDefault();event.stopPropagation();moveSettingsStack(stack,'root');
 });
 let swipe=null;
 stack.addEventListener('pointerdown',event=>{
  const edge=stack.getBoundingClientRect().left;
  if(event.pointerType!=='touch'||!event.isPrimary||event.clientX-edge>36||
     stack.dataset.settingsActive==='root'||stack.dataset.moving||
     event.target.closest('button,input,select,textarea,label,a,summary'))return;
  swipe={pointer:event.pointerId,x:event.clientX,y:event.clientY,t:performance.now(),distance:0,drawing:false};
 });
 stack.addEventListener('pointermove',event=>{
  if(swipe?.pointer!==event.pointerId)return;
  const dx=event.clientX-swipe.x,dy=Math.abs(event.clientY-swipe.y);
  if(!swipe.drawing&&(dy>12&&dy>dx||dx<-8)){swipe=null;return;}
  if(dx<8&&!swipe.drawing)return;
  if(!swipe.drawing){
   swipe.drawing=!matchMedia('(prefers-reduced-motion: reduce)').matches;
   if(swipe.drawing){
    stack.setPointerCapture(event.pointerId);
    stack.style.height=stack.getBoundingClientRect().height+'px';
    settingsStackPanel(stack,'root').hidden=false;
   }
  }
  swipe.distance=Math.min(stack.clientWidth,Math.max(0,dx));
  if(swipe.drawing){
   settingsStackPanel(stack,stack.dataset.settingsActive).style.transform=`translateX(${swipe.distance}px)`;
   settingsStackPanel(stack,'root').style.transform=`translateX(${(swipe.distance-stack.clientWidth)*.3}px)`;
  }
 });
 function endSwipe(event){
  if(swipe?.pointer!==event.pointerId)return;
  const {distance,t,drawing}=swipe;swipe=null;
  if(event.type==='pointerup'&&(distance>stack.clientWidth*.35||distance>32&&distance/(performance.now()-t)>.5)){
   moveSettingsStack(stack,'root',null,drawing?distance:0);return;
  }
  if(!drawing)return;
  const from=settingsStackPanel(stack,stack.dataset.settingsActive),under=settingsStackPanel(stack,'root');
  under.hidden=true;under.style.transform='';stack.style.height='';
  from.style.transform='';
  from.animate?.([{transform:`translateX(${distance}px)`},{transform:'none'}],{duration:180,easing:'ease-out'});
 }
 stack.addEventListener('pointerup',endSwipe);
 stack.addEventListener('pointercancel',endSwipe);
}
const industryOptions=['전자상거래·쇼핑몰','음식점·카페','숙박·여행','뷰티·미용','교육·학원','전문 상담·서비스','병원·건강','사진·촬영','IT·SaaS','부동산','제조·유통','기타'];
const workOptions=['일반 고객 상담','상품·서비스 안내','예약 접수','예약 변경·취소','견적·제안서','고객 관리','업무 요청','불만·환불 안내','다국어 상담','외부 채널 연결','알림·보고서'];
function businessProfileCard(s){
 const options=(key,values)=>[...new Set([...values,...(s[key]||[])])].map(x=>`<label class="line"><input type="checkbox" class="check" data-profile="${key}" value="${e(x)}" ${(s[key]||[]).includes(x)?'checked':''}> ${e(x)}</label>`).join('');
 return `<p class="muted">업종과 원하는 업무를 여러 개 선택할 수 있습니다. 선택만으로 유료 상품이 추가되거나 결제되지 않습니다.</p><details class="ui-disclosure"><summary>사업 업종 선택</summary>${options('industries',industryOptions)}${label('기타 업종 추가 (쉼표 구분)',input('custom-industries'))}</details><details class="ui-disclosure"><summary>원하는 업무 선택</summary>${options('desired_work',workOptions)}${label('기타 업무 추가 (쉼표 구분)',input('custom-work-intent'))}</details>${label('새 고객 상담 기본 방식',select('consultation-mode',[['ai','AI가 먼저 상담'],['staff','담당자가 직접 상담']],s.consultation_mode||'ai'))}<p class="muted">담당자 직접 상담은 AI 답변 사용량을 차감하지 않습니다. 기존 상담의 전환은 통합 상담함에서 별도로 할 수 있습니다. 공개 상담은 유료 구독 또는 초청 체험이 필요합니다.</p>${actionFooter([btn('업종·업무 및 상담 방식 저장','saveBusinessProfile()','primary')])}`;
}
async function saveBusinessProfile(){await act(async()=>{const values=(key,id)=>[...new Set([...document.querySelectorAll('[data-profile="'+key+'"]:checked')].map(x=>x.value).concat(val(id).split(',').map(x=>x.trim()).filter(Boolean)))];await api('/api/settings',{industries:values('industries','custom-industries'),desired_work:values('desired_work','custom-work-intent'),consultation_mode:val('consultation-mode')},'PATCH');await refresh();toast('설정 저장 완료');render()})}
async function saveSettings(){await act(async()=>{let links=val('links').split('\n').filter(x=>x.trim()).map(x=>{let [name,url]=x.split('|').map(x=>x.trim());return {name,url}});await api('/api/settings',{brand:val('brand'),notice:val('notice'),price:val('price'),location:val('location'),hours:val('hours'),links},'PATCH');await refresh();toast('저장 완료')})}
async function saveModes(){await act(async()=>{await api('/api/settings',{modes:Object.fromEntries(Object.keys(modeLabels).map(k=>[k,val('mode-'+k)]))},'PATCH');await refresh();toast('권한 저장 완료')})}
let inboxKind='customer',inboxQuery='',inboxSource='all',inboxUnread=false,inboxPriority='all',inboxSnapshot='',inboxPolling=null,inboxBrands=[],inboxSnippets=[];
const channelNames={public:'CS AI 웹 상담',test:'관리자 테스트',naver:'네이버 톡톡',kakao:'카카오 AI 챗봇',telegram:'텔레그램',line:'LINE',instagram:'인스타그램 DM'};
function inboxChannelBadge(t){
 const color=({naver:'naver',kakao:'kakao',public:'web'})[t.kind]||'other';
 return `<span class="inbox-channel inbox-channel-${color}">${e(inboxChannel(t))}</span>`;
}
function inboxChannel(t){return t.source==='widget'?'홈페이지 위젯':t.source==='link'?'CS AI 상담 링크':channelNames[t.kind]||t.kind;}
async function applyInboxFilters(){if(inboxReplyDraftActive()&&!confirm('작성 중인 내용을 닫고 필터를 변경할까요?'))return;await leaveTemporary();inboxKind=val('inbox-kind');inboxSource=val('inbox-source');inboxQuery=val('inbox-q').trim();inboxUnread=!!$('#inbox-unread')?.checked;inboxPriority=val('inbox-priority');threadId=null;render()}
function sharedPreviewEnabled(){if(!me)return false;if(me.sample_tools){try{if(sessionStorage.getItem('csai-hide-samples:'+me.slug)==='1')return false;}catch{}return true;}return freeFeaturePreview();}
function previewInboxThread(id){return sharedPreviewEnabled()&&previewData().sampleThreads.find(t=>t.id===id);}async function inboxDetailFor(id){const example=previewInboxThread(id);return example?structuredClone(example):api('/api/inbox/'+enc(id));}async function loadInboxThreads(){
 let ts=await api('/api/inbox?agent='+enc(inboxAgent)+'&kind='+enc(['all','customer'].includes(inboxKind)?'':inboxKind)+'&q='+enc(inboxQuery));
 if(sharedPreviewEnabled()&&(!inboxAgent||inboxAgent==='all')){const examples=previewData().sampleThreads.filter(t=>(['all','customer'].includes(inboxKind)||inboxKind===t.kind)&&(!inboxQuery||(t.name+' '+t.messages.map(m=>m.body).join(' ')).toLowerCase().includes(inboxQuery.toLowerCase())));ts=ts.concat(examples.map(t=>({...t,manual:inboxDirect(t)}))).sort((a,b)=>(b.activity||b.created)-(a.activity||a.created));}if(inboxKind==='customer')ts=ts.filter(t=>t.kind!=='test');
 if(inboxSource==='manual')ts=ts.filter(t=>t.manual||t.paused_by);
 if(inboxSource==='widget'||inboxSource==='link')ts=ts.filter(t=>t.source===inboxSource);
 if(inboxUnread)ts=ts.filter(t=>t.unread>0);
 if(inboxPriority!=='all')ts=ts.filter(t=>!t.sample&&t.kind!=='test'&&(inboxPriority==='unassigned'?!t.assignment?.assignee:t.assignment?.priority===inboxPriority));
 return ts;
}
function replyCompletionEnabled(){try{return localStorage.getItem('csai-reply-completion:'+me?.slug)!=='off';}catch{return true;}}
function toggleReplyCompletion(control){try{localStorage.setItem('csai-reply-completion:'+me?.slug,control.checked?'on':'off');}catch{}document.querySelectorAll('.reply-completion-toggle').forEach(x=>{x.checked=control.checked;});document.querySelectorAll('.reply-with-history textarea').forEach(field=>{field.closest('.reply-with-history').dataset.completionEnabled=control.checked?'on':'off';if(!control.checked)clearReplySuggestion(field);else if(document.activeElement===field)updateReplySuggestion(field);});}
function replyWithHistory(id,title,messages,{maxLength=0}={}){
 const limit=maxLength||2000;
 const portableText=message=>message&&!message.photo&&!message.attachment?String(message.body||'').replace(/\r\n?/g,'\n').trim():'';
 const questionKey=message=>portableText(message).replace(/\s+/g,' ').toLowerCase();
 const latest=messages.at(-1);
 const question=latest?.role==='user'?questionKey(latest):'';
 let repeated='';
 const prior=[];
 for(let index=messages.length-1;index>=0;index--){
  const current=messages[index];
  if(current.role!=='assistant')continue;
  const answer=portableText(current);
  if(!answer||answer.length>limit)continue;
  if(prior.length<12&&!prior.includes(answer))prior.push(answer);
  const previous=messages[index-1];
  if(!repeated&&question&&previous?.role==='user'&&questionKey(previous)===question)repeated=answer;
  if(repeated&&prior.length>=12)break;
 }
 const field=maxLength?ta(id).replace('<textarea',`<textarea maxlength="${maxLength}"`):ta(id);
 const saved=inboxSnippets.map(x=>String(x.body||'').replace(/\r\n?/g,'\n').trim()).filter(x=>x&&x.length<=limit);
 const enabled=replyCompletionEnabled();
 const withEvents=field.replace('<textarea',`<textarea
  onfocus="updateReplySuggestion(this)" oninput="if(!event.isComposing)updateReplySuggestion(this)"
  onselect="updateReplySuggestion(this)" onkeydown="replySuggestionKey(event)"`);
 return `<div class="reply-with-history" data-completion-enabled="${enabled?'on':'off'}" data-reply-history="${e(JSON.stringify({repeated,prior,saved,limit}))}">
  ${label(title,withEvents)}
  <div class="reply-history-ghost" hidden>
   <p class="reply-history-source" id="${id}-suggestion">이 상담의 이전 AI 답변</p>
   <p class="reply-history-completion"></p>
   <div class="ui-actions ui-actions-keep-size">
    ${btn('초안에 넣기','acceptReplySuggestion(this.closest(\'.reply-with-history\').querySelector(\'textarea\'))','secondary ui-sm')}
    <span class="reply-history-keys"><kbd>Tab</kbd> 적용 <kbd>Esc</kbd> 닫기</span>
   </div>
  </div>
 </div>`;
}
function clearReplySuggestion(field){
 const panel=field.closest('.reply-with-history').querySelector('.reply-history-ghost');
 panel.hidden=true;
 const described=(field.getAttribute('aria-describedby')||'').split(/\s+/).filter(x=>x&&x!==field.id+'-suggestion');if(described.length)field.setAttribute('aria-describedby',described.join(' '));else field.removeAttribute('aria-describedby');
}
function updateReplySuggestion(field){
 const scope=field.closest('.reply-with-history');
 const panel=scope.querySelector('.reply-history-ghost');
 const draft=field.value;
 const history=JSON.parse(scope.dataset.replyHistory);
 const atEnd=field.selectionStart===draft.length&&field.selectionEnd===draft.length;
 const match=answer=>answer.length>draft.length&&answer.startsWith(draft)&&answer.length<=history.limit;
 const savedMatch=draft.trim().length>=2&&history.saved.find(match);
 const priorMatch=draft.trim().length>=2&&history.prior.find(match);
 const remaining=draft?(savedMatch||priorMatch)?.slice(draft.length):history.repeated;
 if(scope.dataset.completionEnabled==='off'||field.dataset.composing||!atEnd||scope.dataset.dismissed===draft||!remaining){clearReplySuggestion(field);return '';}
 panel.querySelector('.reply-history-source').textContent=savedMatch?'저장된 답변 추천':'이 상담의 이전 AI 답변';
 panel.querySelector('.reply-history-completion').textContent=remaining;
 panel.hidden=false;
 const described=new Set((field.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean));described.add(field.id+'-suggestion');field.setAttribute('aria-describedby',[...described].join(' '));
 return remaining;
}
function acceptReplySuggestion(field){
 const remaining=updateReplySuggestion(field);
 if(!remaining)return;
 field.setRangeText(remaining,field.value.length,field.value.length,'end');
 field.closest('.reply-with-history').dataset.dismissed=field.value;
 clearReplySuggestion(field);
 field.focus();
 field.dispatchEvent(new Event('input',{bubbles:true}));
 toast('추천 답변을 초안에 넣었습니다.');
}
document.addEventListener('compositionstart',event=>{
 const field=event.target;
 if(!field.matches('.reply-with-history textarea'))return;
 field.dataset.composing='1';
 clearReplySuggestion(field);
});
document.addEventListener('compositionend',event=>{
 const field=event.target;
 if(!field.matches('.reply-with-history textarea'))return;
 delete field.dataset.composing;
 updateReplySuggestion(field);
});
function replySuggestionKey(event){
 if(event.isComposing||event.keyCode===229)return;
 const field=event.target;
 if(event.key==='Escape'&&updateReplySuggestion(field)){
  event.preventDefault();
  field.closest('.reply-with-history').dataset.dismissed=field.value;
  clearReplySuggestion(field);
 }else if(event.key==='Tab'&&!event.shiftKey&&!event.ctrlKey&&!event.altKey&&!event.metaKey&&updateReplySuggestion(field)){
  event.preventDefault();
  acceptReplySuggestion(field);
 }
}

const sampleManualThreads=new Set(),sampleTemporaryThreads=new Map();
const sampleModeKey=id=>(me?.slug||'guest')+':'+id;
let activeTemporary=null,temporaryRenewAt=0;
function inboxTemporary(t){if(t.sample){const lease=sampleTemporaryThreads.get(sampleModeKey(t.id));if(lease&&lease.expires<=Date.now()/1000){sampleTemporaryThreads.delete(sampleModeKey(t.id));sampleManualThreads.delete(sampleModeKey(t.id));return null;}return lease||null;}return t.temporary||null;}
function temporaryClock(expires){const left=Math.max(0,Math.ceil(expires-Date.now()/1000));return String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0');}
function rememberTemporary(t){const lease=t&&inboxTemporary(t);activeTemporary=lease?{...lease,id:t.id,sample:!!t.sample}:null;}
async function leaveTemporary(){const lease=activeTemporary;activeTemporary=null;if(!lease)return;if(lease.sample){sampleTemporaryThreads.delete(sampleModeKey(lease.id));sampleManualThreads.delete(sampleModeKey(lease.id));return;}try{await api('/api/inbox/'+enc(lease.id),{release_temporary:lease.lease});}catch(x){toast('자동 복귀 요청 실패 · 설정 시간이 지나면 복귀합니다.');}}
window.addEventListener('pagehide',()=>{const lease=activeTemporary;if(lease&&!lease.sample&&!inboxReplyDraftActive()){fetch('/api/inbox/'+enc(lease.id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({release_temporary:lease.lease}),keepalive:true}).catch(()=>{});}});
function refreshTemporaryClock(){document.querySelectorAll('[data-temporary-expires]').forEach(el=>{el.textContent=temporaryClock(Number(el.dataset.temporaryExpires));});}
setInterval(refreshTemporaryClock,1000);
let inboxDetailSignature='',inboxModeSignature='';
const inboxDesk=()=>new URLSearchParams(location.search).get('desk')==='1';
const inboxCenter=()=>route==='consultation-center';
const inboxWorkspace=()=>route==='inbox'||inboxCenter();
const inboxDirect=t=>{if(t.sample)inboxTemporary(t);return t.sample?sampleManualThreads.has(sampleModeKey(t.id)):!!t.manual;};
const inboxCanReply=t=>['public','test'].includes(t.kind)||(['naver','telegram'].includes(t.kind)&&(t.sample||t.channel_reply?.available));
const inboxModeKey=t=>JSON.stringify([t.id,inboxDirect(t),inboxTemporary(t)?.lease||'',t.paused_by||'',t.status,inboxCanReply(t)]);
function sampleDisplayText(value,isSample){return isSample?String(value??'').replace(/^샘플\s*·\s*/,''):value;}
function sampleRecord(x){return !!(x?.sample||x?.preview||String(x?.id||'').startsWith('preview-'));}
function sampleTitle(value,isSample){return isSample?'샘플 · '+sampleDisplayText(value,true):value;}
function inboxMessageMarkup(t){return t.messages.map(m=>`<div class="inbox-message ${m.role==='user'?'from-customer':'from-staff'}${t.sample?' sample-chat-message':''}"><small>${e(m.role==='user'?'고객':m.role==='staff'?'담당자':'AI 상담사')} · ${e(new Date(m.created*1000).toLocaleString('ko-KR'))}</small>${m.photo||m.attachment?photoBubble(m,'owner',t.id):bubble(m.role==='user'?'assistant':'user',sampleDisplayText(m.body,t.sample),false)}${!m.photo&&!m.attachment&&String(m.body||'').trim()?`<details class="inbox-message-menu"><summary aria-label="메시지 메뉴">···</summary>${btn('복사','copyInboxMessage(this)','tertiary ui-sm')}${!t.sample&&m.role==='assistant'?btn('참고 교육 정보',`showAnswerContext('${m.id}')`):''}</details>`:''}</div>`).join('')}
function copyInboxMessage(b){const value=b.closest('.inbox-message')?.querySelector('[data-chat-copy-text]')?.textContent||'';if(value)navigator.clipboard.writeText(value).then(()=>toast('복사했습니다.')).catch(()=>toast('복사하지 못했습니다.'))}
function inboxModeBar(t){
 const supported=['public','test'].includes(t.kind)||t.sample;
 const direct=inboxDirect(t),temporary=inboxTemporary(t);
 if(!inboxCanReply(t))return '<div class="inbox-mode-bar"><span>외부 채널에서 직접 응대</span>'+(t.sample?'':btn(t.manual?'이 상담 AI 재개':'이 상담 AI 일시 중지',`switchInboxMode(${!t.manual})`))+'</div>';
 const status=t.paused_by?'상위 수동 설정 적용 중':temporary?'일시 개입 중':direct?'수동 상담 유지':'AI 자동 상담 중';
 const controls=temporary?btn('수동 유지','switchInboxMode(true,null)')+btn('AI 복귀','switchInboxMode(false)'):direct?btn('AI 상담 재개','switchInboxMode(false)'):supported?btn('직접 개입','switchInboxMode(true,300)','primary')+btn('수동 유지','switchInboxMode(true,null)'):btn('직접 상담 개입','switchInboxMode(true)','primary');
 const options=temporary?'<label class="takeover-settings"><span>자동 복귀</span><select aria-label="자동 복귀 시간" onchange="switchInboxMode(true,Number(this.value))">'+[[0,'전송 직후'],[60,'1분'],[180,'3분'],[300,'5분'],[600,'10분'],[1800,'30분'],[3600,'60분']].map(([v,k])=>'<option value="'+v+'" '+(v===temporary.seconds?'selected':'')+'>'+k+'</option>').join('')+'</select></label>':'';
 return '<div class="inbox-mode-bar takeover-bar"><div class="takeover-status"><span class="takeover-dot '+(direct||t.paused_by?'is-manual':'')+'"></span><span>'+e(status)+'</span>'+(temporary?'<span class="takeover-clock" data-temporary-expires="'+temporary.expires+'">'+temporaryClock(temporary.expires)+'</span>':'')+'</div><div class="takeover-actions">'+controls+'</div>'+options+(temporary&&t.paused_by?'<small class="takeover-note">복귀 후에도 상위 수동 설정이 유지됩니다.</small>':'')+'</div>';
}
async function switchInboxMode(manual,seconds=null){
 const id=threadId;if(!id)return;
 if(!manual&&inboxReplyDraftActive()&&!confirm('작성 중인 답변을 닫고 AI로 복귀할까요?'))return;
 if(manual&&seconds===null&&!confirm('AI가 자동으로 복귀하지 않는 수동 상담으로 전환할까요?'))return;
 await act(async()=>{const t=await inboxDetailFor(id);if(threadId!==id)return;
 if(t.sample){if(manual){sampleManualThreads.add(sampleModeKey(id));if(seconds!==null)sampleTemporaryThreads.set(sampleModeKey(id),{lease:crypto.randomUUID(),seconds,expires:Date.now()/1000+(seconds||300)});else sampleTemporaryThreads.delete(sampleModeKey(id));}else{sampleManualThreads.delete(sampleModeKey(id));sampleTemporaryThreads.delete(sampleModeKey(id));}}
 else{await api('/api/inbox/'+enc(id),manual&&seconds!==null?{manual:true,auto_resume_seconds:seconds}:{manual});}
 if(threadId===id){await render();}
 });
}
function resizeOwnerComposer(field){field.style.height='auto';field.style.height=Math.min(120,Math.max(42,field.scrollHeight))+'px';}
function inboxComposer(t){const id=['public','test'].includes(t.kind)||t.sample?'staff-reply':'external-reply';const send=t.sample?"sendSampleInboxMessage('staff')":id==='staff-reply'?"sendOwnerInboxReply()":"sendExternalReply()";return `<div class="owner-compose"><div class="owner-compose-input">${replyWithHistory(id,'메시지 입력',t.messages,{maxLength:id==='external-reply'?1000:2000}).replace('<textarea','<textarea rows="1" placeholder="메시지 입력"').replace('oninput="if(!event.isComposing)updateReplySuggestion(this)"','oninput="resizeOwnerComposer(this);if(!event.isComposing)updateReplySuggestion(this)"')}</div><button type="button" class="primary owner-send" aria-label="전송" onclick="${send}">${workspaceControlIcon('send')}</button></div>`}
async function sendOwnerInboxReply(){const id=threadId,reply=val('staff-reply').trim();if(!reply)return toast('메시지를 입력하세요.');if(ownerReplyBusy)return;ownerReplyBusy=true;try{await act(async()=>{const t=await api('/api/inbox/'+enc(id));if(threadId!==id||!t.manual)return toast('직접 상담 모드를 확인하세요.');await api('/api/inbox/'+enc(id),{reply,expected_lease:t.temporary?.lease||''});if(threadId===id)await render()})}finally{ownerReplyBusy=false}}
let ownerReplyBusy=false;
function inboxReplyDraftActive(){return ['staff-reply','external-reply','sample-customer-reply'].some(id=>$('#'+id)?.value)||['inbox-note','inbox-tags','inbox-assignee','inbox-due-date'].some(id=>{const x=$('#'+id);return x&&x.value!==x.defaultValue})||!!$('.modal')}
let deskInstallPrompt=null;
window.addEventListener('beforeinstallprompt',ev=>{if(!publicMode){ev.preventDefault();deskInstallPrompt=ev}});
async function installInboxDesk(){if('serviceWorker'in navigator){try{await navigator.serviceWorker.register('/push-sw.js')}catch{}}if(deskInstallPrompt){await deskInstallPrompt.prompt();deskInstallPrompt=null;return;}modal('상담센터 바로가기 설치','<p>Chrome 또는 Edge 메뉴에서 앱 설치 또는 홈 화면에 추가를 선택하세요. iPhone은 Safari 공유 메뉴의 홈 화면에 추가를 이용하세요.</p><p>설치가 지원되지 않으면 상담센터 URL을 즐겨찾기 하세요.</p>')}
function openInboxWindow(event,link){if(matchMedia('(max-width:700px)').matches)return;const win=window.open('about:blank','_blank','popup,width=1100,height=760');if(win){event.preventDefault();win.opener=null;win.location.replace(link.href)}}
function deskLinks(){return '<div class="inbox-desk-links"><a class="ui-button primary" href="/#consultation-center">상담센터 바로 열기</a><a class="ui-button secondary" href="/?desk=1#consultation-center" target="_blank" rel="noopener" onclick="openInboxWindow(event,this)">독립 창으로 열기</a>'+btn('바로가기 설치','installInboxDesk()')+'</div>'}
function inboxDeskShell(body){return `<div class="inbox-desk-shell" data-route="consultation-center"><header class="inbox-desk-header"><strong>CS AI 상담센터</strong><span>${e(me.settings.brand)}</span><a href="/#dashboard">관리자 대시보드</a>${btn('알림 설정',"location.href='/#alerts'")}${btn('로그아웃','logout()')}</header><main>${body}</main>${mobileQuickNav()}</div>`}

function sampleInboxReply(detail){if(!inboxCanReply(detail))return externalReplyControls(detail);return inboxDirect(detail)?inboxComposer(detail)+actionGroup({keepSize:true},inboxSnippets.length?btn('저장 답변 불러오기','chooseInboxSnippet()'):''):'';}
let sampleInboxSending=false;
async function sendSampleInboxMessage(role){
 if(sampleInboxSending)return;
 if(role==='staff'&&!sampleManualThreads.has(sampleModeKey(threadId)))return toast('직접 상담 모드로 전환하세요.');
 const id=threadId,field=role==='staff'?'staff-reply':'sample-customer-reply',value=val(field).trim();
 if(!value)return toast('메시지를 입력하세요.');
 sampleInboxSending=true;
 try{const example=previewInboxThread(id);if(example){const stamp=Math.floor(Date.now()/1000);example.messages.push({id:crypto.randomUUID(),role,body:value,created:stamp});example.activity=stamp;example.last=value;example.unread=role==='staff'?0:example.unread+1;if(role==='user'&&!sampleManualThreads.has(sampleModeKey(id))){const answer='샘플 AI 답변 · 문의 내용을 접수했습니다. 업체에 등록된 정보에 따라 안내합니다.';example.messages.push({id:crypto.randomUUID(),role:'assistant',body:answer,created:stamp});example.last=answer;}}else await api('/api/demo/samples/'+enc(id)+'/message',{role,message:value});if(role==='staff'){const lease=sampleTemporaryThreads.get(sampleModeKey(id));if(lease){if(lease.seconds===0){sampleTemporaryThreads.delete(sampleModeKey(id));sampleManualThreads.delete(sampleModeKey(id));}else lease.expires=Date.now()/1000+lease.seconds;}}if(inboxWorkspace()&&threadId===id){await render();const chat=$('.inbox-conversation');if(chat)chat.scrollTop=chat.scrollHeight;}}catch(err){toast(err.message);}finally{sampleInboxSending=false;}
}

function centerActivityLabel(stamp,now=Date.now()){
 const d=new Date(Number(stamp)*1000);
 if(!Number.isFinite(d.getTime())||Number(stamp)<=0)return '';
 const minutes=Math.max(0,Math.floor((now-d.getTime())/60000));
 if(minutes===0)return '방금 전';
 if(minutes<=60)return minutes+'분 전';
 return d.toDateString()===new Date(now).toDateString()?d.toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'}):d.toLocaleDateString('ko-KR',{month:'numeric',day:'numeric'});
}
function centerIsRecent(stamp,now=Date.now()){const age=now-Number(stamp)*1000;return Number(stamp)>0&&age>=0&&age<61*60000;}
function refreshCenterAges(list){list.querySelectorAll('[data-center-activity]').forEach(node=>{const stamp=Number(node.dataset.centerActivity);const label=centerActivityLabel(stamp);if(node.textContent!==label)node.textContent=label;const badge=node.parentElement.querySelector('.center-new');if(badge)badge.hidden=!centerIsRecent(stamp);});}
function consultationTitle(t){return t.preview?sampleTitle(t.name,true):t.sample?'샘플 · 고객 '+String(t.id).slice(-6).toUpperCase():t.kind==='test'?'관리자 테스트':t.consultation?.title||'고객 '+String(t.id).slice(-6).toUpperCase();}
function consultationCustomer(t){return t.consultation?.customer_name?' · '+t.consultation.customer_name:'';}
function renderCenterList(ts){
 return ts.map(t=>{const title=consultationTitle(t),mode=t.paused_by?'상위 수동':inboxTemporary(t)?'일시 개입':inboxDirect(t)?'수동 유지':t.status==='resolved'?'완료':t.status==='pending'?'확인 필요':'AI 상담';
 const stamp=Number(t.activity||t.created)||0,time=centerActivityLabel(stamp);
 return `<button type="button" class="inbox-entry center-entry ${threadId===t.id?'selected':''}${t.sample?' sample-record':''}" onclick="openInboxThread('${e(t.id)}')" aria-pressed="${threadId===t.id}"><span class="center-avatar">${uiIcon('user-round')}</span><span class="center-entry-body"><span class="center-entry-title"><strong>${e(title)}</strong>${t.unread?`<span class="center-new" ${centerIsRecent(stamp)?'':'hidden'}>NEW</span>`:''}<time data-center-activity="${stamp}">${e(time)}</time></span><span class="center-entry-meta">${e(inboxChannel(t))} · ${e(mode+consultationCustomer(t))}</span><span class="inbox-excerpt">${e(t.consultation?.summary||sampleDisplayText(t.last||'새 상담',t.sample))}</span></span>${t.unread?'<span class="center-unread">'+e(t.unread)+'</span>':''}</button>`}).join('')||emptyState('조건에 맞는 상담이 없습니다.');
}
async function centerBack(){if(inboxReplyDraftActive()&&!confirm('작성 중인 내용을 닫고 목록으로 이동할까요?'))return;await leaveTemporary();threadId=null;render()}
async function centerTab(kind){if(inboxReplyDraftActive()&&!confirm('작성 중인 내용을 닫고 목록을 변경할까요?'))return;await leaveTemporary();inboxUnread=kind==='unread';inboxSource=kind==='manual'?'manual':'all';threadId=null;render()}
function centerExtras(t,assignment,annotation){
 const last=t.messages.filter(m=>m.role==='user').at(-1);
 if(t.sample)return (me.sample_tools||t.preview)?accordion('샘플 고객 메시지 체험',label('고객이 보낼 메시지',ta('sample-customer-reply'))+btn('고객 메시지 보내기',"sendSampleInboxMessage('user')")):'';
 return actionGroup({keepSize:true},btn('완료 처리',"updateThread({status:'resolved'})"),t.manual?btn('완료 후 AI 복귀','closeAndResumeAI()'):'',last&&t.kind!=='test'?btn('읽음 처리',`markInboxRead('${t.id}','${last.id}')`):'',t.kind==='test'?btn('테스트 기록 삭제','deleteTestThread()'):'',['naver','kakao','telegram','line','instagram'].includes(t.kind)?btn('이전 상담','showRelatedThreads()'):'',t.messages.some(m=>m.role==='assistant')?btn('최근 AI 답변 오류 표시','reportOwnerAnswer()'):'',t.messages.length?btn('상담 핵심 보기','showInboxBrief()'):'',t.consultation?.booking?btn('관련 예약 일정',`jumpLinkedBooking('${e(t.consultation.booking.start)}','${e(t.consultation.booking.agent||'')}')`):'',t.messages.some(m=>m.role==='staff')&&t.kind!=='test'?btn('직접 상담 기록으로 교육','staffTrainingPreview()'):'',t.kind!=='test'&&['crm','quote','tasks','leads','complaints'].some(has)?btn('업무로 등록','convertModal()'):'',t.kind==='public'?btn('주문 조회 승인','ownerOrderAccess()'):'',t.web_calls&&t.kind==='public'?btn('통화 요청 확인',"checkWebCall('owner')"):'')+(assignment?inboxAssignmentHtml(assignment):'')+(annotation?inboxAnnotationHtml(annotation):'')+(!['public','test'].includes(t.kind)?externalReplyControls(t,false):'');
}
function centerAttachments(t){
 const items=actionGroup({keepSize:true},t.photos&&t.kind==='public'&&!t.sample?btn('사진 첨부',"photoUploadModal('owner')"):'',t.files&&t.kind==='public'&&!t.sample?btn('영상·파일 첨부',"photoUploadModal('owner','file')"):'',inboxSnippets.length?btn('저장 답변','chooseInboxSnippet()'):'',!t.sample&&t.messages.some(m=>m.role==='user')?btn('AI 답장 추천','openInboxDraftAssistant()'):'');
 return items?'<details class="center-attachments"><summary aria-label="첨부 및 답변 도구">+</summary><div>'+items+'</div></details>':'';
}
function centerComposer(t){
 if(!inboxCanReply(t))return t.kind==='kakao'?'<a class="center-external" href="https://center-pf.kakao.com/" target="_blank" rel="noopener noreferrer">카카오에서 직접 상담하기</a>':'<p class="center-external">외부 채널 관리자에서 직접 응대하세요.</p>';
 if(!inboxDirect(t))return '';
 return '<div class="center-compose-row">'+centerAttachments(t)+inboxComposer(t)+'</div>';
}
function centerWorkspace({detail,brands,filter,list,modes,assignment,annotation,sampleTools,scope}){
 const active=detail?'<div class="center-chat-head'+(detail.sample?' sample-chat-surface':'')+'"><button type="button" class="center-back" aria-label="상담 목록으로" onclick="centerBack()">←</button><div class="center-avatar">'+uiIcon('user-round')+'</div><div class="center-identity"><strong>'+e(consultationTitle(detail))+'</strong><small>'+e(inboxChannel(detail))+' · '+e((states[detail.status]||detail.status)+consultationCustomer(detail))+'</small></div><details class="center-chat-tools"><summary aria-label="상담 상세 메뉴">···</summary><div class="center-popover">'+centerExtras(detail,assignment,annotation)+'</div></details></div><div class="inbox-conversation center-messages'+(detail.sample?' sample-chat-surface':'')+'" role="log" aria-live="polite">'+inboxMessageMarkup(detail)+'</div><div class="center-chat-bottom"><div class="inbox-live-mode">'+inboxModeBar(detail)+'</div>'+centerComposer(detail)+'</div>':'<div class="center-empty"><strong>상담을 선택하세요.</strong><p>AI 상담을 관찰하거나 직접 고객에게 답변할 수 있습니다.</p></div>';
 return `<section class="center-workspace ${detail?'has-selected-thread':''}"><section class="center-list-pane"><div class="center-list-head"><div><h1>상담센터</h1><span id="inbox-live-status" role="status">자동 갱신 · 3초 간격</span></div>${inboxDesk()?'':'<a class="center-open-window" href="/?desk=1#consultation-center" target="_blank" rel="noopener" onclick="openInboxWindow(event,this)" title="상담센터 독립 창 열기" aria-label="상담센터 독립 창 열기">'+workspaceControlIcon('external')+'</a>'}<details class="center-global-tools"><summary aria-label="상담센터 메뉴">···</summary><div class="center-popover"><a class="ui-button secondary" href="/#inbox">통합 상담함</a><a class="ui-button secondary" href="/?desk=1#consultation-center" target="_blank" rel="noopener" onclick="openInboxWindow(event,this)">독립 창 열기</a>${btn('바로가기 설치','installInboxDesk()')}${btn('자주 쓰는 답변','manageInboxSnippets()')}${btn('채널별 통계','showChannelMetrics()')}${btn('외부 발송 문제','showDeliveryIssues()')}${btn('새로고침','refreshInboxNow()')}${btn('알림 설정',"location.href='/#alerts'")}${sampleTools}${consultationControls(modes,brands)}${scope}</div></details></div><div class="center-list-tabs"><button type="button" class="${!inboxUnread&&inboxSource!=='manual'?'active':''}" onclick="centerTab('all')">전체</button><button type="button" class="${inboxUnread?'active':''}" onclick="centerTab('unread')">안 읽음</button><button type="button" class="${inboxSource==='manual'?'active':''}" onclick="centerTab('manual')">직접 상담</button></div><details class="center-filters"><summary>검색 및 필터</summary>${brandSelect('inbox-brand',brands,inboxAgent,'inboxAgent=this.value;threadId=null;render()',true)}${filter}${checkbox('inbox-unread','안 읽은 문의만',{checked:inboxUnread,form:'inbox-filter'})}</details><div id="inbox-live-list" class="inbox-list center-list">${list}</div></section><section class="inbox-detail-card center-chat-pane">${active}</section></section>`;
}

async function inbox(){
 let brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available):[];let policy=await api('/api/history-policy'),ts=await loadInboxThreads();
 let detail=threadId?await inboxDetailFor(threadId):null;const modes=await api('/api/consultation-mode');
 inboxSnippets=await api('/api/inbox-snippets');let annotation=detail&&!detail.sample&&detail.kind!=='test'?await api('/api/inbox/'+threadId+'/annotation'):null;let assignment=annotation?await api('/api/inbox/'+threadId+'/assignment'):null;
 const channels=[['customer','고객 상담'],['all','전체 기록'],['public','CS AI 상담 링크'],['naver','네이버 톡톡'],['kakao','카카오 AI 챗봇'],['telegram','텔레그램'],['line','LINE'],['instagram','인스타그램 DM'],['test','관리자 테스트']];
 const sources=[['all','모든 유입·모드'],['manual','직접 상담만'],['link','직접 링크 유입'],['widget','위젯 유입']];
 const priorities=[['all','전체 우선순위'],['unassigned','미배정'],['urgent','긴급'],['high','높음'],['normal','보통'],['low','낮음']];
 const filter=`<form id="inbox-filter" class="ui-filterbar inbox-filter" aria-label="상담 검색 필터" onsubmit="event.preventDefault();applyInboxFilters()">
  <div class="inbox-filter-selects">
   ${select('inbox-kind',channels,inboxKind).replace('<select','<select aria-label="채널 선택"')}
   ${select('inbox-source',sources,inboxSource).replace('<select','<select aria-label="상담 유입 및 모드"')}
   ${select('inbox-priority',priorities,inboxPriority).replace('<select','<select aria-label="우선순위"')}
  </div>
  <div class="inbox-filter-search">
   <input id="inbox-q" type="search" aria-label="상담 내용 검색" value="${e(inboxQuery)}" placeholder="문의나 답변 검색">
   <button class="ui-button primary" type="submit">찾기</button>
  </div>
 </form>`;
 rememberTemporary(detail);inboxBrands=brands;inboxSnapshot=JSON.stringify(ts);inboxDetailSignature=detail?JSON.stringify(detail.messages):'';inboxModeSignature=detail?inboxModeKey(detail):'';let list=renderInboxList(ts,brands);
 let detailBody=detail?`<p class="muted">${inboxChannelBadge(detail)} · ${e(states[detail.status]||detail.status)} · 메시지 ${detail.messages.length}개</p><div class="inbox-conversation${detail.sample?' sample-chat-surface':''}" role="log" aria-live="polite">${inboxMessageMarkup(detail)}</div><div class="inbox-live-mode">${inboxModeBar(detail)}</div>${detail.sample?sampleInboxReply(detail):`<div class="row" style="margin-top:15px">${detail.paused_by?'<span class="muted">'+e(pauseLabel(detail.paused_by))+' · 상위 설정 해제 전 AI 재개 불가</span>':''}${btn('완료 처리',"updateThread({status:'resolved'})")}${detail.manual?btn('완료 후 AI 복귀','closeAndResumeAI()'):''}${['naver','kakao','telegram','line','instagram'].includes(detail.kind)?btn('동일 고객 이전 상담','showRelatedThreads()'):''}${detail.messages.some(m=>m.role==='assistant')?btn('최근 AI 답변 오류 표시','reportOwnerAnswer()'):''}${detail.kind==='test'?btn('테스트 기록 삭제','deleteTestThread()'):''}</div>${detail.kind!=='test'&&detail.messages.some(m=>m.role==='user')?btn('읽음 처리',`markInboxRead('${detail.id}','${detail.messages.filter(m=>m.role==='user').at(-1).id}')`):''}${assignment?inboxAssignmentHtml(assignment):''}${annotation?inboxAnnotationHtml(annotation):''}${['public','test'].includes(detail.kind)?(inboxDirect(detail)?inboxComposer(detail):''):externalReplyControls(detail,false)+(inboxCanReply(detail)&&inboxDirect(detail)?inboxComposer(detail):'')}${actionGroup({keepSize:true},inboxDirect(detail)&&detail.photos&&detail.kind==='public'?btn('사진 첨부',"photoUploadModal('owner')"):'',inboxDirect(detail)&&detail.files&&detail.kind==='public'?btn('영상·파일 첨부',"photoUploadModal('owner','file')"):'',detail.web_calls&&detail.kind==='public'?btn('통화 요청 확인',"checkWebCall('owner')"):'',detail.kind==='public'?btn('주문 조회 승인','ownerOrderAccess()'):'',inboxDirect(detail)&&inboxCanReply(detail)&&inboxSnippets.length?btn('저장 답변 불러오기','chooseInboxSnippet()'):'',inboxDirect(detail)&&inboxCanReply(detail)&&detail.messages.some(m=>m.role==='user')?btn('AI 답장 3가지 추천','openInboxDraftAssistant()'):'',detail.messages.length?btn('상담 핵심 보기','showInboxBrief()'):'',detail.kind!=='test'&&detail.messages.some(m=>m.role==='staff')?btn('직접 상담 기록으로 교육','staffTrainingPreview()'):'',detail.kind!=='test'&&['crm','quote','tasks','leads','complaints'].some(has)?btn('업무로 등록','convertModal()'):'')}`}`:emptyState('상담 기록에서 대화를 선택하면 메시지와 답변 도구가 여기에 표시됩니다.');
 let sampleTools=me.sample_tools?`<div class="inbox-sample-tools"><span>화면 검토용 샘플 · 상담·예약·업무·알림 연결 · 실제 사용량 차감 없음</span><div>${actionGroup({keepSize:true},btn('연결 샘플 9건 넣기','addDemoSamples()'),btn('샘플만 지우기','removeDemoSamples()','danger ui-sm'))}</div></div>`:'';
 let scope=`<p class="inbox-scope">현재 조회 가능 범위: 최근 ${policy.accessible_days.toLocaleString()}일${policy.older_threads?` · 조회 범위 밖 ${policy.older_threads.toLocaleString()}건`:''}${!has('retention')&&!cfg.demo?` <button type="button" onclick="go('addons')">장기 보관 옵션 보기</button>`:''}</p>`;
 if(inboxCenter())return centerWorkspace({detail,brands,filter,list,modes,assignment,annotation,sampleTools,scope});
 return pageTop('통합 상담함','고객 상담을 실시간으로 관찰하고 직접 응대하세요.')+(inboxDesk()?'':deskLinks())+`<section class="card app-card inbox-toolbar">${brandSelect('inbox-brand',brands,inboxAgent,'inboxAgent=this.value;threadId=null;render()',true)}${filter}<div class="inbox-toolbar-controls">${checkbox('inbox-unread','안 읽은 문의만',{checked:inboxUnread,form:'inbox-filter',className:'inbox-unread'})}<div class="ui-actions inbox-toolbar-actions"><div class="inbox-tool-row">${btn('자주 쓰는 답변','manageInboxSnippets()','secondary ui-sm')}<label class="ui-check inbox-completion-control" title="저장 문구 및 이전 AI 답변을 추천합니다. 사용량 차감 없음"><input type="checkbox" class="ui-choice reply-completion-toggle" ${replyCompletionEnabled()?'checked':''} onchange="toggleReplyCompletion(this)"><span>답변 자동완성</span></label></div><div class="inbox-tool-row inbox-tool-links">${btn('외부 발송 문제','showDeliveryIssues()','tertiary ui-sm')}${btn('채널별 상담 통계','showChannelMetrics()','tertiary ui-sm')}</div></div></div><div class="inbox-toolbar-status"><span id="inbox-live-status">상담 자동 갱신 · 3초 간격</span>${scope}</div>${sampleTools}${consultationControls(modes,brands)}</section>`+`<div class="grid inbox-grid ${detail?'has-selected-thread':''}"><section class="card app-card inbox-record-card"><div class="inbox-record-heading"><h2>상담 기록</h2><button type="button" class="ui-button secondary ui-sm inbox-refresh-icon" onclick="refreshInboxNow()" aria-label="상담 기록 새로고침" title="상담 기록 새로고침"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 6.6M20 4v7h-7"/></svg></button></div>
  <p class="inbox-pull-hint ui-helper">목록 맨 위에서 아래로 당겨 새로고침</p>
  <div class="inbox-pull">
   <div class="inbox-pull-indicator" aria-hidden="true"><span class="inbox-pull-mark"><span class="inbox-pull-drop"></span>${uiIcon('chevron-down')}</span><span data-pull-label></span></div>
   <div class="inbox-pull-announcement" role="status"></div>
   <div id="inbox-live-list" class="inbox-list">${list}</div>
  </div></section><section class="card app-card inbox-detail-card">${btn('상담 목록으로','centerBack()','tertiary inbox-back')}${detailBody}${detail?.sample&&(me.sample_tools||detail.preview)?accordion('샘플 고객 메시지 체험',label('고객이 보낼 메시지',ta('sample-customer-reply'))+btn('고객 메시지 보내기',"sendSampleInboxMessage('user')",'secondary')):''}</section></div>`
}
async function addDemoSamples(){await act(async()=>{let r=await api('/api/demo/samples',{});try{sessionStorage.removeItem('csai-hide-samples:'+me.slug)}catch{}let ts=await api('/api/inbox');threadId=ts.find(t=>t.sample)?.id||null;inboxKind='all';inboxQuery='';toast(r.created?'상담·일정·업무·알림 샘플을 넣었습니다.':'샘플이 이미 있습니다.');render()})}
async function removeDemoSamples(){if(!confirm('이 데모 계정의 샘플 상담만 지울까요?'))return;await act(async()=>{let r=await api('/api/demo/samples',undefined,'DELETE');try{sessionStorage.setItem('csai-hide-samples:'+me.slug,'1')}catch{}threadId=null;toast('샘플 상담 '+r.removed+'건을 지웠습니다.');render()})}
async function staffTrainingPreview(){await act(async()=>{const r=await api('/api/inbox/'+threadId+'/education-source');staffSourceAgent=r.agent||'';modal('직접 상담 기록으로 교육',`<p>담당자가 직접 답변한 ${r.pairs}개 질문·답변을 가져왔습니다. 고객 발화는 질문으로만 사용합니다.</p><p class="muted">전화번호·이메일 등 일부 정보는 자동 제거되지만, 이름·주소·기밀은 직접 확인하고 삭제해 주세요.</p>${label('교육할 자료 검토',ta('staff-education-source',r.text))}<label><input type="checkbox" id="staff-education-consent"> 교육에 사용할 권한이 있으며 개인정보·기밀 정보를 확인했습니다.</label>${btn('교육 화면으로 가져오기','loadStaffTraining()','primary')}`);})}
let staffSourceAgent='';
function loadStaffTraining(){if(educationBusy){toast('진행 중인 교육을 먼저 완료해 주세요.');return;}if(!checked('staff-education-consent')){toast('자료 이용 동의가 필요합니다.');return;}const text=val('staff-education-source').trim();if(!text||text.length>30000){toast('교육 자료는 30,000자 이하로 입력하세요.');return;}if(educationAgent!==staffSourceAgent){educationDraft=null;$('#education-workspace')?.remove();}educationDraft=educationDraft||{values:{},dates:[],files:[],upload:[],memory:[],open:[]};educationDraft.values['training-conversation']=text;educationDraft.values['training-text']='담당자의 실제 답변을 기준으로 사업 정보와 상담 방식을 교육해 주세요.';educationDraft.open[0]=true;educationMethod='direct';estimate=null;trainingChat=[];educationAgent=staffSourceAgent;$('.modal')?.remove();go('education');}
async function updateThread(body){await act(async()=>{await api('/api/inbox/'+threadId,body);render()})}
async function dustDelete(node){
 if(!node?.isConnected||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 const box=node.getBoundingClientRect();
 if(!box.width||!box.height||box.bottom<0||box.top>innerHeight)return;
 const layer=document.createElement('div'),visibility=node.style.visibility;
 layer.className='dust-layer';
 layer.inert=true;
 layer.setAttribute('aria-hidden','true');
 Object.assign(layer.style,{left:box.left+'px',top:box.top+'px',width:box.width+'px',height:box.height+'px'});
 const columns=10,rows=4;
 for(let y=0;y<rows;y++)for(let x=0;x<columns;x++){
  const tile=node.cloneNode(true);
  tile.removeAttribute('id');
  tile.querySelectorAll('[id]').forEach(child=>child.removeAttribute('id'));
  tile.classList.add('dust-tile');
  Object.assign(tile.style,{
   width:box.width+'px',height:box.height+'px',margin:'0',
   clipPath:`inset(${y*100/rows}% ${(columns-x-1)*100/columns}% ${(rows-y-1)*100/rows}% ${x*100/columns}%)`,
   animationDelay:`${(columns-1-x)*7}ms`,
  });
  tile.style.setProperty('--dx',-(18+Math.random()*48)+'px');
  tile.style.setProperty('--dy',(Math.random()-.5)*48+'px');
  layer.append(tile);
 }
 document.body.append(layer);
 node.style.visibility='hidden';
 await new Promise(resolve=>setTimeout(resolve,450));
 layer.remove();
 node.style.visibility=visibility;
}
async function deleteVisibleRow(path,button,onDeleted=render){
 const row=button?.closest('.line');
 await act(async()=>{
  await api(path,undefined,'DELETE');
  await dustDelete(row);
  await onDeleted();
 });
}
async function deleteTestThread(){
 const id=threadId,row=$('.inbox-entry.selected');
 if(!confirm('이 테스트 대화와 메시지를 삭제할까요? 사용한 상담 횟수는 복구되지 않습니다.'))return;
 await act(async()=>{
  await api('/api/inbox/'+id,undefined,'DELETE');
  await dustDelete(row);
  if(threadId===id){threadId=null;chatSession=null;chatMessages=[];}
  toast('테스트 상담 기록을 삭제했습니다.');
  await render();
 });
}
async function alerts(){let u=await api('/api/unknown');if(sharedPreviewEnabled())u=u.concat(previewData().questions);return pageTop('알림 및 미학습 질문','미학습 질문과 업무 알림을 확인하고 수신 방법을 관리하세요.')+card('새로운 질문',helperText('AI가 답변하지 못한 질문을 확인하고 직접 답변을 교육하면 이후 상담에 활용할 수 있습니다.')+(u.map(x=>`<div class="line question-row${sampleRecord(x)?' sample-record':''}"><div class="question-copy"><span class="status">${e(x.status==='open'?'확인 필요':states[x.status]||x.status)}</span><h3>${e(sampleTitle(x.q,sampleRecord(x)))}</h3></div><div class="question-action">${x.preview?(x.status==='open'?btn('교육 체험',`previewQuestionTrain('${x.id}')`,'primary'):helperText('샘플 교육 완료')):x.sample?btn('상담 보기',`openSampleThread('${x.thread}')`):x.status==='open'?`${ta('answer-'+x.id)}${btn('직접 답변으로 교육',`act(async()=>{showEducationQuote(await api('/api/faq',{q:(await api('/api/unknown')).find(z=>z.id==='${x.id}').q,a:val('answer-${x.id}'),unknown:'${x.id}'}))})`,'primary')}`:''}</div></div>`).join('')||emptyState('확인할 질문이 없습니다.')))}
function localDate(iso){let d=new Date(iso),z=(route==='calendar'?calendarProfile?.timezone:null)||me?.settings.timezone||'Asia/Seoul';return new Intl.DateTimeFormat('sv-SE',{timeZone:z,year:'numeric',month:'2-digit',day:'2-digit'}).format(d)}
function localTime(iso){return new Intl.DateTimeFormat('ko-KR',{timeZone:(route==='calendar'?calendarProfile?.timezone:null)||me?.settings.timezone||'Asia/Seoul',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(iso))}
function dateKey(y,m,d){return `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`}
let calendarAgent='',calendarProfile=null;
let calFilter='all',calendarRange=null,calendarRangeMode=false,calendarRangeAnchor='',calendarMotion=null,calendarRecords=[];
function calendarRangeContains(date){return !!calendarRange&&date>=calendarRange.start&&date<=calendarRange.end}
const calendarFilters=[['all','전체'],['confirmed','확정'],['pending','승인·결제 대기']];
const calendarPending=b=>b.status==='pending'||b.status==='pending_payment';
function calendarFiltered(bs){return bs.filter(b=>calFilter==='all'||(calFilter==='pending'&&calendarPending(b))||b.status===calFilter);}
async function setCalendarFilter(key){
 if(calFilter===key)return;
 calFilter=key;
 await render();
 $(`[data-calendar-filter="${key}"]`)?.focus();
}
function calendarStatusFilters(){
 return `<div class="ui-tabs calendar-status-filters" role="group" aria-label="일정 상태">${calendarFilters.map(([key,text])=>
  `<button type="button" data-calendar-filter="${key}" aria-pressed="${calFilter===key}" onclick="setCalendarFilter('${key}')">${text}</button>`).join('')}</div>`;
}
function calendarDay(){if(selectedDate)return selectedDate;const today=localDate(new Date());const month=dateKey(calendarMonth.getFullYear(),calendarMonth.getMonth(),1);return today.slice(0,7)===month.slice(0,7)?today:month;}
function calendarList(bs){
 const day=calendarDay(),range=calendarRangeMode&&calendarRange;
 const dayLabel=new Intl.DateTimeFormat('ko-KR',{month:'long',day:'numeric',weekday:'short',timeZone:'UTC'}).format(new Date(day+'T00:00:00Z'));
 const dateLabel=range?`${range.start} ~ ${range.end}`:dayLabel;
 const matching=calendarFiltered(bs).filter(b=>range?calendarRangeContains(localDate(b.start)):localDate(b.start)===day);
 return `<h3 id="calendar-results-heading">${e(dateLabel)} 일정</h3>
  ${matching.map(bookingCard).join('')||emptyState('표시할 일정이 없습니다.',{icon:'calendar-days'})}`;
}
function calendarTask(id,title,count,description,content,open){
 return `<details class="calendar-task" id="${id}" ${open?'open':''}>
  <summary>
   <span class="calendar-task-title">${e(title)}</span>
   ${uiIcon('chevron-down')}
   <strong data-task-count>${count.toLocaleString('ko-KR')}건</strong>
   <small data-task-description>${e(description)}</small>
  </summary>
  <div class="calendar-task-content">${content}</div>
 </details>`;
}
function calendarTaskExpanded(id,count){
 const workspace=$('.calendar-workspace');
 return workspace?.dataset.calendarScope===calendarAgent
  ?(workspace.querySelector('#'+id)?.open??count>0)
  :count>0;
}
function calendarQueue(bs){
 const filteredByRange=calendarRangeMode&&calendarRange;
 const bookings=bs.filter(b=>calendarPending(b)&&(!filteredByRange||calendarRangeContains(localDate(b.start))));
 return {
  count:bookings.length,
  description:filteredByRange?'선택 기간에 처리할 예약':'전체 날짜에서 처리할 예약',
  content:bookings.map(bookingCard).join('')||emptyState('승인 또는 결제 확인을 기다리는 예약이 없습니다.'),
 };
}
function calendarChangeTasks(requests){
 const count=requests.filter(request=>request.state==='pending').length;
 const content=requests.map(request=>`<div class="line">
  <strong>${request.action==='cancel'?'취소':'일정 변경'} 요청</strong>
  <p class="ui-helper">${e(request.booking)}${request.start?` · ${e(localDate(request.start)+' '+localTime(request.start))}`:''}</p>
  ${statusBadge(request.state==='pending'?'승인 대기':request.state==='approved'?'승인 완료':'거절',request.state==='approved'?'success':'neutral')}
  ${request.state==='pending'?actionFooter([
   btn('승인',`decideChange('${request.id}','approve')`,'primary'),
   btn('거절',`decideChange('${request.id}','reject')`),
  ],{divided:false}):''}
 </div>`).join('')||emptyState('접수된 변경·취소 요청이 없습니다.');
 return calendarTask('calendar-change-task','고객 예약 변경·취소 요청',count,
  requests.length? `전체 요청 이력 ${requests.length.toLocaleString('ko-KR')}건`:'접수된 요청 없음',
  content,calendarTaskExpanded('calendar-change-task',count));
}
function updateCalendarPanels(){
 const list=$('#calendar-results');
 if(list)list.innerHTML=calendarList(calendarRecords);
 const pending=$('#calendar-booking-task');
 if(pending){
  const queue=calendarQueue(calendarRecords);
  pending.querySelector('[data-task-count]').textContent=queue.count.toLocaleString('ko-KR')+'건';
  pending.querySelector('[data-task-description]').textContent=queue.description;
  pending.querySelector('.calendar-task-content').innerHTML=queue.content;
 }
}
function mountCalendarMotion(){
 calendarMotion?.destroy();calendarMotion=null;const root=$('#db-calendar');if(!root)return;
 const counts={};for(const b of calendarFiltered(calendarRecords)){const d=localDate(b.start);counts[d]=(counts[d]||0)+1;}
 calendarMotion=DBMotion.calendar(root,{year:calendarMonth.getFullYear(),month:calendarMonth.getMonth(),range:true,directRange:true,day:calendarDay(),start:calendarRange?.start||calendarDay(),end:calendarRangeAnchor?null:calendarRange?.end||calendarDay(),anchor:!!calendarRangeAnchor,counts},st=>{
  calendarMonth=new Date(st.year,st.month,1);selectedDate=st.day;calendarRangeAnchor=st.anchor?st.start:'';calendarRange=st.start?{start:st.start,end:st.end||st.start}:null;calendarRangeMode=!!(st.start&&st.end&&st.start!==st.end);
  updateCalendarPanels();
 });
}
function calendarGrid(id='db-calendar',tools=''){
 return `<div id="${id}" class="db-calendar calendar-grid-panel">
  <div class="db-calendar-head"><span class="db-calendar-title db-roll"></span>
   <div class="db-calendar-nav">
    <button type="button" data-prev aria-label="이전 달">${uiIcon('chevron-right')}</button>
    <button type="button" data-next aria-label="다음 달">${uiIcon('chevron-right')}</button>
   </div>
  </div>
  ${tools}
  <div class="db-calendar-week">${['일','월','화','수','목','금','토'].map(day=>`<span>${day}</span>`).join('')}</div>
  <div class="db-calendar-view" aria-label="일정 날짜 선택"></div>
  <div class="db-calendar-foot"><span class="db-calendar-sum db-roll"></span><span class="db-calendar-chip db-roll"></span></div>
 </div>`;
}
const previewStateByAccount=new Map();
function previewData(){
 const key=me?.slug||'guest';if(previewStateByAccount.has(key))return previewStateByAccount.get(key);
 const stamp=Math.floor(Date.now()/1000),date=new Date();
 const bookingExamples=[
  ['지난 촬영 상담','completed',-14,10,1],['기업 프로필 촬영','confirmed',-10,14,2],
  ['제품 촬영','completed',-7,13,2],['예약 취소','cancelled',-5,15,1],
  ['행사 촬영','completed',-2,11,2],['개인 프로필','confirmed',-1,16,1],
  ['가족 촬영','confirmed',0,10,1],['프로필 촬영','pending',0,14,1],['상품 촬영','pending_payment',0,16,2],
  ['출장 촬영','confirmed',1,10,3],['예약 변경 문의','cancelled',2,15,1],
  ['단체 촬영','confirmed',3,11,2],['기업 행사 촬영','pending',4,14,3],
  ['여행 스냅','confirmed',5,10,2],['스튜디오 촬영','confirmed',7,13,2],
  ['웨딩 상담','pending_payment',10,15,1],['상품 사진 촬영','confirmed',14,11,2],
  ['연말 행사 상담','pending',21,16,1]
 ];
 const bookings=bookingExamples.map(([name,status,offset,h,duration],i)=>{const d=new Date(date);d.setDate(d.getDate()+offset);const day=dateKey(d.getFullYear(),d.getMonth(),d.getDate());const time=n=>day+'T'+String(n).padStart(2,'0')+':00:00+09:00';return {id:'preview-booking-'+i,sample:true,preview:true,status,start:time(h),end:time(h+duration),resource:'default',fields:[{key:'name',label:'예약명'},{key:'note',label:'메모'}],payload:{name:'샘플 · '+name,note:'고객 상담을 통한 접수 예시'},paid:status==='confirmed'||status==='completed'};});
 const questions=[{id:'preview-question-1',sample:true,preview:true,status:'open',q:'샘플 · 주말 방문 시 주차가 가능한가요?'},{id:'preview-question-2',sample:true,preview:true,status:'open',q:'샘플 · 예약 날짜 변경은 언제까지 가능한가요?'}];
 const events=[['new','새로운 고객 상담 접수'],['handoff_urgent','긴급 담당자 확인 요청'],['booking','예약 확정 안내'],['unknown','미학습 질문 접수']].map(([kind,title],i)=>({id:'preview-event-'+i,sample:true,preview:true,kind,title:'샘플 · '+title,created:stamp-i*180,seen:false}));
 const work=[['tasks','예약 일정 확인','pending'],['complaints','배송 지연 문의','open'],['quote','행사 촬영 견적 요청','pending'],['leads','가족 촬영 구매 문의','resolved'],['crm','고객 연락 요청','open']].map(([kind,title,status],i)=>({id:'preview-work-'+i,sample:true,preview:true,kind,title:'샘플 · '+title,status,details:'담당자 검토 및 처리 흐름 체험'}));
 const sampleThreads=[
  ['가족 촬영','public',2,false,[['user','주말에 가족사진 예약 가능한가요?']]],
  ['상품 교환','naver',12,false,[['user','상품 사이즈를 교환하고 싶습니다.']]],
  ['가격 안내','public',38,false,[['user','프로필 촬영 가격이 궁금합니다.']]],
  ['AI 상담 후 직접 개입','public',5,true,[['user','예약 시간을 변경하고 싶어요.'],['assistant','변경 가능한 시간을 담당자가 확인하겠습니다.'],['staff','안녕하세요. 담당자입니다. 원하시는 시간을 알려주세요.'],['user','토요일 오후 3시 가능한가요?']]],
  ['담당자 직접 상담','public',9,true,[['user','기업 행사 촬영 견적을 요청합니다.'],['staff','안녕하세요. 행사 일정과 예상 인원을 알려주시면 확인하겠습니다.'],['user','다음 주 금요일, 30명입니다.']]]
 ].map(([name,kind,age,manual,history],i)=>{const activity=stamp-age*60,created=activity-(history.length-1)*60,id='preview-thread-'+i;const messages=history.map(([role,body],j)=>({id:'preview-message-'+i+'-'+j,role,body,created:created+j*60}));if(manual)sampleManualThreads.add(sampleModeKey(id));return {id,name,kind,source:'link',sample:true,preview:true,manual,status:'open',unread:1,created,activity,last:messages.at(-1).body,agent:'',paused_by:'',messages};});
 const state={sampleThreads,bookings,questions,events,work,contacts:[{id:'preview-crm-1',name:'샘플 · 김고객',email:'',phone:'',notes:'가족 촬영 문의 · 담당자 확인 대기',threads:[]},{id:'preview-crm-2',name:'샘플 · 이고객',email:'',phone:'',notes:'프로필 촬영 예약 완료',threads:[]}],quoteItems:[{id:'preview-quote-1',name:'샘플 · 행사 촬영',price:350000,active:true}],quoteOffers:[{id:'preview-offer-1',amount:350000,items:[{name:'샘플 · 행사 촬영',quantity:1}],status:'draft'}],commerce:{enabled:true,products:[{id:'preview-product-1',sku:'DEMO-001',name:'샘플 · 프로필 촬영',variant:'기본',price:90000,stock:12,published:true,url:'',description:'촬영 상품 예시'}],orders:[{id:'preview-order-1',channel:'smartstore',reference:'DEMO-1001',product:'샘플 · 프로필 촬영',quantity:1,amount:90000,state:'preparing',carrier:'',tracking:''}],requests:[{id:'preview-request-1',kind:'exchange',channel:'smartstore',reference:'DEMO-1001',details:'샘플 · 상품 옵션 변경 요청',state:'pending',thread:''}]},email:{settings:{email:'',enabled:true},deliveries:[{status:'샘플 · 발송 완료',error:''},{status:'샘플 · 발송 대기',error:''}],live_enabled:false,auto_enabled:false},report:{settings:{frequency:'daily',enabled:true},worker_enabled:false,reports:[{period:'샘플 · 전일 상담 리포트',summary:{threads:12,resolved:8,unknown:2,messages:54}}]},push:{configured:false,live:false,devices:[],kinds:[],deliveries:[{created:stamp,status:'샘플 · 기기 알림 발송 완료'}]}};
 previewStateByAccount.set(key,state);return state;
}
function previewCalendarRecords(){return previewData().bookings;}
function previewBookingAction(id,status){const b=previewData().bookings.find(x=>x.id===id);if(!b)return;b.status=status;if(status==='confirmed')b.paid=true;toast('샘플 일정 상태 변경 · 실제 예약에는 반영되지 않습니다.');render();}
function previewQuestionTrain(id){const item=previewData().questions.find(x=>x.id===id);if(!item)return;modal('샘플 질문 교육',helperText(item.q)+label('답변',ta('preview-answer',''))+btn('교육 체험',`finishPreviewQuestion('${id}')`,'primary'))}
function finishPreviewQuestion(id){if(!val('preview-answer').trim())return toast('답변을 입력하세요.');const item=previewData().questions.find(x=>x.id===id);if(item)item.status='resolved';$('.modal')?.remove();toast('샘플 교육 완료 · 실제 지식에는 반영되지 않습니다.');render();}
function previewEmailAction(send){const n=previewData().email;n.settings={email:val('notify-email'),enabled:checked('notify-enabled')};if(send)n.deliveries.unshift({status:'샘플 · 발송 완료',error:''});toast(send?'샘플 발송 완료 · 실제 이메일은 보내지 않습니다.':'샘플 설정 저장 완료');render();}
function previewPushAction(action){const r=previewData().push;if(action==='register')r.devices=[{id:'preview-device',created:Math.floor(Date.now()/1000),preferences:{kinds:[],silent:false}}];if(action==='remove')r.devices=[];if(action==='test')r.deliveries.unshift({created:Math.floor(Date.now()/1000),status:'샘플 · 테스트 알림 완료'});toast('샘플 기기 알림 체험 · 실제 등록 및 발송 없음');render();}
function savePreviewQuoteItem(id){previewUpsert(previewData().quoteItems,id,{name:val('qe-name'),price:Number(val('qe-price'))});$('.modal')?.remove();render();}function previewSendQuote(id){const x=previewData().quoteOffers.find(z=>z.id===id);if(x)x.status='sent';toast('샘플 견적 발송 완료 · 실제 발송 없음');render();}function previewWorkAction(id,status){const w=previewData().work.find(x=>x.id===id);if(w)w.status=status;toast('샘플 업무 상태 변경');render();}

async function calendar(){
 try{const jump=JSON.parse(sessionStorage.getItem('csai-calendar-jump'));if(jump){sessionStorage.removeItem('csai-calendar-jump');calendarAgent=jump.agent||'';calendarMonth=new Date(jump.start);selectedDate=new Date(jump.start).toLocaleDateString('sv-SE',{timeZone:me.settings.timezone||'Asia/Seoul'});calFilter='all';}}catch{}
 const readOnly=!has('calendar');
 if(readOnly&&!freeFeaturePreview())return pageTop('일정표 보기','업체 맞춤 일정 양식 및 승인 관리')+locked('calendar','자체 일정표, 수동 관리, 맞춤 양식 설정을 이용할 수 있습니다.');
 const id=renderId;
 const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(brand=>brand.available):[];
 if(id!==renderId)return '';
 if(calendarAgent&&!brands.some(brand=>brand.id===calendarAgent))calendarAgent='';
 const scope=readOnly?'':calendarAgent,brandPath='/api/brand-calendar/'+enc(scope);
 const [data,requests]=await Promise.all([
  readOnly?[]:api(scope?brandPath:'/api/bookings'),
  !readOnly&&has('change_booking')?api(scope?brandPath+'/changes':'/api/booking-changes'):null,
 ]);
 if(id!==renderId)return '';
 const bookings=readOnly?previewCalendarRecords():scope?data.bookings:sharedPreviewEnabled()&&me.sample_tools?data.concat(previewCalendarRecords()):data;
 calendarRecords=bookings;
 calendarProfile=scope?data.settings:null;
 const queue=calendarQueue(bookings);
 const hasPreviewBookings=bookings.some(b=>b.preview);
 const tools=actionGroup(
  btn('맞춤 일정 양식',scope?"brandCalendarFields()":"go('fields')"),
  btn('직접 일정 등록','manualBooking()','primary'),
  btn('예약 설정',scope?"brandCalendarSettings()":"go('booking-settings')"),
  btn('담당자 관리','resourceModal()'),
 );
 const sample=readOnly?null:bookings.find(b=>b.sample&&!b.preview&&b.sample_thread&&b.status==='confirmed');
 const sampleCard=sample?card('샘플 · 상담에서 확정된 예약',helperText('자동 확정 설정을 켠 뒤 고객이 예약 양식을 확인하면 일정표에 등록되는 예시입니다. 실제 예약이나 상담 사용량에는 포함되지 않습니다.')+
  actionFooter([btn('샘플 확정 일정 보기',`jumpSampleBooking('${sample.start}')`,'primary'),btn('연결된 상담 보기',`openSampleThread('${sample.sample_thread}')`)])):
  !readOnly&&!scope&&me.sample_tools?card('예약 흐름 샘플 보기',helperText('상담부터 확정 일정, 담당자 알림까지 연결된 가상 기록을 넣어 확인하세요.')+
   actionFooter([btn('연결 샘플 넣기','addDemoSamples()','primary')])):'';
 return (readOnly?previewNotice('calendar','일정표 및 가상 예약을 직접 둘러볼 수 있습니다'):'')+`<div class="card app-card calendar-workspace" data-calendar-scope="${e(scope)}">
  <header class="calendar-workspace-head">
   ${pageTop('일정표 보기','AI 상담에서 접수·확정된 예약이 자동으로 등록됩니다.')}
   ${brandSelect('calendar-brand',brands,scope,'switchCalendarBrand(this.value)')}
   ${scope?helperText('추가 브랜드 전용 일정표입니다. 예약 설정에서 고객 예약을 활성화할 수 있습니다. 구글 캘린더 연결은 준비 중입니다.'):''}
   <div class="calendar-tools" role="group" aria-label="일정 등록 및 설정">${tools}</div>
  </header>
  <section class="calendar-section" aria-labelledby="calendar-lookup-heading">
   <h2 id="calendar-lookup-heading">일정 조회</h2>
   ${calendarStatusFilters()}
   <div class="calendar-lookup-grid">
    ${calendarGrid('db-calendar',helperText('날짜를 누르면 조회됩니다. 기간은 두 날짜를 선택하거나 드래그하세요.')+(hasPreviewBookings?actionGroup(btn('샘플 7일 일정 조회','showPreviewCalendarWeek()')):''))}
    <section id="calendar-results" class="calendar-grid-panel calendar-results" aria-labelledby="calendar-results-heading">${calendarList(bookings)}</section>
   </div>
  </section>
  <section class="calendar-section" aria-labelledby="calendar-tasks-heading">
   <h2 id="calendar-tasks-heading">처리할 업무</h2>
   <div class="calendar-task-grid">
    ${calendarTask('calendar-booking-task','승인·결제 대기',queue.count,queue.description,queue.content,calendarTaskExpanded('calendar-booking-task',queue.count))}
    ${requests?calendarChangeTasks(requests):''}
   </div>
  </section>
 </div>${sampleCard}`;
}
async function showPreviewCalendarWeek(){const today=localDate(new Date()),end=new Date(today+'T00:00:00Z');end.setUTCDate(end.getUTCDate()+6);calendarMonth=new Date(Number(today.slice(0,4)),Number(today.slice(5,7))-1,1);selectedDate=today;calendarRange={start:today,end:end.toISOString().slice(0,10)};calendarRangeMode=true;calendarRangeAnchor='';calFilter='all';await render();$('#calendar-results')?.scrollIntoView({block:'nearest'});}
async function jumpSampleBooking(start){calendarRange=null;calendarRangeMode=false;calendarRangeAnchor='';calendarMonth=new Date(start);selectedDate=localDate(start);calFilter='confirmed';await render();$('#calendar-results')?.scrollIntoView({block:'nearest'});}
function openSampleThread(id){threadId=id;inboxKind='customer';inboxQuery='';go('inbox')}
function openBookingConversation(id){if(!id)return;threadId=id;inboxAgent='all';inboxUnread=false;inboxSource='all';go('consultation-center');}
async function jumpLinkedBooking(start,agent){if(inboxReplyDraftActive()&&!confirm('작성 중인 내용을 닫고 일정표로 이동할까요?'))return;await leaveTemporary();threadId=null;calendarAgent=agent||'';calendarRange=null;calendarRangeMode=false;calendarRangeAnchor='';calendarMonth=new Date(start);selectedDate=new Date(start).toLocaleDateString('sv-SE',{timeZone:me.settings.timezone||'Asia/Seoul'});calFilter='all';if(inboxDesk()){sessionStorage.setItem('csai-calendar-jump',JSON.stringify({start,agent}));location.href='/#calendar';return;}go('calendar');}
function bookingCard(b){return `<div class="line${sampleRecord(b)?' sample-record':''}"><div class="row between"><strong class="blue">${e(localDate(b.start))} ${e(localTime(b.start))}–${e(localTime(b.end))}</strong><span class="status">${e(states[b.status])}</span></div>${b.fields.map(f=>b.payload[f.key]?`<div class="row between"><small>${e(f.label)}</small><span>${e(sampleTitle(b.payload[f.key],sampleRecord(b)&&f.key==='name'))}</span></div>`:'').join('')}<p class="muted">담당자: ${e(resources().find(r=>r.id===b.resource)?.name||b.resource)}</p><p class="muted">결제 확인: ${b.paid?'완료':'미확인 / 불필요 여부는 업체 정책 확인'}</p>${b.consultation_thread&&!b.sample?btn('관련 상담 열기',`openBookingConversation('${e(b.consultation_thread)}')`):''}${b.preview?'<div class="row">'+(['pending','pending_payment'].includes(b.status)?btn('확정 체험',`previewBookingAction('${b.id}','confirmed')`,'primary'):'')+(['confirmed','pending','pending_payment'].includes(b.status)?btn('취소 체험',`previewBookingAction('${b.id}','cancelled')`):'')+(b.status==='confirmed'?btn('완료 체험',`previewBookingAction('${b.id}','completed')`):'')+'</div>':b.sample?'<p class="muted">고객 확인 후 일정표에 등록된 화면 예시입니다. 실제 일정과 분리되어 있습니다.</p>':`<div class="row">${['pending','pending_payment'].includes(b.status)?btn('확인 및 확정',`approveBooking('${b.id}',${b.status==='pending_payment'})`,'primary'):''}${['confirmed','pending','pending_payment'].includes(b.status)?btn('취소',`bookingAction('${b.id}','cancel')`):''}${b.status==='confirmed'?btn('완료',`bookingAction('${b.id}','complete')`):''}${b.status==='confirmed'&&has('change_booking')?btn('일정 변경',`changeBooking('${b.id}')`):''}${!b.agent&&has('google_calendar')&&['confirmed','cancelled','completed'].includes(b.status)?btn('구글 일정 동기화',`syncCalendar('${b.id}')`):''}</div>`}</div>`}
async function bookingAction(id,action){if(!requirePreviewAccess('calendar'))return;if(action==='cancel'&&!confirm('일정을 취소하시겠습니까?'))return;await act(async()=>{await api(calendarBookingPath(id),{action});render()})}
function approveBooking(id,pay){if(!requirePreviewAccess('calendar'))return;modal('예약 확정',`<p>고객이 확인한 양식과 예약 조건을 검토하세요.</p>${pay?'<label><input class="check" id="paid-ok" type="checkbox"> 외부 결제 내역을 직접 확인했습니다.</label>':''}${btn('확정',`act(async()=>{await api(calendarBookingPath('${id}'),{action:'approve',paid:${pay?"checked('paid-ok')":"false"}});$('.modal').remove();render()})`,'primary')}`)}
function changeBooking(id){if(!requirePreviewAccess('calendar'))return;modal('일정 변경',label('변경 일시',input('new-start','','datetime-local'))+btn('변경 저장',`act(async()=>{await api(calendarBookingPath('${id}'),{action:'change',start:val('new-start')});$('.modal').remove();render()})`,'primary'))}
function fieldsPage(){const readOnly=!has('calendar');if(readOnly&&!freeFeaturePreview())return locked('calendar','일정 양식은 일정표에 포함됩니다.');if(fieldsPreviewMode!==readOnly){fields=null;fieldsPreviewMode=readOnly;}if(fields===null)fields=structuredClone(me.settings.fields);return (readOnly?previewNotice('calendar','맞춤 일정 양식 설정 체험'):'')+pageTop('맞춤 일정 등록 양식','시작 및 종료 일시는 시스템 필수 항목입니다. 나머지는 업체가 정합니다.')+card('수집 항목',`<p class="muted">라벨 · 형식 · 필수 · 삭제 / 순서: 위·아래 버튼</p>${fields.map((f,i)=>`<div class="fieldrow"><input value="${e(f.label)}" onchange="fields[${i}].label=this.value">${select('type-'+i,['text','phone','number','date','time','select','boolean'].map((x,j)=>[x,['텍스트','전화','숫자','날짜','시간','선택','예/아니오'][j]]),f.type).replace('<select','<select onchange="fields['+i+'].type=this.value;render()"')}<label><input type="checkbox" class="check" ${f.required?'checked':''} onchange="fields[${i}].required=this.checked">필수</label>${btn('×',`fields.splice(${i},1);render()`)}</div><div class="row" style="margin-bottom:8px">${i>0?btn('↑',`swapField(${i},-1)`):''}${i<fields.length-1?btn('↓',`swapField(${i},1)`):''}${f.type==='select'?`<input placeholder="선택지: 쉼표 구분" value="${e((f.options||[]).join(','))}" onchange="fields[${i}].options=this.value.split(',').map(x=>x.trim()).filter(Boolean)">`:''}</div>`).join('')}${stack('<div class="row">'+input('field-name','','text','새 항목 이름')+btn('항목 추가','addField()')+'</div>'+
  divider()+actionGroup({keepSize:true},btn('양식 저장','saveFields()','primary'),btn('돌아가기',"go('calendar')"))) }`)}
function addField(){let name=val('field-name').trim();if(!name)return;fields.push({key:'f_'+crypto.randomUUID().slice(0,8),label:name,type:'text',required:false});render()}
function swapField(i,d){[fields[i],fields[i+d]]=[fields[i+d],fields[i]];render()}
async function saveFields(){if(!requirePreviewAccess('calendar'))return;await act(async()=>{await api('/api/settings',{fields},'PATCH');await refresh();fields=structuredClone(me.settings.fields);toast('새 양식 버전을 저장했습니다.')})}
let bookingBlockSerial=0;
function bookingBlockRow(rule={}){
 const id='booking-block-'+(++bookingBlockSerial),kind=rule.kind||'date',allDay=rule.start==='00:00'&&rule.end==='24:00'||!rule.start;
 return `<div class="booking-block-row" data-booking-block>
  <div class="row between"><strong>차단 일정</strong><button type="button" class="ui-button secondary ui-sm" onclick="this.closest('[data-booking-block]').remove()">삭제</button></div>
  ${label('일정 이름',input(id+'-name',rule.name||'','text','예: 점심시간, 휴가').replace('<input','<input data-block-name maxlength="100"'))}
  ${label('반복 유형',select(id+'-kind',[['date','특정 날짜 또는 기간'],['weekly','매주 반복']],kind).replace('<select','<select data-block-kind onchange="toggleBookingBlock(this.closest(\'[data-booking-block]\'))"'))}
  <div class="booking-settings-grid" data-block-date ${kind==='weekly'?'hidden':''}>
   ${label('시작일',input(id+'-from',rule.from||'','date').replace('<input','<input data-block-from'))}
   ${label('종료일',input(id+'-to',rule.to||'','date').replace('<input','<input data-block-to'))}
  </div>
  <div data-block-week ${kind==='weekly'?'':'hidden'}><p class="ui-helper">반복 요일</p><div class="booking-weekdays">${['월','화','수','목','금','토','일'].map((day,i)=>`<label><input type="checkbox" data-block-day value="${i}" ${(rule.days||[0,1,2,3,4,5,6]).includes(i)?'checked':''}><span>${day}</span></label>`).join('')}</div></div>
  <label class="ui-check"><input class="ui-choice" type="checkbox" data-block-all ${allDay?'checked':''} onchange="toggleBookingBlock(this.closest('[data-booking-block]'))"><span>종일 예약 차단</span></label>
  <div class="booking-settings-grid" data-block-hours ${allDay?'hidden':''}>
   ${label('시작 시간',input(id+'-start',allDay?'12:00':rule.start||'12:00','time').replace('<input','<input data-block-start'))}
   ${label('종료 시간',input(id+'-end',allDay?'13:00':rule.end==='24:00'?'23:59':rule.end||'13:00','time').replace('<input','<input data-block-end'))}
  </div>
 </div>`;
}
function toggleBookingBlock(row){row.querySelector('[data-block-date]').hidden=row.querySelector('[data-block-kind]').value==='weekly';row.querySelector('[data-block-week]').hidden=!row.querySelector('[data-block-date]').hidden;row.querySelector('[data-block-hours]').hidden=row.querySelector('[data-block-all]').checked;}
function bookingBlockFields(prefix,s){return `<div class="booking-block-list" id="${prefix}-blocked">${(s.blocked_times||[]).map(bookingBlockRow).join('')}</div><button type="button" class="ui-button secondary" onclick="addBookingBlock('${prefix}')">+ 예약 불가 일정 추가</button>`;}
function addBookingBlock(prefix){const list=document.getElementById(prefix+'-blocked');if(list.children.length>=100){toast('최대 100개까지 등록할 수 있습니다.');return;}list.insertAdjacentHTML('beforeend',bookingBlockRow());list.lastElementChild.querySelector('[data-block-name]').focus();}
function readBookingBlocks(prefix){return [...document.getElementById(prefix+'-blocked').querySelectorAll('[data-booking-block]')].map(row=>{const get=k=>row.querySelector('[data-block-'+k+']'),kind=get('kind').value,all=get('all').checked;const rule={name:get('name').value.trim(),kind,start:all?'00:00':get('start').value,end:all?'24:00':get('end').value};if(kind==='date'){rule.from=get('from').value;rule.to=get('to').value||rule.from;if(!rule.from||rule.from>rule.to)throw Error('예약 불가 날짜를 확인하세요.');}else{rule.days=[...row.querySelectorAll('[data-block-day]:checked')].map(x=>+x.value);if(!rule.days.length)throw Error('반복 요일을 선택하세요.');}if(!rule.start||!rule.end||rule.start>=rule.end)throw Error('예약 불가 시간을 확인하세요.');return rule;});}
function bookingScheduleFields(prefix,s){const p=prefix?prefix+'-':'',closed=prefix?'bc-closed':'closed';return `<div class="booking-settings-form">${label('시간대',input(p+'tz',s.timezone))}<div class="booking-settings-grid">${label('영업 시작',input(p+'open',s.open,'time'))}${label('영업 종료',input(p+'close',s.close,'time'))}${label('기본 소요시간(분)',input(p+'duration',s.duration,'number'))}${label('예약 사이 여유(분)',input(p+'buffer',s.buffer,'number'))}</div><p class="label">정기 휴무 요일</p><div class="booking-weekdays">${['월','화','수','목','금','토','일'].map((x,i)=>`<label><input type="checkbox" class="${closed}" value="${i}" ${s.closed_days.includes(i)?'checked':''}><span>${x}</span></label>`).join('')}</div></div>`;}
function bookingSettings(){const readOnly=!has('calendar');if(readOnly&&!freeFeaturePreview())return locked('calendar','일정표 권한이 필요합니다.');const s=me.settings;return (readOnly?previewNotice('calendar','예약 설정 체험'):'')+pageTop('예약 설정','AI가 고객 예약을 접수할 수 있는 조건을 설정합니다.')+card('예약 가능 시간',bookingScheduleFields('',s))+card('예약 불가 일정',helperText('점심시간, 출장, 휴가 등 지정한 시간에는 신규 예약과 일정 변경이 차단됩니다. 기존 확정 예약은 유지됩니다.')+bookingBlockFields('main',s))+card('예약 처리 방식',`<div class="booking-settings-form">${checkbox('payment-required','외부 결제 확인 후 확정',{checked:s.payment_required})}${label('예약 모드',select('booking-mode',[['manual','수동 승인'],['auto','자동 확정'],['off','OFF']],s.modes.booking))}${helperText('자동 확정은 자동 예약 옵션이 있어야 적용됩니다.')}${actionFooter([btn('돌아가기',"go('calendar')"),btn('저장','saveBookingSettings()','primary')])}</div>`);}
async function saveBookingSettings(){if(!requirePreviewAccess('calendar'))return;await act(async()=>{await api('/api/settings',{timezone:val('tz'),open:val('open'),close:val('close'),duration:+val('duration'),buffer:+val('buffer'),closed_days:[...document.querySelectorAll('.closed:checked')].map(x=>+x.value),blocked_times:readBookingBlocks('main'),payment_required:checked('payment-required'),modes:{booking:val('booking-mode')}},'PATCH');await refresh();toast('예약 설정 저장');go('calendar')})}
function formFields(fs,prefix){return fs.map(f=>label(f.label+(f.required?' *':''),f.type==='select'?select(prefix+f.key,(f.options||[]).map(x=>[x,x]),''):f.type==='boolean'?select(prefix+f.key,[['','선택'],['예','예'],['아니오','아니오']],''):input(prefix+f.key,'',f.type==='phone'?'tel':f.type==='number'?'number':f.type==='date'?'date':f.type==='time'?'time':'text'))).join('')}
function payload(fs,prefix){return Object.fromEntries(fs.map(f=>[f.key,val(prefix+f.key)]))}
function manualBooking(){let s=calendarProfile||me.settings;modal('수동 일정 등록',label('업체 현지 시작 일시',input('manual-start','','datetime-local'))+label('담당자',select('manual-resource',resources().map(r=>[r.id,r.name]),'default'))+formFields(s.fields,'manual-')+(s.payment_required?'<label><input type="checkbox" class="check" id="manual-paid"> 결제 확인 완료</label>':'')+btn('일정 등록','submitManual()','primary'))}
async function submitManual(){if(!has('calendar')&&freeFeaturePreview()){const start=val('manual-start');if(!start)return toast('일시를 선택하세요.');const fields=(calendarProfile||me.settings).fields;const p=payload(fields,'manual-');const d=new Date(start);previewData().bookings.push({id:'preview-booking-'+crypto.randomUUID(),sample:true,preview:true,status:'confirmed',start:d.toISOString(),end:new Date(d.getTime()+3600000).toISOString(),resource:val('manual-resource'),fields,payload:p,paid:$('#manual-paid')?.checked||false});$('.modal')?.remove();toast('샘플 일정 등록 완료');render();return;}if(!requirePreviewAccess('calendar'))return;await act(async()=>{await api(calendarBookingPath(),{start:val('manual-start'),resource:val('manual-resource'),payload:payload((calendarProfile||me.settings).fields,'manual-'),version:(calendarProfile||me.settings).template_version,paid:$('#manual-paid')?.checked||false});$('.modal').remove();render()})}
let activeForm=null,activeDraft=null;
async function bookingForm(token,prefill={}){await act(async()=>{activeForm=await api('/api/booking/form/'+enc(token));$('#booking-box')?.remove();$('#messages').insertAdjacentHTML('beforeend',`<section id="booking-box" class="card booking-form"><h3>예약 정보 확인</h3><p class="muted">시간대: ${e(activeForm.timezone)} · ${activeForm.duration}분</p>${label('담당자',select('booking-resource',activeForm.resources.map(r=>[r.id,r.name]),'default').replace('<select','<select onchange="clearSlots()"'))}${label('예약 날짜',input('booking-date','','date').replace('<input','<input onchange="clearSlots()"'))}${btn('가능 시간 조회','loadSlots()')}<div id="slots"></div>${formFields(activeForm.fields,'booking-')}${btn('예약 내용 확인','submitDraft()','primary')}<p class="muted">이 양식은 예약 접수에만 사용됩니다.</p></section>`);if(prefill.date)$('#booking-date').value=prefill.date;for(let [k,v] of Object.entries(prefill.payload||{})){let field=document.getElementById('booking-'+k);if(field)field.value=v}if(prefill.date){await loadSlots();if(prefill.time&&$('#booking-time')&&[...$('#booking-time').options].some(o=>o.value===prefill.time))$('#booking-time').value=prefill.time}$('#messages').scrollTop=$('#messages').scrollHeight})}
async function loadSlots(){await act(async()=>{let r=await api('/api/booking/availability',{token:chatSession,date:val('booking-date'),resource:val('booking-resource')});$('#slots').innerHTML=r.length?label('예약 시간',select('booking-time',r.map(x=>[x,x]),r[0])):'<p class="muted">예약 가능한 시간이 없습니다.</p>'})}
async function submitDraft(){await act(async()=>{if(!$('#booking-time'))throw Error('예약 시간을 먼저 조회하세요.');activeDraft=await api('/api/booking/draft',{token:chatSession,start:val('booking-date')+'T'+val('booking-time'),version:activeForm.template_version,resource:val('booking-resource'),payload:payload(activeForm.fields,'booking-')});$('#booking-box').innerHTML=`<h3>예약 내용 최종 확인</h3><p>${e(val('booking-date'))} ${e(val('booking-time'))} · ${activeForm.duration}분 · ${e(activeForm.resources.find(r=>r.id===activeDraft.resource)?.name||activeDraft.resource)}</p>${activeDraft.fields.map(f=>`<div class="row between"><small>${e(f.label)}</small><span>${e(activeDraft.payload[f.key]||'')}</span></div>`).join('')}<p class="muted">${activeForm.payment_required?'결제 확인 후 최종 확정됩니다.':'업체 설정에 따라 자동 확정 또는 승인 대기됩니다.'}</p>${actionGroup({keepSize:true},btn('확정 요청','confirmDraft()','primary'),btn('다시 작성','bookingForm(chatSession)'))}`})}
async function confirmDraft(){await act(async()=>{let r=await api('/api/booking/'+activeDraft.id+'/confirm',{token:chatSession,confirmation:activeDraft.token});$('#booking-box').innerHTML=`<h3>${e(states[r.status])}</h3><p>예약번호: ${e(r.id)}</p><p class="muted">${r.status==='confirmed'?'예약이 확정되었습니다.':'업체 확인 후 확정됩니다.'}</p>`})}
async function customers(){let keys=['crm','quote','tasks','leads','complaints'];let brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available):[];if(crmAgent&&!brands.some(x=>x.id===crmAgent))crmAgent='';let archived=brands.some(x=>x.id===crmAgent&&x.archived),a=keys.filter(has),preview=freeFeaturePreview()&&!a.length;let list=a.length?await api(workPath()):[];let stats=has('stats')?await api('/api/stats'):null;if(preview){a=keys;list=previewData().work;}else if(me.sample_tools&&sharedPreviewEnabled()&&!crmAgent){list=list.concat(previewData().work.filter(x=>a.includes(x.kind)));}return pageTop('고객·업무 관리','업무 요청을 정리하고 진행 상태를 관리합니다.')+brandSelect('work-brand',brands,crmAgent,'crmAgent=this.value;render()')+(preview?previewNotice('crm','고객·업무 관리 화면 체험'):'')+(a.length?card('업무 등록',`${archived?'<p>보관된 브랜드 · 업무 조회만 가능</p>':`${label('분류',select('work-kind',a.map(k=>[k,cfg.catalog.addons.find(x=>x.id===k).name]),a[0]))}${label('제목',input('work-title'))}${label('내용',ta('work-detail'))}${btn('등록',"act(async()=>{if(!requirePreviewAccess(val('work-kind')))return;await api('/api/work',{agent:crmAgent,kind:val('work-kind'),title:val('work-title'),details:val('work-detail')});render()})",'primary')}`}${list.map(x=>`<div class="line${sampleRecord(x)?' sample-record':''}"><b>${e(sampleTitle(x.title,sampleRecord(x)))}</b><p>${e(x.details)}</p><small>${e(states[x.status])}</small>${x.preview?btn(x.status==='resolved'?'다시 열기':'완료 체험',`previewWorkAction('${x.id}','${x.status==='resolved'?'open':'resolved'}')`):x.sample?btn('연결된 상담 보기',`openSampleThread('${x.sample_thread}')`):archived?'':actionGroup({keepSize:true},btn('수정',`workEdit('${x.id}')`),btn('삭제',`workDelete('${x.id}',this)`))+(x.status==='open'?btn('완료',`act(async()=>{await api(workPath('${x.id}'),{});render()})`):'')}</div>`).join('')}`):locked('crm','고객 및 업무 기록을 관리합니다.'))+(has('crm')||preview?await crmPanel():'')+(has('leads')||preview?await leadPanel(archived):'')+(has('quote')||preview?await quotePanel(list,archived):'')+(stats?card('계정 전체 상담 통계',`<p>상담 ${stats.threads}건 · 메시지 ${stats.messages}개 · 미학습 ${stats.unknown}건</p>`):(freeFeaturePreview()?previewNotice('stats','상담 통계 화면 체험')+card('계정 전체 상담 통계','<p>상담 —건 · 메시지 —개 · 미학습 —건</p>'):locked('stats','상담 건수와 미학습 질문을 확인합니다.')))+(has('export')?card('계정 상담 기록 다운로드','<p class="muted">상담은 계정 전체, 고객 및 업무는 기본 브랜드 기준입니다.</p><a href="/api/export">엑셀로 저장</a>'):(freeFeaturePreview()?card('계정 상담 기록 다운로드',helperText('상담은 계정 전체, 고객 및 업무는 기본 브랜드 기준입니다.')+btn('엑셀로 저장',"CSAISetup.preview('export')")):locked('export','상담 내역을 엑셀 파일로 저장합니다.')))}
async function channels(){
  const modes=await api('/api/consultation-mode');
  const addon=k=>cfg.catalog.addons.find(a=>a.id===k),price=k=>money(addon(k)?.price||0);
  const items=[
    {k:'chat',name:'전용 웹 채팅',desc:'전용 상담 링크 및 QR코드',icon:'message-circle',action:'관리',click:"go('preview')",price:'기본 포함'},
    {k:'naver',name:'네이버 톡톡',desc:'네이버 고객 상담 채널',logo:'naver-n',action:has('naver')?'연동 설정':'상세 안내',click:has('naver')?"liveChannelModal('naver')":"channelHelp('naver')",price:'월 '+price('naver')},
    {k:'kakao',name:'카카오 AI 챗봇',desc:'카카오톡에서도 교육한 CS AI 상담사가 상담 · AI 기록 조회 · CS AI 수동 발송 불가',logo:'kakao-talk',action:has('kakao')?'연동 설정':'상세 안내',click:has('kakao')?"liveChannelModal('kakao')":"channelHelp('kakao')",price:'월 '+price('kakao')},
    {k:'kakao_consult',name:'카카오 상담톡 (비즈니스 채널용)',desc:'CS AI에서 AI와 담당자가 고객에게 답변합니다. 카카오 비즈니스 채널 인증과 공식 딜러사 계약이 필요합니다.',logo:'kakao-talk',action:'연동 신청',click:'openKakaoConsultRequest()',price:'준비 중 · 외부 비용 별도'},
    {k:'telegram',guide:'https://core.telegram.org/bots/api',name:'텔레그램 봇',desc:'개인 채팅 텍스트 상담',logo:'channel-telegram',action:'연결 설정',click:'telegramModal()',price:'서버 활성화 및 봇 인증 필요'},
    {k:'line',guide:'https://developers.line.biz/en/docs/messaging-api/overview/',name:'LINE 공식 계정',desc:'개인 텍스트 상담 수신 및 답장 토큰 기반 응답',logo:'channel-line',action:'연결 설정',click:'lineModal()',price:'유료 푸시 발송 없음'},
    {k:'instagram',guide:'https://developers.facebook.com/documentation/business-messaging/instagram-messaging/',name:'인스타그램 DM',desc:'전문 계정 메시지 수신 전용',logo:'channel-instagram',action:'연결 설정',click:'instagramModal()',price:'Meta 앱 승인 및 서명 검증 필요'},
    {k:'widget',name:'홈페이지 위젯',desc:'내 홈페이지에 상담창 설치',icon:'app-window',action:has('widget')?'코드 보기':'상세 안내',click:has('widget')?"widgetCodeModal()":"channelHelp('widget')",price:'월 '+price('widget')},
    {k:'google_calendar',name:'Google 캘린더',desc:'예약 및 일정 자동 동기화',logo:'channel-google_calendar',action:has('google_calendar')?'연결 관리':'상세 안내',click:has('google_calendar')?'googleCalendarModal()':"channelHelp('google_calendar')",price:'월 '+price('google_calendar')},
    {k:'external_api',name:'외부 API',desc:'자체 서비스와 상담 기능 연동',icon:'code-xml',action:'상세 안내',click:"channelHelp('external_api')",price:'월 '+price('external_api')},
    {k:'messenger',name:'Messenger',desc:'페이지 · Meta 메시징 권한',logo:'channel-messenger',guide:'https://developers.facebook.com/docs/messenger-platform/',price:'연동 준비 중'},
    {k:'tiktok',name:'TikTok DM',desc:'Business Messaging API 권한',logo:'channel-tiktok',guide:'https://business-api.tiktok.com/portal/docs/business-messaging-api-overview/v1.3',price:'연동 준비 중'},
    {k:'x',name:'X DM',desc:'공식 API 접근 권한 및 요금 검토',logo:'channel-x',guide:'https://help.x.com/en/rules-and-policies/x-api',price:'연동 준비 중'},
    {k:'whatsapp',name:'WhatsApp',desc:'Business Platform · 메시징 정책',logo:'channel-whatsapp',guide:'https://developers.facebook.com/documentation/business-messaging/whatsapp/overview/',price:'연동 준비 중'},
    {k:'discord',name:'Discord',desc:'공식 봇 · 서버 및 DM 권한',logo:'channel-discord',guide:'https://discord.com/developers/docs/intro',price:'연동 준비 중'},
    {k:'gmail',name:'Gmail',desc:'이메일 수신·답장 · Google OAuth 권한',logo:'channel-gmail',guide:'https://developers.google.com/workspace/gmail/api/guides',price:'연동 준비 중'},
  ];
  const pack=addon('channels');
  return pageTop('외부 채널 연동','나의 클론 상담사를 원하는 채널에 배치하세요.')+card('채널 상담 모드',consultationControls(modes,[],true))+`<section class="card app-card assistance-strip" aria-labelledby="assistance-title">${inline('<h2 id="assistance-title">연동 대행</h2>'+helperText('월 구독 후 신청 · 1회 요금 · '+assistancePrices())+actionGroup({keepSize:true},btn('대행 항목 선택','openAssistance()'),me.operator?btn('대행 접수함','assistanceQueue()'):''))}</section>`+`<section class="channel-panel"><h2>상담 채널 연결</h2><p class="channel-intro">고객이 편한 곳에서 CS AI 상담사를 만나도록 설정하세요.</p><div class="channel-list">${items.map(x=>`<div class="channel-item"><span class="channel-icon ${x.k}" aria-hidden="true">${x.logo?`<img src="/assets/${x.logo}.svg" alt="">`:uiIcon(x.icon)}</span><div class="channel-info"><strong>${e(x.name)}</strong><span>${e(x.desc)}</span><small class="${x.k==='chat'?'included':''}">${e(x.price)}</small>${x.guide&&x.click?`<a href="${e(x.guide)}" target="_blank" rel="noopener noreferrer">공식 안내</a>`: ''}</div>${x.click?`<button class="channel-action" onclick="${x.click}">${e(x.action)}</button>`:`<a class="channel-action" href="${e(x.guide)}" target="_blank" rel="noopener noreferrer">공식 안내</a>`}</div>${cfg.demo&&has(x.k)&&['naver','kakao'].includes(x.k)?`<div class="channel-test">${btn('메시지 테스트',`channelModal('${x.k}')`)}</div>`:''}`).join('')}</div></section><section class="channel-bundle"><strong>${e(pack.name)}</strong><p><b>월 ${money(pack.price)}</b> <s>월 ${money(addon('naver').price+addon('kakao').price)}</s></p><span>두 채널을 함께 이용할 때 매월 ${money(addon('naver').price+addon('kakao').price-pack.price)} 할인</span>${btn('통합 연동 자세히 보기',"go('addons')")}</section>`+card('채널 발송 관리',btn('처리 대기·실패·미확인','showDeliveryIssues()'))}
const assistNames={web:'홈페이지 위젯',naver:'네이버 톡톡',kakao:'카카오 AI 챗봇'};
let assistOptions;
function assistSelection(){
 try{return JSON.parse(sessionStorage.getItem('assist-items:'+me.slug)||'[]').filter(k=>Object.hasOwn(assistNames,k))}catch{return []}
}
async function openAssistance(resume=false){
 await act(async()=>{
  assistOptions=await api('/api/billing/assistance');
  if(resume&&assistOptions.active&&assistSelection().length){assistForm();return}
  modal('연동 대행', '<fieldset class="ui-fieldset"><legend>대행할 항목</legend>'+Object.entries(assistNames).map(([k,name])=>checkbox('assist-'+k,name+' · '+money(assistOptions.fees[k]),{checked:assistSelection().includes(k)})).join('')+'</fieldset><div id="assist-total" aria-live="polite"></div>'+helperText('월 구독자 전용 서비스입니다. 채널 이용료는 별도입니다.')+flowActions(btn(assistOptions.active?'신청서 작성하기':'월 구독 후 신청하기','assistNext()','primary')));
  for(const k of Object.keys(assistNames))$('#assist-'+k).onchange=assistTotal;
  assistTotal();
 });
}
function assistTotal(){
 const keys=Object.keys(assistNames).filter(k=>checked('assist-'+k));
 sessionStorage.setItem('assist-items:'+me.slug,JSON.stringify(keys));
 const discount=assistOptions.discounts[keys.length];
 $('#assist-total').textContent='묶음 할인 '+money(discount)+' · 1회 대행료 '+money(keys.reduce((n,k)=>n+assistOptions.fees[k],0)-discount);
}
function assistNext(){
 if(!assistSelection().length){toast('대행할 항목을 선택하세요.');return}
 if(assistOptions.active){assistForm();return}
 sessionStorage.setItem('assist-return:'+me.slug,'1');$('.modal').remove();go('pricing');
}
function assistForm(){
 const choice=(id,opts)=>select(id,[['','선택하세요'],...opts.map(x=>[x,x])],'');
 const blocks=assistSelection().map(k=>card(assistNames[k],label(k==='web'?'홈페이지 주소':k==='naver'?'톡톡 또는 스마트스토어 주소':'카카오 채널 주소 또는 검색용 ID',input('assist-ref-'+k,''))+label('관리자 권한으로 설정 또는 초대 가능 여부',choice('assist-access-'+k,['가능','불가능','모름']))+(k==='web'?label('홈페이지 제작 방식',choice('assist-extra-'+k,['카페24','아임웹','자체 제작','기타','모름'])):label('기존 챗봇 사용 여부',choice('assist-extra-'+k,['없음','있음','모름']))))).join('');
 modal('연동 대행 신청서','<form class="ui-flow-body" onsubmit="event.preventDefault();submitAssistance(this)">'+label('연락 이메일',input('assist-email','','email'))+blocks+helperText('비밀번호나 인증번호를 입력하지 마세요. 권한 또는 기존 챗봇 확인이 필요하면 운영자 확인 후 결제를 진행합니다.')+flowActions('<button type="submit" class="ui-button primary">신청 내용 확인</button>')+'</form>');
 const form=$('#assist-email').form;
 form.querySelectorAll('select,input').forEach(el=>el.required=true);
 form.dataset.client=crypto.randomUUID();
}
async function submitAssistance(form){
 const submit=form.querySelector('[type=submit]');submit.disabled=true;
 try{await act(async()=>{
  const details={};
  for(const k of assistSelection())details[k]={reference:val('assist-ref-'+k),access:val('assist-access-'+k),[k==='web'?'platform':'existing']:val('assist-extra-'+k)};
  const order=await api('/api/billing/orders',{kind:'assistance',client:form.dataset.client,email:val('assist-email'),details});
  if(order.status==='review')modal('확인 요청 접수',helperText('운영자가 신청 내용을 확인한 후 주문 내역에서 결제할 수 있습니다.'));
  else showCheckout(order);
 })}finally{submit.disabled=false}
}
const setupEstimate='예상 비용 · 기본 구축 대행 50만 원부터, 맞춤 컨설팅 및 구축 대행 100만 원부터';
const setupCallback='전화번호를 남겨주시면 담당자가 연락드립니다. 상담 후 필요한 작업과 견적을 확인하고 진행 여부를 결정하세요.';
const setupConsultationTypes={
 basic:{title:'기본 구축 대행',price:'50만 원부터',intro:'사장님이 정해 놓은 운영 방식을 실제 사용할 수 있도록 구축합니다.',items:['사업 및 필요 기능 파악, 구독 패키지 구성 및 결제 안내','AI 상담사 교육, 기능 설정 및 지원되는 채널 연동','작동 테스트 및 사용법 안내']},
 custom:{title:'맞춤 컨설팅 및 구축 대행',price:'100만 원부터',intro:'사장님과 함께 사업 운영 방식을 설계하고 구현합니다.',items:['기본 구축 대행 전체 포함','사업 운영 과정 분석, 상담 자료 정리 및 맞춤 AI 교육','견적·예약·취소 등 상황별 응대 및 예외 처리 기준 설계','맞춤 업무 자동화 설계 및 시나리오별 검수']},
 undecided:{title:'상담 후 결정',price:'',intro:'어떤 구축이 적합한지 상담을 통해 안내받습니다.',items:[]}
};
function openSetupConsultation(){
 const options=Object.entries(setupConsultationTypes).map(([key,o])=>`<label class="setup-consultation-option"><input type="radio" name="setup_type" value="${e(key)}" required><span><strong>${e(o.title)}${o.price?' · '+e(o.price):''}</strong><small>${e(o.intro)}</small>${o.items.length?'<ul>'+o.items.map(item=>'<li>'+e(item)+'</li>').join('')+'</ul>':''}</span></label>`).join('');
 modal('초기 세팅 대행 상담',`<form class="ui-flow-body" onsubmit="event.preventDefault();submitSetupConsultation(this)">
   <fieldset class="setup-consultation-options"><legend>희망 구축 유형을 선택하세요</legend>${options}</fieldset>
   ${helperText('표시 금액은 시작 견적입니다. 최종 비용은 업무 범위와 난이도에 따라 결정되며, 구독료·교육 크레딧·외부 서비스 비용 및 미지원 기능의 별도 개발비는 포함되지 않습니다.')}
   ${label('연락받을 전화번호','<input name="phone" type="tel" autocomplete="tel" maxlength="32" required>')}
   ${label('궁금한 점 (선택)','<textarea name="needs" maxlength="1140" placeholder="예: 스냅 촬영 예약, 카카오 연결, 교환·반품 기준 설계"></textarea>')}
   ${helperText(setupCallback+' 상담 요청 시 결제되는 금액은 없습니다.')}
   ${flowActions('<button type="submit" class="ui-button primary">전화 상담 요청하기</button>')}</form>`);
}
async function submitSetupConsultation(form){
 const button=form.querySelector('[type=submit]');button.disabled=true;
 try{await act(async()=>{
  const type=form.elements.setup_type.value;
  if(!Object.prototype.hasOwnProperty.call(setupConsultationTypes,type))throw Error('희망 구축 유형을 선택하세요.');
  const option=setupConsultationTypes[type];
  const needs='[희망 구축 유형: '+option.title+']'+(form.elements.needs.value.trim()?'\n'+form.elements.needs.value.trim():'');
  form.dataset.client ||= crypto.randomUUID();
  await api('/api/billing/setup-consultations',{phone:form.elements.phone.value,needs,client:form.dataset.client});
  modal('상담 신청 완료',helperText(option.title+' 상담 신청이 접수되었습니다. 담당자가 신청 내용을 확인하고 입력하신 번호로 연락드립니다.'));
 })}finally{button.disabled=false}
}
async function assistanceQueue(){
 await act(async()=>{const [orders,consults]=await Promise.all([api('/api/billing/assistance/queue'),api('/api/billing/setup-consultations/queue')]);
 modal('대행 접수함',consults.map(x=>card('전체 세팅 상담 · '+e(x.slug),helperText(x.phone)+'<p>'+e(x.needs)+'</p>')).join('')+orders.map(o=>card((o.sample?'샘플 · ':'')+(o.status==='review'?'확인 요청':'대행 접수 완료'),helperText(o.items.email)+'<ul>'+Object.entries(o.items.details).map(([k,f])=>'<li>'+e(assistNames[k])+' · '+e([f.reference,f.access,f.platform||f.existing].join(' · '))+'</li>').join('')+'</ul>'+(!o.sample&&o.status==='review'?btn('결제 가능으로 변경',`act(async()=>{await api('/api/billing/assistance/${o.id}/approve',{});await assistanceQueue()})`):''))).join('')||helperText('접수된 신청이 없습니다.'));});
}
function assistEntry(channel){
 return btn('연동 대행 알아보기',`sessionStorage.setItem('assist-items:'+me.slug,JSON.stringify(['${channel}']));openAssistance()`);
}
function channelSetupGuide(channel){
 const steps=channel==='naver'?['톡톡 파트너센터의 연동 관리에서 챗봇 API를 신청하세요.','파트너 ID와 보내기 API 인증키를 아래에 입력하고 저장하세요.','저장 후 표시되는 수신 주소를 네이버의 이벤트 받을 URL에 등록하세요.']:['카카오 챗봇 관리자센터에서 내 채널에 연결할 봇을 선택하세요.','봇 ID를 아래에 입력하고 저장한 뒤 표시되는 스킬 URL을 복사하세요.','카카오에서 스킬 URL을 등록하고 폴백 블록의 응답을 스킬 데이터로 설정한 뒤 배포하세요.'];
 return '<ol>'+steps.map(x=>'<li>'+e(x)+'</li>').join('')+'</ol>'+assistEntry(channel);
}
function widgetCodeModal(){
 const src=e(location.origin+'/widget/'+enc(me.slug));
 const id='csai-widget-'+String(me.slug).replace(/[^a-zA-Z0-9_-]/g,'');
 const floating=`<style>
#${id}{position:fixed;right:16px;bottom:16px;z-index:2147483000;font-family:system-ui,sans-serif}
#${id}>summary{list-style:none;cursor:pointer;background:#2468bd;color:#fff;padding:12px 18px;border-radius:24px;font-size:14px;font-weight:600;box-shadow:0 3px 15px #15284222}
#${id}>summary::-webkit-details-marker{display:none}
#${id} .csai-widget-close,#${id}[open] .csai-widget-open{display:none}
#${id}[open] .csai-widget-close{display:inline}
#${id} iframe{position:fixed;right:16px;bottom:72px;width:min(380px,calc(100vw - 32px));height:min(650px,calc(100dvh - 88px));border:1px solid #e0e6ed;border-radius:14px;background:#fff;box-shadow:0 6px 24px #15284222}
@media(max-width:700px){#${id}[open]{inset:0;background:white}#${id}[open]>summary{border-radius:0;display:block;text-align:right;padding:14px 16px;height:52px;box-sizing:border-box}#${id} iframe{inset:52px 0 0;width:100%;height:calc(100dvh - 52px);border:0;border-radius:0}}
</style>
<details id="${id}"><summary><span class="csai-widget-open">고객 상담</span><span class="csai-widget-close">상담창 닫기</span></summary><iframe src="${src}" title="AI 고객센터" loading="lazy"></iframe></details>`;
 const inlineCode=`<iframe src="${src}" title="AI 고객센터" width="380" height="650" style="border:0;max-width:100%"></iframe>`;
 modal('홈페이지 위젯 코드',helperText('PC는 우측 하단, 모바일은 전체 화면으로 열리는 채팅 위젯입니다. 사이트의 HTML 삽입 영역에서 스타일과 iframe을 허용해야 합니다.')+assistEntry('web')+label('팝업 위젯 코드',ta('widget-code',floating))+copyButton('팝업 코드 복사','widget-code')+accordion('기존 페이지 삽입형 코드',label('삽입 코드',ta('widget-inline-code',inlineCode))+copyButton('삽입 코드 복사','widget-inline-code')));
}
function channelHelp(k){let a=cfg.catalog.addons.find(x=>x.id===k);modal(a.name,`<p>월 ${money(a.price)} 추가 옵션입니다.</p><p>${a.local?'로컬 구현이 있습니다. 공개 HTTPS 환경은 별도 검증이 필요합니다.':'공식 권한 및 실계정 검증 전까지 연결과 실제 판매를 차단합니다.'}</p>${k==='kakao'?kakaoChatbotNotice():''}${actionGroup({keepSize:true},btn('기능 미리보기',`CSAISetup.preview('${k}')`),btn('구독 구성에 추가',`CSAISetup.add('${k}')`,'primary'))}`)}
function table(headers,rows,{numeric=[]}={}){
 const numberClass=index=>numeric.includes(index)?' class="ui-table-number"':'';
 return `<div class="wrap ui-table"><table>
  <thead><tr>${headers.map((value,index)=>`<th${numberClass(index)}>${e(value)}</th>`).join('')}</tr></thead>
  <tbody>${rows.map(row=>`<tr>${row.map((value,index)=>`<td${numberClass(index)}>${e(value)}</td>`).join('')}</tr>`).join('')}</tbody>
 </table></div>`;
}
function billingTabs(){
 const pages=[['pricing','상담 요금'],['features','전체 기능'],['credits','교육 크레딧'],['addons','추가 기능'],['orders','주문·구독 내역'],['allinone','올인원 패키지']];
 return `<nav class="ui-tabs billing-tabs" aria-label="결제 메뉴">${pages.map(([id,name])=>`<button type="button" onclick="go('${id}')" ${route===id?'aria-current="page"':''}>${e(name)}</button>`).join('')}</nav>`;
}
function normalizeAdd(set){let a=new Set(set);if(a.has('channels')){a.delete('naver');a.delete('kakao')}for(let p of cfg.catalog.packages)if(a.has(p.id))p.includes.forEach(x=>a.delete(x));let covered=new Set([...a]);for(let p of cfg.catalog.packages)if(a.has(p.id))p.includes.forEach(x=>covered.add(x));for(let x of cfg.catalog.addons)if(a.has(x.id))x.requires.forEach(k=>{if(!covered.has(k))a.add(k)});return a}
function addonTotal(){let all=[...cfg.catalog.addons,...cfg.catalog.packages],a=normalizeAdd(selectedAdd);return all.filter(x=>a.has(x.id)).reduce((s,x)=>s+x.price,0)-(a.has('naver')&&a.has('kakao')?1900:0)}
let pricingPeriod='month';
let planMotionPeriod='month', planMotionId='';
function planBaseAmount(plan,period){return plan.price*(period==='year'?12:1);}
function planMotionPlan(plans){
 return plans.find(plan=>plan.id===planMotionId)||plans.find(plan=>plan.id===selectedPlan)||plans.find(plan=>plan.id==='lite')||plans[0];
}
function planMotionDigits(amount,previous=amount){
 const digits=Number(amount).toLocaleString('ko-KR');
 const initial=Number(previous).toLocaleString('ko-KR').padStart(digits.length,'0').slice(-digits.length);
 return [...digits].map((digit,index)=>{
  if(digit===',')return '<span class="plan-motion-comma">,</span>';
  const from=initial[index]===','?'0':initial[index];
  return `<span class="plan-motion-digit"><span class="plan-motion-strip" style="--digit:${digit};--from-digit:${from}" ${from===digit?'':'data-roll'}>${Array.from({length:10},(_,value)=>`<span>${value}</span>`).join('')}</span></span>`;
 }).join('');
}
function planMotionBreakdown(plan,period){
 return period==='year'?`월 ${money(plan.price)} × 12개월`:`매월 ${money(plan.price)}`;
}
function planMotionCard(plans){
 const paid=plans.filter(plan=>plan.price>0), plan=planMotionPlan(paid);
 if(!plan)return '';
 const period=planMotionPeriod, amount=planBaseAmount(plan,period), unit=period==='year'?'연':'월';
 return card('월·연 요금 미리보기',`<div class="ui-stack plan-motion-preview" data-period="${period}" data-plan="${e(plan.id)}">
  <div class="plan-motion-controls" onchange="updatePlanMotionPreview()">
   ${label('미리 볼 요금제',select('plan-motion-sku',paid.map(item=>[item.id,item.name]),plan.id))}
   <fieldset class="plan-period-switch">
    <legend>미리보기 기준</legend>
    <div class="plan-period-options">
     <span class="plan-motion-indicator" aria-hidden="true"></span>
     ${[['month','월 요금'],['year','연 요금']].map(([key,caption])=>`<label><input type="radio" name="plan-motion-period" id="plan-motion-${key}" value="${key}" ${period===key?'checked':''}><span>${caption}</span></label>`).join('')}
    </div>
   </fieldset>
  </div>
  <div class="plan-motion-readout">
   <output class="plan-motion-price" for="plan-motion-sku plan-motion-month plan-motion-year">
    <span class="db-motion-sr" data-plan-motion-amount>${unit} ${money(amount)}</span>
    <span class="plan-motion-figure" aria-hidden="true"><span class="plan-motion-number">${planMotionDigits(amount)}</span><span class="plan-motion-currency">원</span><span class="plan-motion-unit">/ ${unit}</span></span>
   </output>
   <p class="plan-motion-breakdown">${planMotionBreakdown(plan,period)}</p>
  </div>
  <div class="plan-motion-inclusions"><span>기본 제공 답변</span><strong data-plan-motion-quota>월 ${plan.quantity.toLocaleString('ko-KR')}회</strong></div>
  ${helperText('실제 구독과 결제는 월 단위로 진행됩니다.')}
 </div>`);
}
function updatePlanMotionPreview(){
 const preview=$('.plan-motion-preview'), id=$('#plan-motion-sku').value;
 const period=preview.querySelector('input:checked').value;
 const plans=cfg.catalog.plans, plan=plans.find(item=>item.id===id);
 const previousPlan=plans.find(item=>item.id===preview.dataset.plan);
 const previousPeriod=preview.dataset.period, unit=period==='year'?'연':'월';
 const amount=planBaseAmount(plan,period), previous=planBaseAmount(previousPlan,previousPeriod);
 const indicator=preview.querySelector('.plan-motion-indicator');
 const animate=typeof indicator.animate==='function'&&!matchMedia('(prefers-reduced-motion: reduce)').matches;
 const start=animate?getComputedStyle(indicator).transform:'';
 const breakdown=preview.querySelector('.plan-motion-breakdown');
 planMotionPeriod=period;
 planMotionId=id;
 preview.dataset.period=period;
 preview.dataset.plan=id;
 preview.querySelector('[data-plan-motion-amount]').textContent=`${unit} ${money(amount)}`;
 preview.querySelector('.plan-motion-number').innerHTML=planMotionDigits(amount,previous);
 preview.querySelector('.plan-motion-unit').textContent=`/ ${unit}`;
 preview.querySelector('[data-plan-motion-quota]').textContent=`월 ${plan.quantity.toLocaleString('ko-KR')}회`;
 breakdown.textContent=planMotionBreakdown(plan,period);
 if(animate&&period!==previousPeriod){
  const forward=period==='year';
  indicator.getAnimations().forEach(animation=>animation.cancel());
  indicator.animate([
   {transform:start},
   {transform:`translateX(${forward?43:14}%) scaleX(1.42)`,offset:.52},
   {transform:`translateX(${forward?100:0}%) scaleX(1)`},
  ],{duration:460,easing:'cubic-bezier(.2,.7,.3,1)'});
  breakdown.getAnimations().forEach(animation=>animation.cancel());
  breakdown.animate([{transform:`translateY(${forward?8:-8}px)`,opacity:0},{transform:'translateY(0)',opacity:1}],{duration:320,easing:'ease-out'});
 }
}
function planPrice(plan,period=pricingPeriod){return money(planBaseAmount(plan,period));}
function planPriceTable(plans){
 return stack(`<div data-plan-prices>${table(['요금제','월 답변',pricingPeriod==='year'?'연 요금':'월 요금'],
  plans.map(plan=>[plan.name,plan.id==='free'?'최초 1회':plan.quantity.toLocaleString(),planPrice(plan)]),{numeric:[1,2]})}</div>`+
  `<div class="plan-period" data-period="${pricingPeriod}">
   <fieldset class="plan-period-switch" aria-describedby="plan-period-hint" onchange="setPricingPeriod(event.target.value)">
    <legend>요금 표시 기준</legend>
    <div class="plan-period-options">
     ${[['month','월 요금'],['year','연 요금']].map(([key,label])=>`<label><input type="radio" name="plan-price-period" value="${key}" ${pricingPeriod===key?'checked':''}><span>${label}</span></label>`).join('')}
    </div>
   </fieldset>
   ${helperText('연 요금은 월 요금의 12개월 합계입니다. 현재 구독은 월 단위로 계산됩니다.','plan-period-hint')}
  </div>`);
}
function setPricingPeriod(period){
 if(!['month','year'].includes(period)||period===pricingPeriod)return;
 pricingPeriod=period;
 const table=$('[data-plan-prices] table');
 $('.plan-period').dataset.period=period;
 table.tHead.rows[0].cells[2].textContent=period==='year'?'연 요금':'월 요금';
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 [...table.tBodies[0].rows].forEach((row,index)=>{
  const cell=row.cells[2], value=planPrice(cfg.catalog.plans[index],period);
  if(cell.textContent===value)return;
  const text=document.createElement('span');
  text.className='plan-price-value';
  text.textContent=value;
  cell.replaceChildren(text);
  if(!reduced)text.animate([{transform:'translateY(5px)',opacity:.35},{transform:'none',opacity:1}],{duration:200,easing:'ease-out'});
 });
}
function pricing(){return pricingBuilder()}
const pricingGroups={'채널·디자인':'channel','예약·일정':'booking','고객·업무':'work','알림':'alert'},packageGroup={channel_pack:'channel',booking_pack:'booking',customer_pack:'work',work_pack:'work',design_pack:'channel',alert_pack:'alert',all:'all'};
const priceMark='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 12.5l4 4L18 8"/></svg>';
function priceChoice(item,kind,group,coveredBy=''){let selected=selectedAdd.has(item.id),covered=Boolean(coveredBy),on=selected||covered,description=kind==='package'?`${item.includes.length}개 기능 포함`:covered?`${coveredBy}에 포함`:item.local?'개별 선택':'연동 준비 중';return `<label class="price-choice price-group-${group} ${covered?'is-covered':''}" data-price-key="${e(kind+'-'+item.id)}" data-price-on="${on?1:0}" data-price-strike="${covered?1:0}"><input type="checkbox" ${on?'checked':''} ${covered?'disabled':''} aria-label="${e(item.name)} ${covered?'패키지에 포함':''}" onchange="toggleAdd('${item.id}',this.checked)"><span class="price-check">${priceMark}</span><span class="price-choice-copy"><span class="price-choice-name">${e(item.name)}<i class="price-strike"></i></span><small>${e(description)}</small></span><b>${covered?'포함':money(item.price)}</b></label>`}
function assistancePrices(){
 return Object.entries(cfg.catalog.assistance.fees).map(([channel,fee])=>assistNames[channel]+' '+money(fee)).join(' · ');
}
function pricingAssistanceOption(){
 const {discounts}=cfg.catalog.assistance;
 const prices=assistancePrices();
 const terms='1회 대행료 · '+prices+'. 2개 선택 시 '+money(discounts[2])+', 3개 선택 시 '+money(discounts[3])+' 할인됩니다.';
 if(selectedPlan==='free')return helperText('연동 대행은 월 구독 결제 후 신청할 수 있습니다. '+terms);
 const key='assist-return:'+me.slug;
 return `<div class="ui-section" onchange="togglePricingAssistance(event.target.checked)">${checkbox('pricing-assistance','연동 대행 신청',{checked:sessionStorage.getItem(key)==='1',hint:terms})}${helperText('월 구독 결제 후 신청서를 작성하고 대행료를 별도로 결제합니다.')}</div>`;
}
function togglePricingAssistance(enabled){
 const key='assist-return:'+me.slug;
 if(enabled)sessionStorage.setItem(key,'1');
 else sessionStorage.removeItem(key);
}
function pricingBuilder(){let cat=cfg.catalog,selectedPackages=cat.packages.filter(p=>selectedAdd.has(p.id)),coveredBy=new Map();for(let p of selectedPackages)for(let id of p.includes)coveredBy.set(id,p.name);let chosen=cat.addons.filter(a=>selectedAdd.has(a.id)&&!coveredBy.has(a.id)),count=new Set([...coveredBy.keys(),...chosen.map(a=>a.id)]).size;let taskList=`<section class="price-task-list"><div class="price-task-head"><strong>내 구성</strong><span>추가 기능 ${count}개 선택</span></div>${selectedPackages.length||chosen.length?selectedPackages.map(p=>`<details class="ui-disclosure price-task-package price-group-${packageGroup[p.id]}"><summary><span class="price-task-check">${priceMark}</span><b>${e(p.name)} 패키지</b><small>${p.includes.length}개 포함</small></summary><div class="price-task-children">${p.includes.map(id=>{let a=cat.addons.find(x=>x.id===id);return `<div><span class="price-task-check">${priceMark}</span>${e(a?.name||id)}${a&&!a.local?' · 준비 중':''}</div>`}).join('')}</div></details>`).join('')+chosen.map(a=>`<div class="price-task-single price-group-${pricingGroups[a.group]}"><span class="price-task-check">${priceMark}</span>${e(a.name)}</div>`).join(''):'<p class="muted">패키지나 필요한 기능을 선택하세요.</p>'}</section>`;let packages=`<section class="price-section"><h3>패키지로 묶어 선택</h3><p class="muted">선택하면 포함된 개별 기능은 아래에서 취소선으로 표시되고 중복 결제되지 않습니다.</p>${cat.packages.map(p=>priceChoice(p,'package',packageGroup[p.id])).join('')}</section>`;let addons=[...new Set(cat.addons.map(a=>a.group))].map(g=>`<section class="price-section price-group-${pricingGroups[g]}"><h3>${e(g)}</h3>${cat.addons.filter(a=>a.group===g).map(a=>priceChoice(a,'addon',pricingGroups[g],coveredBy.get(a.id)||'')).join('')}</section>`).join('');return pageTop('요금제 및 결제','기본 상담 구독 + 교육 크레딧 + 유료 추가 기능')+billingTabs()+usageMeter()+`<div class="grid pricing-layout"><div class="pricing-left ui-stack ui-stack-sections">${card('AI 상담 월 구독',planPriceTable(cat.plans)+helperText('AI 답장 비서: 초안 3개 생성당 상담량 1회 차감. 무료 상담 테스트와 공유하며, 교육 크레딧은 차감하지 않습니다. 저장 답변·자동완성·복사·삽입은 차감 없음.'))}${planMotionCard(cat.plans)}</div>${card('맞춤 구독 구성',label('기본 요금제',select('plan',cat.plans.map(x=>[x.id,x.name+' · '+money(x.price)]),selectedPlan).replace('<select','<select onchange="selectPricingPlan(this)"'))+taskList+packages+addons+(selectedAdd.has('extra_agent')?label('추가 브랜드 수량',`<input id="extra-brand-quantity" type="number" min="1" max="1000" value="${selectedBrandCount}" onchange="changeBrandQuantity(this.value)">`):'')+pricingAssistanceOption()+`<div class="banner" id="quote-price"></div>${me.sandbox_allowed?btn('테스트용 구독 적용','applyPlan()','primary'):'<p>실제 결제 연동 준비 중</p>'}<p class="muted">실제 결제되지 않습니다. 준비 중 기능은 테스트 구독에도 실연동되지 않습니다.</p>`)}</div>`}
let pricingMotionPrevious=new Map();
function animatePricing(){let reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;document.querySelectorAll('.price-choice').forEach(row=>{let key=row.dataset.priceKey,on=Number(row.dataset.priceOn),strike=Number(row.dataset.priceStrike),previous=pricingMotionPrevious.get(key);pricingMotionPrevious.set(key,{on,strike});let from=previous||{on,strike},box=row.querySelector('.price-check'),path=row.querySelector('path'),line=row.querySelector('.price-strike'),spring=(x,k,c)=>({x,v:0,t:x,k,c}),fill=spring(from.on,300,24),pop=spring(1,520,13),check=spring(from.on,160,20),cross=spring(from.strike,140,22);fill.t=on;check.t=on;cross.t=strike;let changed=from.on!==on||from.strike!==strike;if(changed&&!reduce){pop.x=.7;pop.v=5}if(!changed||reduce){fill.x=on;check.x=on;cross.x=strike}let last=performance.now(),clamp=x=>Math.max(0,Math.min(1,x));function paint(){let f=clamp(fill.x);box.style.background=f>.01?`color-mix(in srgb, var(--price-accent) ${(f*100).toFixed(1)}%, #e8edf2)`:'';box.style.transform=`scale(${pop.x.toFixed(4)})`;path.style.strokeDasharray='18';path.style.strokeDashoffset=(18*(1-clamp(check.x))).toFixed(2);line.style.width=(clamp(cross.x)*100).toFixed(2)+'%'}paint();if(!changed||reduce)return;function frame(now){if(!row.isConnected)return;let dt=Math.min((now-last)/1000,1/30)/4;last=now;for(let i=0;i<4;i++)for(let s of [fill,pop,check,cross]){let a=-s.k*(s.x-s.t)-s.c*s.v;s.v+=a*dt;s.x+=s.v*dt}paint();if([fill,pop,check,cross].some(s=>Math.abs(s.x-s.t)>.002||Math.abs(s.v)>.02))requestAnimationFrame(frame)}requestAnimationFrame(frame)})}
const pricingBaseRender=render;
render=async function(){await pricingBaseRender();if(route==='pricing')requestAnimationFrame(animatePricing)};
function allInOnePreserved(){return (me.addons||[]).filter(x=>['extra_agent','domain','external_api','custom_integration'].includes(x))}
function allinone(){let c=cfg.catalog,p=c.packages.find(x=>x.id==='all'),plan=c.plans.find(x=>x.id===allPlan&&x.price>0)||c.plans.find(x=>x.id==='basic'),credit=c.education.find(x=>x.id===allEducation&&x.price>0),preserved=allInOnePreserved(),extra=preserved.reduce((n,k)=>n+(c.addons.find(x=>x.id===k)?.price||0)*(k==='extra_agent'?(me.brand_quantity||1):1),0),monthly=plan.price+p.price+extra,individual=p.includes.reduce((n,id)=>n+(c.addons.find(x=>x.id===id)?.price||0),0),included=p.includes.map(id=>c.addons.find(x=>x.id===id)).filter(Boolean);return pageTop('올인원 패키지','상담량과 교육 크레딧을 선택해 내 조합을 확인하세요.')+billingTabs()+`<section class="allinone-hero"><small>ALL-IN-ONE</small><h2>상담량은 맞게 고르고,<br>기능은 한 번에.</h2><p>기존 올인원 추가 기능 월 ${money(p.price)}</p></section>`+card('내 조합 만들기',`<div class="grid">${label('월 기본 상담량',select('all-plan',c.plans.filter(x=>x.price>0).map(x=>[x.id,`${x.name} · 월 ${x.quantity.toLocaleString()}회 · ${money(x.price)}`]),plan.id).replace('<select','<select onchange="allPlan=this.value;render()"'))}${label('교육 크레딧 (일회성)',select('all-credit',[['','추가 안 함'],...c.education.filter(x=>x.price>0).map(x=>[x.id,`${x.quantity.toLocaleString()} C · ${money(x.price)}`])],allEducation).replace('<select','<select onchange="allEducation=this.value;render()"'))}</div><div class="allinone-price"><div><span>${e(plan.name)} · 월 상담 ${plan.quantity.toLocaleString()}회</span><b>${money(plan.price)}</b></div><div><span>올인원 추가 기능</span><b>${money(p.price)}</b></div>${extra?`<div><span>기존 별도 구매 기능 유지</span><b>${money(extra)}</b></div>`:''}<div><span>교육 크레딧 ${credit?credit.quantity.toLocaleString()+' C':'추가 없음'}</span><b>${credit?money(credit.price):'0원'}</b></div><div class="allinone-total"><span>매월 구독료</span><strong>${money(monthly)}</strong></div><p>교육 크레딧까지 선택한 첫 주문 예상 합계 <b>${money(monthly+(credit?.price||0))}</b></p></div><p class="muted">올인원에 포함된 기능을 개별 구매하면 월 ${money(individual)}입니다. 기존 패키지 가격은 월 ${money(individual-p.price)} 저렴합니다. 교육 크레딧은 기존 가격 그대로이며 매월 자동 충전되지 않습니다.</p>${me.sandbox_allowed?`<div class="row allinone-actions">${btn('올인원 테스트 구독 주문','orderAllInOne()','primary')}${credit?btn('교육 크레딧 별도 주문','orderAllEducation()'):''}</div><p class="muted">구독과 교육 크레딧은 현재 각각 테스트 주문으로 처리됩니다. 실제 결제되지 않습니다.</p>`:'<p class="muted">실결제 연결 전에는 구매할 수 없습니다.</p>'}`)+card('포함 기능과 제공 상태',`<p>추가 기능 ${included.length}개 포함 · 외부 권한이 필요한 기능은 준비 중</p><div class="allinone-features">${included.map(x=>`<span>${e(x.name)}${x.local?'':' · 준비 중'}</span>`).join('')}</div><p class="muted">추가 브랜드 상담원, 자체 도메인, 외부 API 등은 패키지에 포함되지 않습니다.</p>`)}
async function orderAllInOne(){await act(async()=>{await openCheckout({kind:'subscription',plan:allPlan,addons:['all',...allInOnePreserved()],brand_quantity:(me.addons||[]).includes('extra_agent')?(me.brand_quantity||1):0})})}
async function orderAllEducation(){await act(async()=>{if(allEducation)await openCheckout({kind:'education',sku:allEducation})})}
function toggleAdd(k,on){let p=cfg.catalog.packages.find(x=>x.id===k);if(on&&p)for(let other of cfg.catalog.packages)if(other.id!==k&&selectedAdd.has(other.id)&&other.includes.some(id=>p.includes.includes(id)))selectedAdd.delete(other.id);if(on)selectedAdd.add(k);else selectedAdd.delete(k);selectedAdd=normalizeAdd(selectedAdd);if(selectedPlan==='free'&&selectedAdd.size)selectedPlan='lite';render()}
function changeBrandQuantity(v){selectedBrandCount=Math.max(1,Math.min(1000,Math.trunc(Number(v)||1)));render()}
function selectPricingPlan(el){selectedPlan=el.value;if(selectedPlan==='free'&&selectedAdd.size){selectedPlan='lite';el.value='lite';toast('추가 기능에는 유료 기본 요금제가 필요합니다.')}updatePrice()}
function updatePrice(){if($('#quote-price'))$('#quote-price').innerHTML=`<b class="motion-quote-value">예상 월 ${money(cfg.catalog.plans.find(x=>x.id===selectedPlan).price +addonTotal()+(selectedAdd.has('extra_agent')?(selectedBrandCount-1)*cfg.catalog.addons.find(x=>x.id==='extra_agent').price:0))}</b><br><small>교육 및 알림톡·문자 별도</small>`;CSAISetup.mount()}
async function applyPlan(){await act(async()=>{if(selectedPlan==='free'){await api('/api/demo/billing',{plan:'free',addons:[]});await refresh();render();return}await openCheckout({kind:'subscription',plan:selectedPlan,addons:[...normalizeAdd(selectedAdd)],brand_quantity:selectedAdd.has('extra_agent')?selectedBrandCount:0})})}
const comparisonTones={
 '포함':'included','미제공':'unavailable','추가 결제':'extra',
 '준비 중':'upcoming','추가 결제 · 준비 중':'upcoming',
};
function comparisonTable(title,headers,rows){
 const valueCell=value=>Object.hasOwn(comparisonTones,value)
  ?`<span class="ui-comparison-status" data-tone="${comparisonTones[value]}">${e(value)}</span>`
  :e(value);
 return `<div class="ui-comparison">
  <table aria-label="${e(title)}">
   <colgroup><col class="ui-comparison-feature"><col><col></colgroup>
   <thead><tr>${headers.map(name=>`<th scope="col">${e(name)}</th>`).join('')}</tr></thead>
   <tbody>${rows.map(([feature,...values])=>`<tr><th scope="row">${e(feature)}</th>${values.map(value=>`<td>${valueCell(value)}</td>`).join('')}</tr>`).join('')}</tbody>
  </table>
 </div>`;
}
const adminFeatureExamples={
 widget:'홈페이지 상담 버튼에서 접수',naver:'네이버 톡톡 문의 접수',kakao:'카카오 AI 챗봇 응답 대상',channels:'네이버·카카오 통합 상담함 조회',
 multilingual:'고객 언어에 맞춘 상담 요청',extra_agent:'촬영 전문 브랜드 상담원 배정',design:'채팅창 테마 미리보기',unbrand:'업체 브랜드로 표시할 상담창',
 custom_url:'상담 전용 링크 안내',domain:'업체 도메인의 상담 페이지',calendar:'일정표에서 예약 확인',auto_booking:'빈 시간 확인 후 예약 확정',
 change_booking:'기존 예약 변경 요청',google_calendar:'외부 캘린더에 표시할 일정',booking_alert:'예약 확정 알림 예시',crm:'고객 상담 이력',
 quote:'견적서에 포함할 요청',tasks:'담당자 확인 업무',leads:'후속 연락이 필요한 잠재고객',complaints:'담당자 검토가 필요한 불편 접수',
 stats:'상담 주제별 집계 예시',export:'내보낼 상담 기록',retention:'보관 대상 상담 이력',external_api:'외부 서비스에서 조회할 상담',
 push:'담당자 푸시 알림 예시',email:'담당자 이메일 알림 예시',unknown_alert:'답변 보완이 필요한 질문 알림',new_alert:'신규 문의 알림',
 report:'상담 보고서에 포함할 주제',custom_integration:'외부 업무 도구로 전달할 요청'
};
async function showAdminExamples(){
 await act(async()=>{
  const examples=await api('/api/demo/feature-examples');
  const options=[...cfg.catalog.basic.map(name=>[name,name]),...cfg.catalog.addons.map(a=>[a.id,a.name])];
  modal('기능별 사용 예시',label('기능 선택',select('admin-example-feature',options,options[0][0]))+'<div id="admin-example-list"></div>');
  const update=()=>{
   const feature=val('admin-example-feature');
   const caption=adminFeatureExamples[feature]||feature;
   $('#admin-example-list').innerHTML=table(['예시','고객 문의'],examples.map(x=>[e(x.service+' · '+caption),e(x.question)]));
  };
  $('#admin-example-feature').onchange=update;update();
 });
}
function features(){
 const columns=['기능','무료 회원','유료 구독'];
 const freeFeatures=['말투 설정','업체명·로고','공지·구매처 안내','기본 자동·수동 설정'];
 const basic=[
  ['최초 교육 20크레딧','포함','포함'],['최초 상담 테스트','1회','월 제공량'],
  ['자주 쓰는 답변','차감 없음','차감 없음'],['답변 자동완성','차감 없음','차감 없음'],['AI 답장 비서 (초안 3개)','최초 1회 공유','상담량 1회 차감'],
  ...cfg.catalog.basic.map(name=>{
   if(name==='AI 교육 (크레딧 차감)')return [name,'크레딧 차감','크레딧 차감'];
   const free=name==='상담 내역 열람'?'1회 테스트 기록':freeFeatures.includes(name)?'포함':'미제공';
   return [name,free,'포함'];
  }),
 ];
 const extras=cfg.catalog.addons.map(addon=>[addon.name,'미제공',addon.local?'추가 결제':'추가 결제 · 준비 중']);
 return pageTop('전체 기능 비교','기본 포함, 별도 구매 및 준비 중 구분')+billingTabs()+
  card('기본 제공',comparisonTable('기본 제공 기능 비교',columns,basic)+helperText('답장 비서는 별도 추가 기능 구매 없이 이용할 수 있습니다. 생성 1회(초안 3개)는 기존 상담량 1회를 차감하며, 무료 회원은 최초 상담 테스트 1회를 공유합니다. 저장 문구·자동완성·복사·삽입은 차감되지 않습니다.'))+
  card('추가 결제 기능',comparisonTable('추가 결제 기능 비교',columns,extras))+(me.operator||me.demo_view==='developer'?card('관리자 샘플',btn('기능별 사용 예시','showAdminExamples()')):'');
}
function usageMeter(){const plan=cfg.catalog.plans.find(x=>x.id===me.plan),quota=Number(plan?.quantity||1),remaining=Math.max(0,Number(me.remaining)||0),used=Math.max(0,quota-remaining),bounded=Math.min(100,used/quota*100);return card('계정 공통 사용량',`<div class="real-usage-meter"><strong class="usage-number">${remaining.toLocaleString('ko-KR')}회</strong><small>남은 상담 횟수</small>${me.trial||me.operator?'':`<div class="real-meter-track" role="progressbar" aria-label="상담 사용량" aria-valuemin="0" aria-valuemax="${quota}" aria-valuenow="${Math.min(quota,used)}"><span style="--used:${bounded}%"></span></div><div class="row"><span>사용 ${used.toLocaleString('ko-KR')}회</span><span>제공 ${quota.toLocaleString('ko-KR')}회</span></div>`}<details class="ui-disclosure"><summary>교육 크레딧 잔액</summary><strong>${Math.max(0,Number(me.credits)||0).toLocaleString('ko-KR')} C</strong><p class="muted">교육 크레딧은 일회성 충전 잔액이며 월 상담량과 별개입니다.</p></details><p class="muted">추가 브랜드도 계정의 상담량과 교육 크레딧을 함께 사용합니다.</p></div>`)}
const creditCartLimitTimers=new WeakMap();
function creditCart(){
 const products=cfg.catalog.education.filter(product=>product.price>0);
 const sku=products.some(product=>product.id==='mini')?'mini':products[0]?.id;
 if(!sku)return '';
 return `<form class="credit-cart ui-stack" data-packed="false"
  onsubmit="event.preventDefault();startCreditCheckout(this)" onchange="if(event.target.id==='edu-sku')setCreditCart(this,false)">
  ${label('충전 상품',select('edu-sku',products.map(product=>[product.id,product.name+' · '+money(product.price)]),sku))}
  <div class="credit-cart-row">
   <div class="credit-cart-control">
    <span class="credit-cart-limit-notice" role="status"></span>
    <div class="credit-cart-stepper" role="group" aria-label="크레딧 상품 담기" aria-describedby="credit-cart-limit">
     <button type="button" class="credit-cart-remove" aria-label="담은 팩 빼기" hidden
      onclick="setCreditCart(this.form,false);this.form.querySelector('.credit-cart-add').focus()">
      <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 7h16M10 11v6m4-6v6M9 7V4h6v3m3 0-1 13H7L6 7"/></svg>
     </button>
     <span class="credit-cart-quantity" aria-hidden="true" hidden><span>1</span></span>
     <button type="button" class="credit-cart-add" aria-label="선택한 팩 담기" onclick="addCreditPack(this.form)">
      <span class="credit-cart-add-text" aria-hidden="true">담기</span>
      <span class="credit-cart-add-glyph"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></span>
     </button>
    </div>
   </div>
   <button type="submit" class="ui-button primary" disabled>로컬 테스트 충전</button>
  </div>
  <p class="ui-helper" id="credit-cart-limit">한 주문에 한 팩씩 충전할 수 있어요.</p>
  <p class="credit-cart-summary" role="status">담은 상품이 없습니다.</p>
 </form>`;
}
function addCreditPack(form){
 if(form.dataset.packed!=='true'){setCreditCart(form,true);return;}
 const notice=form.querySelector('.credit-cart-limit-notice');
 const counter=form.querySelector('.credit-cart-quantity > span');
 notice.textContent='주문당 최대 1팩';
 clearTimeout(creditCartLimitTimers.get(form));
 creditCartLimitTimers.set(form,setTimeout(()=>{notice.textContent='';},1600));
 if(typeof counter.animate==='function'&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
  counter.getAnimations().forEach(animation=>animation.cancel());
  counter.animate([0,-3,3,-2,2,0].map(x=>({transform:`translateX(${x}px)`})),{duration:300,easing:'ease-out'});
 }
}
function setCreditCart(form,packed){
 if(form.dataset.busy==='true'||form.dataset.packed===String(packed))return;
 const product=cfg.catalog.education.find(item=>item.id===form.querySelector('#edu-sku').value&&item.price>0);
 if(packed&&!product)return;
 form.dataset.packed=String(packed);
 delete form.dataset.checkoutClient;
 const notice=form.querySelector('.credit-cart-limit-notice');
 clearTimeout(creditCartLimitTimers.get(form));
 notice.textContent='';
 const add=form.querySelector('.credit-cart-add');
 add.setAttribute('aria-label',packed?'주문 수량 한도 확인':'선택한 팩 담기');
 form.querySelector('.credit-cart-remove').hidden=!packed;
 form.querySelector('.credit-cart-quantity').hidden=!packed;
 form.querySelector('[type="submit"]').disabled=!packed;
 form.querySelector('.credit-cart-summary').textContent=packed?
  `${product.name} · ${product.quantity.toLocaleString('ko-KR')} C · ${money(product.price)}`:'담은 상품이 없습니다.';
}
async function startCreditCheckout(form){
 if(form.dataset.packed!=='true'||form.dataset.busy==='true')return;
 const sku=form.querySelector('#edu-sku');
 const submit=form.querySelector('[type="submit"]');
 const remove=form.querySelector('.credit-cart-remove');
 const add=form.querySelector('.credit-cart-add');
 const client=form.dataset.checkoutClient||(form.dataset.checkoutClient=crypto.randomUUID());
 form.dataset.busy='true';
 submit.setAttribute('aria-busy','true');
 sku.disabled=remove.disabled=add.disabled=submit.disabled=true;
 try{await openCheckout({kind:'education',sku:sku.value},client);}
 catch(error){toast(error.message);}
 finally{
  delete form.dataset.busy;
  submit.removeAttribute('aria-busy');
  sku.disabled=remove.disabled=add.disabled=submit.disabled=false;
 }
}
function credits(){
 const prices=table(['요금제','크레딧','금액'],cfg.catalog.education.map(x=>[x.name,x.quantity.toLocaleString(),money(x.price)]),{numeric:[1,2]});
 const purchase=stack(
  `<strong>보유 크레딧: ${me.credits}</strong>`+
  (me.sandbox_allowed?creditCart():
   helperText('실제 결제 준비 중'))+
  helperText('기본 말투 설정은 무료이며, AI 교육 및 모범 답변 교육은 크레딧이 차감됩니다.')
 );
 return pageTop('AI 교육 크레딧','고성능 AI 분석에만 사용량 차감')+billingTabs()+usageMeter()+
  card('일회성 충전',splitContent(prices,purchase,{balanced:true}));
}
function addonPriceTable(headers,rows){return `<div class="wrap addon-price-table"><table><thead><tr>${headers.map(h=>`<th>${e(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map((value,i)=>`<td data-label="${e(headers[i])}">${e(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`}
function addons(){return pageTop('추가 기능 요금표','필요한 기능만 선택 · 월 추가 구독')+billingTabs()+[...new Set(cfg.catalog.addons.map(x=>x.group))].map(g=>card(g,addonPriceTable(['기능','월 요금','상태'],cfg.catalog.addons.filter(x=>x.group===g).map(x=>[x.name,money(x.price),x.local?'로컬 구현':'준비 중'])))).join('')+card('추가 기능 패키지',addonPriceTable(['패키지','월 요금','포함 기능'],cfg.catalog.packages.map(p=>[p.name,money(p.price),p.includes.map(i=>cfg.catalog.addons.find(x=>x.id===i)?.name).join(', ')])))+card('알림톡·SMS 별도 충전',addonPriceTable(['유형','건수','가격'],cfg.catalog.messages.map(x=>[x.name,x.quantity,money(x.price)])))}

let staffDeskMember='',staffDeskThread='',staffDeskPending=null;
async function teamBrands(){return has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available&&!x.archived):[]}
function teamFields(m,brands){return label('관리 브랜드',select('team-brand',[['',me.settings.brand+' · 기본'],...brands.map(x=>[x.id,x.settings.brand])],m.agent||''))+label('권한',select('team-role',[['agent','상담 조회·답변·완료'],['viewer','상담 조회 전용']],m.role||'agent'))+'<label><input type="checkbox" id="team-assigned" '+(m.assigned_only===false||m.assigned_only===0?'':'checked')+'> 배정된 상담만 접근 가능</label>'}
async function teamPage(){const people=await api('/api/team'),brands=await teamBrands();return pageTop('직원 관리','사업주와 직원 계정을 분리합니다.')+card('직원 초청',me.public_access?stack(splitContent(
   stack(label('직원 이름',input('team-name'))+label('직원 Google 이메일',input('team-email','','email'))),
   stack(teamFields({},brands)),{balanced:true}
  )+`<div>${btn('초청 링크 발급','inviteTeam()','primary')}</div>`+
  helperText('초청받은 이메일로 Google 로그인해야 합니다. 링크는 7일 동안 유효하며 메일은 자동 발송하지 않습니다.')):'<p>유료 상담 또는 체험 이용 권한이 필요합니다.</p>')+card('직원 목록',people.map(m=>'<div class="line"><b>'+e(m.name)+'</b><p>'+e(m.email)+' · '+e(brands.find(x=>x.id===m.agent)?.settings.brand||(m.agent?'이전 브랜드':me.settings.brand))+'</p><small>'+e(({active:'활성',pending:'수락 대기',revoked:'회수됨'})[m.state])+' · '+e(m.role==='viewer'?'조회 전용':'상담 직원')+' · '+e(m.assigned_only?'배정 상담만':'브랜드 전체 상담')+'</small><div class="row">'+(m.state==='active'?btn('권한 변경',"editTeam('"+m.id+"')"):'')+(m.state!=='revoked'?btn('권한 회수',"revokeTeam('"+m.id+"')"):'')+'</div></div>').join('')||emptyState('등록된 직원이 없습니다.'))}
function teamPayload(){return {agent:val('team-brand'),role:val('team-role'),assigned_only:checked('team-assigned')}}
async function inviteTeam(){await act(async()=>{const r=await api('/api/team/invite',{...teamPayload(),name:val('team-name'),email:val('team-email')});modal('직원 초청 링크',label('복사해서 전달하세요',input('team-code',location.origin+r.accept_path))+copyButton('링크 복사','team-code','primary'));await render()})}
async function editTeam(id){await act(async()=>{const m=(await api('/api/team')).find(x=>x.id===id),brands=await teamBrands();if(!m)throw Error('직원 없음');modal('직원 권한 설정',teamFields(m,brands)+btn('저장',"saveTeamPermissions('"+id+"')",'primary'))})}
async function saveTeamPermissions(id){await act(async()=>{await api('/api/team/'+enc(id)+'/permissions',teamPayload());$('.modal')?.remove();render()})}
async function revokeTeam(id){if(!confirm('이 직원의 업체 상담 접근 권한을 회수할까요?'))return;await act(async()=>{await api('/api/team/'+enc(id)+'/revoke',{});render()})}
async function assignTeamMember(){const tid=threadId;await act(async()=>{const r=await api('/api/team/threads/'+enc(tid));modal('직원 계정 배정',label('실제 담당 직원',select('team-member',[['','미배정'],...r.people.map(m=>[m.id,m.name+(m.role==='viewer'?' · 조회 전용':'')])],r.member))+btn('배정 저장',"saveTeamAssignment('"+tid+"')",'primary'))})}
async function saveTeamAssignment(tid){await act(async()=>{await api('/api/team/threads/'+enc(tid),{member:val('team-member')});$('.modal')?.remove();toast('직원 계정 배정을 저장했습니다.');render()})}
async function staffDesk(){const invite=sessionStorage.getItem('csai-staff-invite'),members=await api('/api/staff/memberships');if(!members.some(m=>m.id===staffDeskMember)){staffDeskMember=members[0]?.id||'';staffDeskThread='';staffDeskPending=null}let html=pageTop('직원 상담함','허용된 업체·브랜드 및 배정 상담만 표시합니다.')+(invite?card('직원 초청 수락','<div class="ui-flow-body">'+helperText('초청받은 Google 이메일로 로그인했는지 확인하세요.')+flowActions(btn('초청 수락','acceptStaffInvite()','primary'),btn('취소',"sessionStorage.removeItem('csai-staff-invite');render()",'tertiary ui-flow-secondary'))+'</div>'):'');if(!members.length)return html+card('연결된 업체','<p>사업주에게 초청 링크를 받아 연결하세요.</p>');const m=members.find(x=>x.id===staffDeskMember),path='/api/staff/'+enc(m.id)+'/threads',threads=await api(path);if(!threads.some(t=>t.id===staffDeskThread)){staffDeskThread='';staffDeskPending=null}const t=staffDeskThread?await api(path+'/'+enc(staffDeskThread)):null;return html+card('근무 브랜드',select('staff-membership',members.map(x=>[x.id,x.brand+' · '+x.name]),m.id).replace('<select','<select onchange="switchStaffMembership(this.value)"')+'<p class="muted">'+e(m.role==='viewer'?'조회 전용':'상담 직원')+' · '+e(m.assigned_only?'배정 상담만':'브랜드 전체 상담')+'</p>'+btn('새로고침','render()'))+card('상담 목록',threads.map(x=>'<div class="line"><small>'+e(states[x.status]||x.status)+' · '+e(x.kind)+'</small><p>'+e(x.last||'새 상담')+'</p>'+btn('열기',"openStaffThread('"+x.id+"')")+'</div>').join('')||'<p>조회할 상담이 없습니다.</p>')+(t?card('상담 상세',t.messages.map(x=>photoBubble(x,'staff',t.id,m.id)).join('')+(t.can_reply?replyWithHistory('staff-desk-reply','직접 답변',t.messages)+actionGroup({keepSize:true},btn('답변 전송',"staffDeskWrite('reply')",'primary'),btn('완료 처리',"staffDeskWrite('resolve')"))+actionGroup({keepSize:true},(t.photos?btn('사진 첨부',"photoUploadModal('staff')"):''),(t.files?btn('영상·파일 첨부',"photoUploadModal('staff','file')"):''),(t.web_calls?btn('통화 요청 확인',"checkWebCall('staff')"):'')):'<p class="muted">조회 전용이거나 외부 채널 상담입니다.</p>')):'')}
function switchStaffMembership(id){staffDeskMember=id;staffDeskThread='';staffDeskPending=null;render()}
function openStaffThread(id){staffDeskThread=id;staffDeskPending=null;render()}
async function acceptStaffInvite(){await act(async()=>{const code=sessionStorage.getItem('csai-staff-invite');if(!code)throw Error('초청 링크 없음');const r=await api('/api/staff/accept',{code});sessionStorage.removeItem('csai-staff-invite');staffDeskMember=r.id;toast('직원으로 연결되었습니다.');render()})}
async function staffDeskWrite(action){const mid=staffDeskMember,tid=staffDeskThread,reply=action==='reply'?val('staff-desk-reply').trim():'';if(action==='reply'&&!reply)return toast('답변을 입력하세요.');if(!confirm(action==='reply'?'고객에게 답변을 전송할까요?':'상담을 완료 처리할까요?'))return;const key=JSON.stringify([mid,tid,action,reply]);if(staffDeskPending?.key!==key)staffDeskPending={key,client:crypto.randomUUID()};const client=staffDeskPending.client;await act(async()=>{await api('/api/staff/'+enc(mid)+'/threads/'+enc(tid),{action,reply,client});if(staffDeskPending?.client===client)staffDeskPending=null;toast('처리 완료');render()})}


let businessAgent='',commerceAgent='',commerceCustomerClient=null,commerceCustomerBusy=false;
const commerceChannels={smartstore:'네이버 스마트스토어',coupang:'쿠팡',cafe24:'카페24',imweb:'아임웹',shopify:'Shopify','11st':'11번가',gmarket:'G마켓',auction:'옥션',own:'자사몰',other:'기타'};
const commerceOrderStates={received:'신규 주문',preparing:'배송 준비',shipped:'배송 중',delivered:'배송 완료',cancelled:'취소'};
const commerceRequestKinds={delivery:'배송 문의',exchange:'교환 요청',return:'반품 요청',refund:'환불 요청',defect:'불량 접수',restock:'재입고 희망',other:'기타 문의'};
const commerceRequestStates={pending:'접수',review:'확인 중',resolved:'처리 완료',rejected:'반려'};
function scopeOptions(brands){return [['',me.settings.brand+' · 기본'],...brands.map(a=>[a.id,a.settings.brand])]}
function scopedUrl(path,agent){return path+'?agent='+enc(agent)}
function metric(name,value){
 return `<div class="dashboard-metric"><dt>${e(name)}</dt><dd>${e(String(value))}</dd></div>`;
}
function dashboardJump(p){if(p==='calendar'){calendarAgent=businessAgent;selectedDate=null;calendarRange=null;}if(p==='inbox'){inboxAgent=businessAgent;threadId=null;}if(p==='customers')crmAgent=businessAgent;if(p==='commerce')commerceAgent=businessAgent;go(p)}
async function businessDashboard(){
 const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(brand=>brand.available):[];
 if(businessAgent&&!brands.some(brand=>brand.id===businessAgent))businessAgent='';
 const r=await api(scopedUrl('/api/business-dashboard',businessAgent));
 const activity=[['오늘 신규 상담',r.new_threads],['직접 상담 대기',r.manual_pending]];
 if(r.calendar)activity.push(['오늘 예약',r.calendar.today],['예약 승인·변경 대기',r.calendar.pending+r.calendar.changes]);
 if(r.work)activity.push(['미처리 업무',Object.values(r.work).reduce((total,count)=>total+count,0)]);
 if(r.contacts!==null)activity.push(['등록 고객',r.contacts]);
 if(r.leads!==null)activity.push(['관심·구매 의사 고객',r.leads]);
 const sales=r.sales?[
  ['오늘 등록 주문',r.sales.orders_today],['배송 준비',r.sales.preparing],
  ['판매 문의 대기',r.sales.pending_requests],['오늘 등록 주문금액',money(r.sales.recorded_amount)],
 ]:[];
 const metrics=(items)=>'<dl class="dashboard-metrics">'+items.map(([name,value])=>metric(name,value)).join('')+'</dl>';
 const time=new Intl.DateTimeFormat('ko-KR',{timeZone:r.timezone,hour:'2-digit',minute:'2-digit',hour12:false});
 const schedule=r.calendar?.records.map(record=>`<div class="line"><b>${e(time.format(new Date(record.start)))}</b> · ${e(states[record.status]||record.status)}</div>`).join('');
 const shortcuts=[
  ['통합 상담함','messages-square',"dashboardJump('inbox')"],
  ['고객·업무','users-round',"dashboardJump('customers')"],
  ['판매 관리','shopping-bag',"dashboardJump('commerce')"],
  ['직원 관리','contact-badge',"go('team')"],
  ['채팅 첨부 설정','paperclip','photoSettingsModal()'],
  ['음성·영상통화 설정','video','webCallSettings()'],
 ];
 return pageTop('오늘의 사업 현황',r.date+' · '+r.timezone)+deskLinks()+
  `<div class="preview-brand">${brandSelect('business-brand',brands,businessAgent,'businessAgent=this.value;render()')}</div>`+
  `<section class="card app-card dashboard-setup-strip" aria-labelledby="dashboard-setup-title"><div class="dashboard-setup-copy"><h2 class="dashboard-setup-title" id="dashboard-setup-title">초기 세팅 대행</h2><p class="dashboard-setup-price"><span>기본 구축 50만 원~</span> · <span>맞춤 구축 100만 원~</span></p></div><button type="button" class="ui-button secondary dashboard-setup-action" onclick="openSetupConsultation()">상담 요청</button></section>`+
  card('상담 및 업무',metrics(activity))+
  (sales.length?card('판매 현황',metrics(sales)+'<p class="muted">판매 금액은 직접 등록한 주문의 합계이며 결제·정산 매출이 아닙니다.</p>'):'')+
  `<div class="grid dashboard-workspace">
   ${card('오늘 예약 일정',(schedule||`<p class="ui-empty">${r.calendar?'오늘 등록된 일정이 없습니다.':'예약 기능을 사용하면 상담에서 접수된 일정이 표시됩니다.'}</p>`)+btn('일정표 보기',"dashboardJump('calendar')"))}
   ${card('운영 바로가기',quickActions('운영 바로가기',shortcuts))}
  </div>`;
}
function commercePath(path=''){return scopedUrl('/api/commerce'+path,commerceAgent)}
async function commercePage(){const readOnly=!me.public_access;if(readOnly&&!freeFeaturePreview())return pageTop('온라인 판매 관리','상품·주문·판매 요청을 관리합니다.')+card('판매 관리','<p>유료 상담 또는 체험 계정에서 사용할 수 있습니다.</p>');let brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available):[];if(commerceAgent&&!brands.some(x=>x.id===commerceAgent))commerceAgent='';let archived=brands.some(x=>x.id===commerceAgent&&x.archived),r=readOnly?previewData().commerce:await api(commercePath());if(!readOnly&&me.sample_tools&&sharedPreviewEnabled()&&!commerceAgent){const demo=previewData().commerce;r={...r,products:r.products.concat(demo.products),orders:r.orders.concat(demo.orders),requests:r.requests.concat(demo.requests)};}let intro=(readOnly?previewNotice(null,'판매 관리 화면 체험'):'')+pageTop('온라인 판매 관리','판매처별 주문과 고객 문의를 한 곳에 기록합니다.')+brandSelect('commerce-brand',brands,commerceAgent,'commerceAgent=this.value;render()')+card('판매 관리 설정','<p class="muted">현재 수동 등록 방식입니다. 스마트스토어·쿠팡·자사몰과 실시간 주문·재고·배송 연동은 준비 중입니다. 실제 결제 및 환불은 판매처에서 처리하세요.</p>'+(archived?'<p>보관된 브랜드 · 조회만 가능</p>':btn(r.enabled?'판매 관리 끄기':'판매 관리 활성화',"toggleCommerce("+(!r.enabled)+")",'primary')));let edit=readOnly||r.enabled&&!archived;const commerceButton=(...args)=>readOnly?btn(args[0],/^(editCommerceProduct|editCommerceOrder|saveCommerceRequest)\(/.test(args[1])?args[1]:"showPreviewCommerceAction(this.textContent)",args[2]):btn(...args);return intro+card('상품·옵션·재고',(edit?actionGroup({keepSize:true},commerceButton('상품 등록','editCommerceProduct()','primary'),commerceButton('스마트스토어 상품 연동','smartstoreCatalogModal()'),commerceButton('쿠팡 상품 연동','coupangCatalogModal()')):'')+r.products.map(x=>'<div class="line'+(sampleRecord(x)?' sample-record':'')+'"><b>'+e(sampleTitle(x.name,sampleRecord(x)))+' · '+e(x.variant||'기본')+'</b><p>'+e(x.sku)+' · '+money(x.price)+' · 수동 재고 '+e(x.stock)+'개 · '+(x.published?'공개':'비공개')+'</p>'+(edit?commerceButton('수정',"editCommerceProduct('"+x.id+"')"):'')+'</div>').join(''))+card('주문 및 배송',(edit?actionGroup({keepSize:true},commerceButton('주문 등록','editCommerceOrder()','primary'),commerceButton('CSV 주문 가져오기','commerceImportModal()'),commerceButton('스마트스토어 API 확인','smartstoreProbeModal()'),commerceButton('스마트스토어 주문 조회','smartstoreOrderModal()'),commerceButton('스마트스토어 주문 자동 동기화','smartstoreOrderSyncModal()'),commerceButton('쿠팡 주문 연동','coupangModal()'),commerceButton('쿠팡 주문 자동 동기화','coupangOrderSyncModal()')):'')+r.orders.map(x=>'<div class="line'+(sampleRecord(x)?' sample-record':'')+'"><b>'+e(commerceChannels[x.channel])+' · '+e(x.reference)+'</b><p>'+e(sampleTitle(x.product,sampleRecord(x)))+' × '+e(x.quantity)+' · '+money(x.amount)+' · '+e(commerceOrderStates[x.state])+'</p><small>'+e([x.carrier,x.tracking].filter(Boolean).join(' '))+'</small>'+(edit?commerceButton('수정',"editCommerceOrder('"+x.id+"')"):'')+'</div>').join(''))+card('판매처 상품 Q&A',(edit?commerceButton('스마트스토어·쿠팡 문의 관리','marketplaceQnaModal()','primary'):'')+'<p>실시간 채팅과 별도인 상품 문의를 조회하고 승인 후 답변합니다.</p>')+card('교환·반품·환불·배송 문의',r.requests.map(x=>'<div class="line'+(sampleRecord(x)?' sample-record':'')+'"><b>'+e(commerceRequestKinds[x.kind])+' · '+e(commerceChannels[x.channel])+'</b><p>'+e(x.reference)+' · '+e(x.details)+'</p><small>'+e(commerceRequestStates[x.state])+'</small>'+commerceButton('상담 열기',"openCommerceThread('"+x.thread+"')")+(edit?select('commerce-request-'+x.id,Object.entries(commerceRequestStates),x.state)+commerceButton('처리 상태 저장',"saveCommerceRequest('"+x.id+"')"):'')+'</div>').join('')||'<p>접수된 요청이 없습니다.</p>')}
function showPreviewCommerceAction(name){modal(name,helperText('샘플 연결 체험입니다. 실제 판매처에 접속하거나 주문 데이터를 가져오지 않습니다.')+btn('샘플 연결 확인',"$('.modal')?.remove();toast('샘플 검증 완료 · 실제 연동 없음')",'primary'))}function previewUpsert(items,id,data){const item=items.find(x=>x.id===id);if(item)Object.assign(item,data);else items.push({...data,id:'preview-'+crypto.randomUUID()});}async function toggleCommerce(enabled){if(!me.public_access&&freeFeaturePreview()){previewData().commerce.enabled=enabled;render();return;}if(!requirePreviewAccess(null))return;await act(async()=>{await api(commercePath('/settings'),{enabled});render()})}
function openCommerceThread(id){inboxAgent=commerceAgent;threadId=id;go('inbox')}
async function editCommerceProduct(id=''){await act(async()=>{let r=(!me.public_access&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))?previewData().commerce:await api(commercePath()),x=r.products.find(z=>z.id===id)||{};if(id&&!x.id)throw Error('상품 없음');modal('상품 등록·수정',label('SKU (상품·옵션별 고유 코드)',input('cp-sku',x.sku))+label('상품명',input('cp-name',x.name))+label('옵션',input('cp-variant',x.variant))+label('원화 가격',input('cp-price',x.price??0,'number'))+label('수동 재고',input('cp-stock',x.stock??0,'number'))+label('HTTPS 판매 링크',input('cp-url',x.url))+label('고객에게 공개할 상품 설명',ta('cp-description',x.description))+'<label><input type="checkbox" id="cp-published" '+(x.published?'checked':'')+'> 고객 상품 목록·AI 상담에 공개</label>'+btn('저장',"saveCommerceProduct('"+id+"')",'primary'))})}
async function saveCommerceProduct(id){if((!me.public_access&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))){if(!val('cp-name').trim())return toast('상품명을 입력하세요.');previewUpsert(previewData().commerce.products,id,{sku:val('cp-sku'),name:'샘플 · '+val('cp-name').replace(/^샘플 · /,''),variant:val('cp-variant'),price:Number(val('cp-price')),stock:Number(val('cp-stock')),url:val('cp-url'),description:val('cp-description'),published:checked('cp-published')});$('.modal')?.remove();render();return;}await act(async()=>{await api(commercePath('/products'),{id,sku:val('cp-sku'),name:val('cp-name'),variant:val('cp-variant'),price:Number(val('cp-price')),stock:Number(val('cp-stock')),url:val('cp-url'),description:val('cp-description'),published:checked('cp-published')});$('.modal')?.remove();render()})}
async function editCommerceOrder(id=''){await act(async()=>{let r=(!me.public_access&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))?previewData().commerce:await api(commercePath()),x=r.orders.find(z=>z.id===id)||{};if(id&&!x.id)throw Error('주문 없음');modal('주문 등록·수정',label('판매처',select('co-channel',Object.entries(commerceChannels),x.channel||'smartstore'))+label('판매처 주문번호',input('co-ref',x.reference))+label('상품·옵션',input('co-product',x.product))+label('수량',input('co-qty',x.quantity??1,'number'))+label('주문 총액 (수동 기록)',input('co-amount',x.amount??0,'number'))+label('상태',select('co-state',Object.entries(commerceOrderStates),x.state||'received'))+label('택배사',input('co-carrier',x.carrier))+label('운송장 번호',input('co-tracking',x.tracking))+btn('저장',"saveCommerceOrder('"+id+"')",'primary'))})}
async function saveCommerceOrder(id){if((!me.public_access&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))){if(!val('co-product').trim())return toast('상품명을 입력하세요.');previewUpsert(previewData().commerce.orders,id,{channel:val('co-channel'),reference:val('co-ref'),product:'샘플 · '+val('co-product').replace(/^샘플 · /,''),quantity:Number(val('co-qty')),amount:Number(val('co-amount')),state:val('co-state'),carrier:val('co-carrier'),tracking:val('co-tracking')});$('.modal')?.remove();render();return;}await act(async()=>{await api(commercePath('/orders'),{id,channel:val('co-channel'),reference:val('co-ref'),product:val('co-product'),quantity:Number(val('co-qty')),amount:Number(val('co-amount')),state:val('co-state'),carrier:val('co-carrier'),tracking:val('co-tracking')});$('.modal')?.remove();render()})}
async function saveCommerceRequest(id){if((!me.public_access&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))){const item=previewData().commerce.requests.find(x=>x.id===id);if(item)item.state=val('commerce-request-'+id);render();return;}await act(async()=>{await api(commercePath('/requests/'+enc(id)),{state:val('commerce-request-'+id)},'PATCH');render()})}
async function commerceCustomerModal(){await act(async()=>{const token=await getChatSession(),r=await api('/api/customer/commerce/'+enc(token));commerceCustomerClient=crypto.randomUUID();modal('상품 및 주문 문의',r.products.map(p=>'<div class="line"><b>'+e(p.name)+' '+e(p.variant)+'</b><p>'+money(p.price)+' · '+e(p.description)+'</p>'+(p.url?'<a href="'+e(p.url)+'" target="_blank" rel="noopener noreferrer">판매처 보기</a>':'')+'</div>').join('')+label('요청 유형',select('cc-kind',Object.entries(commerceRequestKinds),'delivery'))+label('판매처',select('cc-channel',Object.entries(commerceChannels),'smartstore'))+label('주문번호 (재입고·기타 문의 제외)',input('cc-ref'))+label('문의 내용',ta('cc-details'))+'<p class="muted">접수만 진행하며 실제 배송·환불·교환은 판매처에서 확인해야 합니다. 카드번호 등 결제정보를 입력하지 마세요.</p>'+btn('확인 및 접수','submitCommerceCustomer()','primary'))})}
async function submitCommerceCustomer(){if(commerceCustomerBusy)return;await act(async()=>{const token=chatSession,body={token,client:commerceCustomerClient,kind:val('cc-kind'),channel:val('cc-channel'),reference:val('cc-ref'),details:val('cc-details'),confirmed:true};commerceCustomerBusy=true;try{await api('/api/customer/commerce',body);$('.modal')?.remove();toast('판매 문의가 접수되었습니다.')}finally{commerceCustomerBusy=false}})}


let photoUploadBusy=false,photoUploadAttempt=null;
function photoBubble(m,mode,tid='',mid=''){if(m.attachment)return '<div class="bubble '+(m.role==='user'?'user':'')+'"><p>'+e(m.attachment.name)+'</p>'+btn('파일 확인',"openChatPhoto('"+m.attachment.id+"','"+mode+"','"+tid+"','"+mid+"')")+'</div>';if(!m.photo)return bubble(m.role,m.body,true);return '<div class="bubble '+(m.role==='user'?'user':'')+'"><p>사진 첨부</p>'+btn('사진 보기',"openChatPhoto('"+m.photo+"','"+mode+"','"+tid+"','"+mid+"')")+'</div>'}
async function openChatPhoto(id,mode,tid,mid){await act(async()=>{let r=mode==='customer'?await api('/api/customer/photos/read',{token:chatSession,id}):await api((mode==='staff'?'/api/staff/'+enc(mid)+'/threads/':'/api/inbox/')+enc(tid)+'/photos/'+enc(id));if(!r.data)throw Error('첨부 형식 오류');if(r.mime==='image/jpeg'){modal('첨부 사진','<img style="max-width:100%;height:auto" alt="첨부 사진" src="data:image/jpeg;base64,'+e(r.data)+'">');return}if(!['application/pdf','text/plain','video/mp4','video/webm'].includes(r.mime))throw Error('지원하지 않는 파일');pendingChatDownload=r;modal('첨부 파일', '<p>'+e(r.name)+'</p><p class="muted">외부 파일입니다. 악성코드 검사가 완료되지 않았으므로 신뢰할 수 있는 파일만 다운로드하세요.</p>'+btn('파일 다운로드','downloadChatFile()','primary'))})}
let pendingChatDownload=null;
function downloadChatFile(){const r=pendingChatDownload;if(!r)return;const bytes=Uint8Array.from(atob(r.data),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:'application/octet-stream'}));const a=document.createElement('a');a.href=url;a.download=r.name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);pendingChatDownload=null}
async function photoSettingsModal(){await act(async()=>{const agent=businessAgent,r=await api(scopedUrl('/api/chat-photos/settings',agent));modal('채팅 첨부 설정','<p>첨부 파일은 담당자 확인으로 전환합니다. 사진 1MB, PDF·TXT·MP4·WebM 4MB, 상담당 총 20개, 계정당 총 50MB입니다.</p><label><input type="checkbox" id="photo-enabled" '+(r.enabled?'checked':'')+'> 사진 첨부 허용</label><label><input type="checkbox" id="file-enabled" '+(r.files_enabled?'checked':'')+'> 영상·파일 첨부 허용</label>'+btn('저장',"savePhotoSettings('"+agent+"')",'primary'))})}
async function savePhotoSettings(agent){await act(async()=>{await api(scopedUrl('/api/chat-photos/settings',agent),{enabled:checked('photo-enabled'),files_enabled:checked('file-enabled')});$('.modal')?.remove();toast('설정을 저장했습니다.');render()})}
function photoUploadModal(mode,kind='photo'){photoUploadAttempt={mode,kind,tid:mode==='staff'?staffDeskThread:threadId,mid:staffDeskMember,token:chatSession,client:crypto.randomUUID()};modal(kind==='photo'?'사진 첨부':'영상·파일 첨부','<p>'+(kind==='photo'?'JPG·PNG·WebP 사진 1장 (1MB 이하).':'PDF·TXT·MP4·WebM 파일 1개 (4MB 이하).')+' 민감한 정보는 가려 주세요. 담당자가 직접 확인합니다.</p>'+fileUpload('chat-photo-file',{accept:kind==='photo'?'image/jpeg,image/png,image/webp':'.pdf,.txt,.mp4,.webm'})+actionFooter([btn('확인 및 전송','sendChatPhoto()','primary')]))}
async function sendChatPhoto(){if(photoUploadBusy||sending)return;await act(async()=>{const a=photoUploadAttempt,f=$('#chat-photo-file')?.files[0];if(!a||!f||f.size>(a.kind==='photo'?1000000:4000000))throw Error('허용 용량 이내의 첨부 파일을 선택하세요.');photoUploadBusy=true;try{const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('사진 읽기 실패'));reader.readAsDataURL(f)});if(a.mode==='customer'){if(a.token&&a.token!==chatSession)throw Error('상담이 변경되었습니다.');const token=await getChatSession();await api('/api/customer/photos',{token,client:a.client,data,kind:a.kind,name:f.name});const ms=await api('/api/session/'+enc(token)+'/messages');if(chatSession===token){chatMessages=ms;$('#messages').innerHTML=welcomeMarkup(pub)+ms.map(m=>photoBubble(m,'customer')).join('');$('#messages').scrollTop=$('#messages').scrollHeight;}}else{const path=(a.mode==='staff'?'/api/staff/'+enc(a.mid)+'/threads/':'/api/inbox/')+enc(a.tid)+'/photos';await api(path,{client:a.client,data,kind:a.kind,name:f.name});await render()}$('.modal')?.remove();photoUploadAttempt=null;toast('첨부 파일을 전송했습니다.')}finally{photoUploadBusy=false}})}


let rtcCall=null,rtcBusy=false,rtcIncoming=null;
function webCallPath(mode,tid,mid){return (mode==='staff'?'/api/staff/'+enc(mid)+'/threads/':'/api/inbox/')+enc(tid)+'/web-call'}
async function webCallSettings(){await act(async()=>{const agent=businessAgent,r=await api(scopedUrl('/api/web-calls/settings',agent));modal('음성·영상통화 설정','<p>고객이 요청하고 담당자가 수락하는 자체 웹 통화입니다. 전화번호 연결이나 녹음은 지원하지 않습니다. 일부 네트워크에서는 연결되지 않을 수 있습니다.</p>'+(r.available?btn(r.enabled?'통화 끄기':'통화 켜기',"saveWebCallSetting('"+agent+"',"+(!r.enabled)+")",'primary'):'<p>실제 연결 검증 전 서버 통화 기능이 비활성화되어 있습니다.</p>'))})}
async function saveWebCallSetting(agent,enabled){await act(async()=>{await api(scopedUrl('/api/web-calls/settings',agent),{enabled});$('.modal')?.remove();render()})}
function chooseWebCall(){if(rtcCall||rtcBusy)return toast('이미 통화 중입니다.');modal('담당자 연결','<p>통화 요청 전에 마이크 또는 카메라 권한을 확인합니다. 담당자가 수락해야 연결됩니다.</p>'+actionGroup({keepSize:true},btn('음성통화 요청',"startWebCall('audio')",'primary'),btn('영상통화 요청',"startWebCall('video')")))}
function callPanel(c){$('#web-call-panel')?.remove();const n=document.createElement('section');n.id='web-call-panel';n.className='card';n.style.cssText='position:fixed;z-index:10000;bottom:12px;right:12px;left:auto;width:min(340px,calc(100vw - 24px));max-height:75vh;overflow:auto;box-shadow:0 10px 40px #0005';n.innerHTML='<h3>'+e(c.kind==='video'?'영상통화':'음성통화')+'</h3><p id="rtc-status">연결 준비 중</p><video id="rtc-remote" autoplay playsinline '+(c.kind==='audio'?'style="display:none"':'style="width:100%;max-height:240px"')+'></video><video id="rtc-local" autoplay muted playsinline '+(c.kind==='audio'?'style="display:none"':'style="width:90px"')+'></video><div class="row">'+btn('마이크 끄기','toggleCallMic()')+(c.kind==='video'?btn('카메라 끄기','toggleCallCamera()'):'')+btn('통화 종료','endWebCall()','primary')+'</div>';document.body.append(n);$('#rtc-local').srcObject=c.stream;$('#rtc-remote').srcObject=c.remote}
function rtcStatus(s){const n=$('#rtc-status');if(n)n.textContent=s}
function toggleCallMic(){if(!rtcCall)return;rtcCall.stream.getAudioTracks().forEach(t=>t.enabled=!t.enabled);rtcStatus(rtcCall.stream.getAudioTracks()[0]?.enabled?'마이크 켜짐':'마이크 꺼짐')}
function toggleCallCamera(){if(!rtcCall)return;rtcCall.stream.getVideoTracks().forEach(t=>t.enabled=!t.enabled);rtcStatus(rtcCall.stream.getVideoTracks()[0]?.enabled?'카메라 켜짐':'카메라 꺼짐')}
async function makeRtc(kind){if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia||!window.RTCPeerConnection)throw Error('HTTPS와 WebRTC 지원 브라우저가 필요합니다.');const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:kind==='video'});let pc;try{pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});const c={kind,stream,pc,remote:new MediaStream(),id:'',timer:null,polling:false,closed:false};stream.getTracks().forEach(t=>pc.addTrack(t,stream));pc.ontrack=e=>{if(!c.closed&&!c.remote.getTracks().some(t=>t.id===e.track.id))c.remote.addTrack(e.track)};pc.onconnectionstatechange=()=>{if(rtcCall!==c)return;const state=pc.connectionState;if(state==='connected')rtcStatus('통화 연결됨');else if(state==='failed'){rtcStatus('연결 실패 · 네트워크 확인');endWebCall()}else if(state==='disconnected')rtcStatus('연결 불안정');};return c}catch(e){stream.getTracks().forEach(t=>t.stop());throw e}}
async function gatherRtc(pc){if(pc.iceGatheringState==='complete')return;await new Promise(resolve=>{const done=()=>{pc.removeEventListener('icegatheringstatechange',check);clearTimeout(timer);resolve()};const check=()=>{if(pc.iceGatheringState==='complete')done()};const timer=setTimeout(done,8000);pc.addEventListener('icegatheringstatechange',check);check()})}
async function rtcApi(c,action,extra={}){return c.mode==='customer'?api('/api/customer/web-calls',{token:c.token,id:c.id,action,...extra}):api(webCallPath(c.mode,c.tid,c.mid),{id:c.id,key:c.key,action,...extra})}
function cleanupRtc(c){if(!c)return;c.closed=true;clearInterval(c.timer);c.stream?.getTracks().forEach(t=>t.stop());c.remote?.getTracks().forEach(t=>t.stop());c.pc?.close();if(rtcCall===c){rtcCall=null;$('#web-call-panel')?.remove()}}
async function endWebCall(){const c=rtcCall;if(!c)return;cleanupRtc(c);if(c.id)try{await rtcApi(c,'end')}catch{}}
function startRtcPoll(c){c.timer=setInterval(async()=>{if(c.closed||c.polling)return;c.polling=true;try{const r=await rtcApi(c,'status');if(c.closed)return;if(['ended','expired'].includes(r.state)){cleanupRtc(c);toast(r.state==='expired'?'통화 요청이 만료되었습니다.':'통화가 종료되었습니다.');return}if(c.mode==='customer'&&r.state==='answered'&&r.answer&&!c.pc.remoteDescription){await c.pc.setRemoteDescription({type:'answer',sdp:r.answer});rtcStatus('담당자 수락 · 연결 중')}else if(r.state==='claimed')rtcStatus('담당자가 연결 중입니다.');}catch(e){cleanupRtc(c);toast('통화 연결 권한 또는 네트워크 오류')}finally{c.polling=false}},2500)}
async function startWebCall(kind){if(rtcCall||rtcBusy)return;rtcBusy=true;let c;try{const token=await getChatSession();c=await makeRtc(kind);c.mode='customer';c.token=token;rtcCall=c;$('.modal')?.remove();callPanel(c);await c.pc.setLocalDescription(await c.pc.createOffer());await gatherRtc(c.pc);if(c.closed)throw Error('통화가 종료되었습니다.');const r=await rtcApi(c,'start',{kind,confirmed:true,offer:c.pc.localDescription.sdp});c.id=r.id;if(c.closed){await rtcApi(c,'end');return}rtcStatus('담당자 수락 대기 · 최대 2분');startRtcPoll(c)}catch(e){cleanupRtc(c);toast(e.message)}finally{rtcBusy=false}}
async function checkWebCall(mode){if(rtcCall||rtcBusy)return toast('이미 통화 중입니다.');await act(async()=>{const tid=mode==='staff'?staffDeskThread:threadId,mid=staffDeskMember,r=await api(webCallPath(mode,tid,mid),{action:'list'});if(!r.call)return toast('대기 중인 통화 요청이 없습니다.');if(r.call.state!=='ringing')return toast('다른 담당자가 처리 중이거나 통화 중입니다.');rtcIncoming={mode,tid,mid,...r.call};modal('고객 통화 요청','<p>'+e(r.call.kind==='video'?'영상통화 요청':'음성통화 요청')+'</p>'+actionGroup({keepSize:true},btn('수락','acceptWebCall()','primary'),btn('거절','declineWebCall()')))})}
async function declineWebCall(){const c=rtcIncoming;if(!c)return;await act(async()=>{await api(webCallPath(c.mode,c.tid,c.mid),{action:'decline',id:c.id});$('.modal')?.remove();rtcIncoming=null;toast('통화 요청을 거절했습니다.')})}
async function acceptWebCall(){if(rtcCall||rtcBusy||!rtcIncoming)return;rtcBusy=true;const incoming=rtcIncoming;let c,claimed=false;try{c=await makeRtc(incoming.kind);Object.assign(c,{mode:incoming.mode,tid:incoming.tid,mid:incoming.mid,id:incoming.id,key:crypto.randomUUID()});rtcCall=c;$('.modal')?.remove();callPanel(c);const r=await rtcApi(c,'claim',{confirmed:true});claimed=true;if(c.closed){await rtcApi(c,'end');return}await c.pc.setRemoteDescription({type:'offer',sdp:r.offer});await c.pc.setLocalDescription(await c.pc.createAnswer());await gatherRtc(c.pc);if(c.closed){await rtcApi(c,'end');return}await rtcApi(c,'answer',{answer:c.pc.localDescription.sdp});rtcStatus('고객과 연결 중');startRtcPoll(c);rtcIncoming=null}catch(e){cleanupRtc(c);if(claimed)try{await rtcApi(c,'end')}catch{}toast(e.message)}finally{rtcBusy=false}}
window.addEventListener('pagehide',()=>{if(rtcCall)cleanupRtc(rtcCall)});


async function telegramModal(agent=''){await act(async()=>{const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available&&!x.archived):[],r=await api(scopedUrl('/api/telegram',agent));modal('텔레그램 봇 연결',brandSelect('telegram-brand',brands,agent,'telegramModal(this.value)')+'<p>BotFather에서 생성한 전용 봇을 연결합니다. 기존 다른 웹훅을 덮어쓰지 않습니다. 개인 텍스트 상담만 지원합니다.</p><p>'+e(r.active?'활성화됨':r.saved?'저장됨 · 미활성':'미연결')+'</p>'+(r.available&&!r.active?label('봇 토큰',input('telegram-token','','password'))+btn('봇 인증 및 웹훅 등록',"connectTelegram('"+agent+"')",'primary'):'')+(r.active?btn('연결 중지',"pauseTelegram('"+agent+"')"):'')+(!r.available?'<p class="muted">실제 운영 인증 전 서버 기능 비활성화</p>':'')+'<p class="muted">중지는 CSAI 수신·발송을 막습니다. 텔레그램 측 웹훅은 유지됩니다.</p>')})}
async function connectTelegram(agent){if(!confirm('이 봇의 웹훅을 CSAI에 등록할까요?'))return;await act(async()=>{await api(scopedUrl('/api/telegram/connect',agent),{token:val('telegram-token'),confirmed:true});telegramModal(agent)})}
async function pauseTelegram(agent){await act(async()=>{await api(scopedUrl('/api/telegram/pause',agent),{});telegramModal(agent)})}


let orderImportPreview=null;
function commerceImportModal(){orderImportPreview=null;modal('공통 주문 CSV 가져오기','<p>판매처에서 내보낸 파일을 아래 공통 열 순서로 정리해 주세요. 기존 주문번호는 덮어쓰지 않습니다. 주문번호는 판매처별 상품주문 단위로 고유해야 합니다.</p>'+btn('양식 다운로드','downloadCommerceTemplate()')+''+fileUpload('order-import-file',{accept:'.csv,text/csv',onChange:'loadCommerceCsv(this)'})+label('CSV 내용',ta('order-import-csv'))+btn('검토','previewCommerceImport()','primary')+'<div id="order-import-preview"></div>')}
function downloadCommerceTemplate(){const csv='channel,reference,product,quantity,amount,state,carrier,tracking\r\nsmartstore,EXAMPLE-001,상품명,1,10000,received,,\r\n';const url=URL.createObjectURL(new Blob(['\uFEFF',csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='csai-orders-template.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
async function loadCommerceCsv(field){await act(async()=>{const file=field.files[0];if(!file||file.size>750000)throw Error('CSV 파일 용량을 확인하세요.');$('#order-import-csv').value=await file.text();orderImportPreview=null;$('#order-import-preview').innerHTML=''})}
async function previewCommerceImport(){await act(async()=>{const csv=val('order-import-csv'),agent=commerceAgent,r=await api(scopedUrl('/api/commerce/import-orders',agent),{csv});orderImportPreview={csv,agent,checksum:r.checksum};$('#order-import-preview').innerHTML='<p>총 '+e(r.total)+'건 · 신규 '+e(r.new)+'건 · 기존 중복 '+e(r.duplicates)+'건</p>'+btn('신규 주문 등록','applyCommerceImport()','primary')})}
async function applyCommerceImport(){await act(async()=>{const p=orderImportPreview;if(!p||p.agent!==commerceAgent||p.csv!==val('order-import-csv'))throw Error('내용이 변경되었습니다. 다시 검토하세요.');if(!confirm('신규 주문을 등록할까요?'))return;const r=await api(scopedUrl('/api/commerce/import-orders',p.agent),{csv:p.csv,checksum:p.checksum,confirmed:true});orderImportPreview=null;$('.modal')?.remove();toast(r.imported+'건 등록 · 중복 '+r.duplicates+'건 제외');render()})}
async function smartstoreProbeModal(){await act(async()=>{const agent=commerceAgent,r=await api(scopedUrl('/api/commerce/provider-status',agent));modal('스마트스토어 API 연결 확인','<p>커머스API 앱의 본인 판매자(SELF) 인증 정보와 실제 주문번호로 상품주문 조회 권한만 검사합니다. 인증 정보는 저장하지 않으며 자동 동기화나 주문 수정은 하지 않습니다.</p><p><a href="https://apicenter.commerce.naver.com/docs/auth" target="_blank" rel="noopener noreferrer">공식 인증 안내</a></p>'+(r.smartstore_probe?label('Client ID',input('ss-id'))+label('Client Secret',input('ss-secret','','password'))+label('실제 주문번호',input('ss-order'))+btn('읽기 전용 인증 확인',"runSmartstoreProbe('"+agent+"')",'primary'):'<p class="muted">실제 인증 검증 전 서버 기능이 비활성화되어 있습니다.</p>'))})}
async function runSmartstoreProbe(agent){if(!confirm('네이버 공식 API에 인증 및 주문 조회 요청을 보낼까요?'))return;await act(async()=>{const client_id=val('ss-id'),client_secret=val('ss-secret'),order_id=val('ss-order');$('#ss-secret').value='';const r=await api(scopedUrl('/api/commerce/smartstore/probe',agent),{client_id,client_secret,order_id,confirmed:true});modal('인증 조회 결과','<p>상품주문 '+e(r.product_order_count)+'건 조회 확인. 자동 동기화는 아직 연결되지 않았습니다.</p>')})}


async function smartstoreCatalogModal(){await act(async()=>{const agent=commerceAgent,r=await api(scopedUrl('/api/commerce/smartstore',agent));modal('스마트스토어 상품 자동 수집','<p>상품 목록은 API로 수집하고 상담 시 관련 상품 최대 3개만 검색합니다. AI 교육 크레딧은 차감하지 않습니다. 최대 2,000개, 6시간 주기이며 상세페이지 이미지 분석·옵션별 실시간 재고는 지원하지 않습니다.</p><p>'+e(r.state)+' · '+e(r.count)+'개 · '+(r.last_sync?e(new Date(r.last_sync*1000).toLocaleString('ko-KR')):'동기화 전')+'</p><p>'+e(r.error)+'</p>'+(r.available?(r.active?actionGroup({keepSize:true},btn('동기화 요청',"queueSmartstore('"+agent+"')",'primary'),btn('상품 목록',"viewSmartstoreProducts('"+agent+"',1)"),btn('연결 해제',"disconnectSmartstore('"+agent+"')")):label('Client ID',input('ss-sync-id'))+label('Client Secret',input('ss-sync-secret','','password'))+btn('연결 및 자동 수집 신청',"connectSmartstore('"+agent+"')",'primary')):'<p>서버 및 판매자 권한 검증 전 기능 비활성화</p>')+btn('상태 새로고침','smartstoreCatalogModal()'))})}
async function connectSmartstore(agent){if(!confirm('암호화된 인증 정보를 저장하고 6시간마다 판매 상품 목록을 조회할까요?'))return;await act(async()=>{const client_id=val('ss-sync-id'),client_secret=val('ss-sync-secret');$('#ss-sync-secret').value='';await api(scopedUrl('/api/commerce/smartstore/connect',agent),{client_id,client_secret,confirmed:true});smartstoreCatalogModal()})}
async function queueSmartstore(agent){await act(async()=>{await api(scopedUrl('/api/commerce/smartstore/sync',agent),{});toast('동기화 요청을 등록했습니다. 워커가 처리합니다.');smartstoreCatalogModal()})}
async function disconnectSmartstore(agent){if(!confirm('연결 및 수집된 상품 목록을 삭제할까요?'))return;await act(async()=>{await api(scopedUrl('/api/commerce/smartstore/disconnect',agent),{});smartstoreCatalogModal()})}
async function viewSmartstoreProducts(agent,page){await act(async()=>{const r=await api(scopedUrl('/api/commerce/smartstore/products',agent)+'&page='+page);modal('수집된 상품 목록',r.products.map(p=>'<div class="line"><b>'+e(p.name)+'</b><p>상품번호 '+e(p.id)+' · '+money(p.price)+' · 조회 당시 재고 '+e(p.stock)+'개</p>'+btn('상세정보·AI 교육',"smartstoreProductDetail('"+agent+"','"+p.id+"')")+'</div>').join('')+actionGroup({keepSize:true},(page>1?btn('이전',"viewSmartstoreProducts('"+agent+"',"+(page-1)+")"):''),(page*100<r.count?btn('다음',"viewSmartstoreProducts('"+agent+"',"+(page+1)+")"):''),btn('연결 관리','smartstoreCatalogModal()')))})}
async function smartstoreOrderModal(){await act(async()=>{const agent=commerceAgent,r=await api(scopedUrl('/api/commerce/smartstore',agent));modal('스마트스토어 실시간 주문 조회','<p>사업주 전용입니다. 고객의 본인 확인 없이 주문 정보를 자동 제공하지 않습니다. 네이버에서 발급한 상품주문번호를 입력하세요.</p>'+(r.available&&r.active?label('상품주문번호',input('ss-lookup-ref'))+btn('조회',"lookupSmartstoreOrder('"+agent+"')",'primary'):'<p>먼저 스마트스토어 연동을 활성화하세요.</p>'))})}
async function lookupSmartstoreOrder(agent){await act(async()=>{const r=await api(scopedUrl('/api/commerce/smartstore/order-status',agent),{reference:val('ss-lookup-ref'),confirmed:true});modal('주문·배송 조회 결과','<p>'+e(r.product)+'</p><p>상품주문 '+e(r.reference)+'</p><p>주문 상태 '+e(r.status)+' · 배송 상태 '+e(r.delivery_status||'미제공')+'</p><p>'+e(r.carrier)+' '+e(r.tracking)+'</p><p class="muted">조회 시점 '+e(new Date(r.queried_at*1000).toLocaleString('ko-KR'))+'</p>')})}


let productEducationBusy=false;
async function smartstoreProductDetail(agent,pid){await act(async()=>{const r=await api(scopedUrl('/api/commerce/smartstore/products/'+enc(pid)+'/detail',agent)),d=r.content;modal('상품 상세정보·AI 교육','<p><strong>'+e(r.product)+'</strong></p><p>상세 텍스트 수집·상담 검색은 교육 크레딧 무료. 선택적으로 AI 분석을 실행할 때만 기존 교육 크레딧이 차감됩니다.</p>'+btn('상세정보 가져오기·갱신',"collectSmartstoreDetail('"+agent+"','"+pid+"')",'primary')+(r.collected?'<p>'+e(r.educated?'상품별 교육 승인됨':'AI 교육 미실행')+(r.stale?' · 갱신 필요':'')+'</p><p class="muted">이미지 '+e(d.image_count)+'개 · 원격 이미지 자동 분석 없음'+(d.truncated?' · 일부 텍스트 잘림':'')+'</p><pre style="white-space:pre-wrap;max-height:220px;overflow:auto">'+e(d.text||'상세 텍스트 없음')+'</pre><p>'+e(JSON.stringify(d.fees))+'</p><p>이미 교육센터에 등록한 동일 브랜드의 이미지 자료를 선택할 수 있습니다.</p>'+btn('AI 교육 비용 확인',"quoteProductEducation('"+agent+"','"+pid+"')"):'')+btn('상품 목록',"viewSmartstoreProducts('"+agent+"',1)"))})}
async function collectSmartstoreDetail(agent,pid){await act(async()=>{await api(scopedUrl('/api/commerce/smartstore/products/'+enc(pid)+'/detail',agent),{});smartstoreProductDetail(agent,pid)})}
async function quoteProductEducation(agent,pid){await act(async()=>{const files=await api('/api/files?agent='+enc(agent));modal('상품별 AI 교육 견적','<p>상품 상세정보의 AI 분석입니다. 이미지가 필요하면 교육센터에 먼저 등록한 자료를 최대 4개 선택하세요. 이미지 없이 텍스트 분석도 가능합니다.</p>'+files.map(x=>'<label><input type="checkbox" class="product-image-source" value="'+e(x.id)+'"> '+e(x.name)+'</label>').join('')+'<label><input type="checkbox" id="product-education-consent"> 공개 상품 자료를 교육에 이용할 권한이 있습니다.</label>'+btn('크레딧 견적',"estimateProductEducation('"+agent+"','"+pid+"')",'primary'))})}
async function estimateProductEducation(agent,pid){await act(async()=>{const files=[...document.querySelectorAll('.product-image-source:checked')].map(x=>x.value);if(!checked('product-education-consent'))throw Error('자료 이용 권한 확인 필요');const r=await api(scopedUrl('/api/commerce/smartstore/products/'+enc(pid)+'/education',agent),{confirmed:true,files});modal('AI 상품 교육 비용 확인','<p>'+e(r.product)+' · 최대 '+e(r.maxCredits)+' C 예약 · 현재 '+e(r.credits)+' C</p><p>실제 사용량만 차감합니다. 수집·갱신 자체는 무료이며 자동 재교육하지 않습니다.</p>'+(r.enough?btn('분석 시작',"runProductEducation('"+r.id+"','"+agent+"','"+pid+"')",'primary'):btn('크레딧 충전',"$('.modal')?.remove();go('credits')")))})}
async function runProductEducation(id,agent,pid){if(productEducationBusy)return;productEducationBusy=true;try{await act(async()=>{const r=await api('/api/training/'+enc(id)+'/run',{}),k=r.result;await refresh();modal('상품 AI 교육 결과','<p>'+e(r.cost)+' C 사용 · 이 상품에만 반영합니다.</p>'+k.rules.map(x=>'<p>'+e(x)+'</p>').join('')+k.faq.map(x=>'<div class="line"><b>'+e(x.q)+'</b><p>'+e(x.a)+'</p></div>').join('')+btn('검토 후 상품에 반영',"publishProductEducation('"+id+"','"+agent+"','"+pid+"')",'primary'))})}finally{productEducationBusy=false}}
async function publishProductEducation(id,agent,pid){await act(async()=>{await api('/api/training/'+enc(id)+'/publish',{});toast('해당 상품에만 교육 결과를 반영했습니다.');smartstoreProductDetail(agent,pid)})}


async function ownerOrderAccess(){await act(async()=>{const tid=threadId,r=await api('/api/inbox/'+enc(tid)+'/order-access');modal('고객 주문 조회 승인','<p>스마트스토어에서 구매자와 주문 소유권을 확인하고, 인증 코드는 구매자에게 기존 확인된 연락 경로로 별도 전달하세요. 이 상담창에는 코드를 보내지 마세요.</p>'+r.grants.map(x=>'<p>'+e(x.reference)+' · '+e(x.state)+' · '+e(new Date(x.expires*1000).toLocaleString('ko-KR'))+'</p>').join('')+(r.available?label('상품주문번호',input('order-grant-ref'))+'<label><input type="checkbox" id="order-grant-verified"> 구매자의 신원·해당 주문 소유권을 별도 신뢰 경로에서 확인했습니다.</label>'+btn('일회용 인증 코드 발급',"issueOrderAccess('"+tid+"')",'primary'):'<p>스마트스토어 연결 설정이 필요합니다.</p>')+btn('미사용 승인 취소',"revokeOrderAccess('"+tid+"')"))})}
async function issueOrderAccess(tid){await act(async()=>{if(!checked('order-grant-verified'))throw Error('구매자 확인이 필요합니다.');const r=await api('/api/inbox/'+enc(tid)+'/order-access',{reference:val('order-grant-ref'),verified_outside_chat:true,confirmed:true});modal('일회용 주문 조회 인증 코드','<p>구매자에게 별도 확인된 경로로 전달하세요. 15분 이내 1회 조회 가능합니다. 이 채팅창에 입력하지 마세요.</p>'+label('인증 코드',input('order-grant-code',r.code))+actionGroup({keepSize:true},copyButton('코드 복사','order-grant-code'),btn('닫기',"$('.modal')?.remove()")))})}
async function revokeOrderAccess(tid){await act(async()=>{await api('/api/inbox/'+enc(tid)+'/order-access/revoke',{});ownerOrderAccess()})}
function customerOrderAccess(){modal('인증 주문·배송 조회','<p>판매자에게 별도로 전달받은 일회용 인증 코드를 입력하세요. 주문번호만으로 조회할 수 없습니다.</p>'+label('인증 코드',input('customer-order-code','','password'))+btn('조회','redeemOrderAccess()','primary'))}
async function redeemOrderAccess(){await act(async()=>{const token=await getChatSession(),code=val('customer-order-code');$('#customer-order-code').value='';const r=await api('/api/customer/order-access',{token,code});if(token!==chatSession)return;modal('주문·배송 조회 결과','<p>'+e(r.product)+'</p><p>주문 상태 '+e(r.status)+' · 배송 '+e(r.delivery_status||'미제공')+'</p><p>'+e(r.carrier)+' '+e(r.tracking)+'</p><p class="muted">조회 시점 '+e(new Date(r.queried_at*1000).toLocaleString('ko-KR'))+' · 인증 코드는 사용 완료되었습니다. 재조회는 새 승인 필요.</p>')})}


async function coupangModal(){await act(async()=>{const agent=commerceAgent,r=await api(scopedUrl('/api/commerce/coupang',agent));modal('쿠팡 주문·배송 조회','<p>판매자 WING의 Open API 키를 연결합니다. 주문 조회만 가능하며 발주·취소·환불은 실행하지 않습니다. 상품 목록 및 주문 상태 자동 수집은 별도 설정에서 활성화할 수 있습니다.</p><p>'+e(r.connected?'연결됨 · '+r.vendor:'미연결')+'</p>'+(r.available?(r.connected?label('쿠팡 주문번호',input('cp-order-ref'))+actionGroup({keepSize:true},btn('실시간 조회',"lookupCoupang('"+agent+"')",'primary'),btn('연결 해제',"disconnectCoupang('"+agent+"')")):label('업체 코드 (vendorId)',input('cp-vendor'))+label('Access Key',input('cp-access','','password'))+label('Secret Key',input('cp-secret','','password'))+label('권한 확인용 실제 주문번호',input('cp-verify-order'))+btn('인증 확인 및 연결',"connectCoupang('"+agent+"')",'primary')):'<p>실제 계정 검증 전 서버 기능이 비활성화되어 있습니다.</p>')+'<p><a href="https://developers.coupang.com/ko/api" target="_blank" rel="noopener noreferrer">쿠팡 공식 API 문서</a></p>')})}
async function connectCoupang(agent){if(!confirm('API 키를 암호화 저장하고 쿠팡 주문 조회를 허용할까요?'))return;await act(async()=>{const body={vendor:val('cp-vendor'),access_key:val('cp-access'),secret_key:val('cp-secret'),reference:val('cp-verify-order'),confirmed:true};$('#cp-access').value='';$('#cp-secret').value='';await api(scopedUrl('/api/commerce/coupang/connect',agent),body);coupangModal()})}
async function lookupCoupang(agent){await act(async()=>{const r=await api(scopedUrl('/api/commerce/coupang/order-status',agent),{reference:val('cp-order-ref'),confirmed:true});modal('쿠팡 주문 조회 결과','<p>주문번호 '+e(r.reference)+'</p>'+r.shipments.map(x=>'<div class="line"><b>'+e(x.state_label)+'</b><p>'+e(x.products.join(' / '))+'</p><p>'+e(x.carrier)+' '+e(x.tracking)+'</p></div>').join('')+'<p>조회 시점 '+e(new Date(r.queried_at*1000).toLocaleString('ko-KR'))+'</p>'+btn('다시 조회','coupangModal()'))})}
async function disconnectCoupang(agent){if(!confirm('저장된 쿠팡 인증 정보를 삭제할까요?'))return;await act(async()=>{await api(scopedUrl('/api/commerce/coupang/disconnect',agent),{});coupangModal()})}


async function coupangCatalogModal(){await act(async()=>{const a=commerceAgent,r=await api(scopedUrl('/api/commerce/coupang/catalog',a));modal('쿠팡 상품 목록 자동 수집','<p>등록 상품명과 번호를 최대 2,000개, 6시간마다 수집합니다. 교육 크레딧은 차감하지 않습니다. 목록만으로 가격·재고·판매 가능 여부는 확정하지 않습니다.</p><p>'+e(r.state)+' · '+e(r.count)+'개</p><p>'+e(r.error||'')+'</p>'+(r.available&&r.connected?btn(r.active?'지금 동기화 요청':'자동 수집 시작',"setCoupangCatalog('"+a+"',true)",'primary')+(r.active?actionGroup({keepSize:true},btn('상품 목록',"viewCoupangCatalog('"+a+"',1)"),btn('수집 중지 및 목록 삭제',"setCoupangCatalog('"+a+"',false)")):''):'<p>서버 기능 및 판매자 연결 필요</p>'+btn('판매자 연결','coupangModal()'))+btn('상태 새로고침','coupangCatalogModal()'))})}
async function setCoupangCatalog(a,enabled){if(!confirm(enabled?'쿠팡 상품 목록을 조회하고 자동 수집할까요?':'수집한 상품 목록을 삭제할까요?'))return;await act(async()=>{await api(scopedUrl('/api/commerce/coupang/catalog',a),{enabled});coupangCatalogModal()})}
async function viewCoupangCatalog(a,page){await act(async()=>{const r=await api(scopedUrl('/api/commerce/coupang/catalog/products',a)+'&page='+page);modal('쿠팡 수집 상품',r.products.map(x=>'<div class="line"><b>'+e(x.name)+'</b><p>등록상품번호 '+e(x.id)+'</p>'+btn('상세정보·옵션',"coupangDetailModal('"+a+"','"+x.id+"')")+'</div>').join('')+actionGroup({keepSize:true},(page>1?btn('이전',"viewCoupangCatalog('"+a+"',"+(page-1)+")"):''),(page*100<r.count?btn('다음',"viewCoupangCatalog('"+a+"',"+(page+1)+")"):''),btn('연동 설정','coupangCatalogModal()')))})}


let marketQna={provider:'smartstore',agent:'',items:[],send:false,ai:false,busy:false};
async function marketplaceQnaModal(){await act(async()=>{const agent=commerceAgent,r=await api(scopedUrl('/api/commerce/qna/status',agent));marketQna={provider:'smartstore',agent,items:[],send:false,ai:false,busy:false};modal('판매처 상품 Q&A','<p>최근 7일 미답변 문의를 최대 250건 조회합니다. 상담 채널 연동과 별개입니다. AI 초안 생성 시 기존 상담량 1회 차감, 직접 답변·조회는 AI 크레딧 미사용입니다.</p>'+Object.entries(r).map(([k,v])=>'<div class="line"><b>'+e(commerceChannels[k])+'</b><p>'+e(v.available&&v.connected?'조회 가능':'연결 또는 서버 권한 확인 필요')+'</p>'+(v.available&&v.connected?actionGroup({keepSize:true},btn('미답변 조회',"refreshMarketplaceQna('"+k+"')"),btn('승인 FAQ 자동화',"marketAutoModal('"+k+"')")):'')+'</div>').join(''))})}
async function refreshMarketplaceQna(provider){if(marketQna.busy)return;marketQna.busy=true;try{await act(async()=>{const a=marketQna.agent,r=await api(scopedUrl('/api/commerce/qna/refresh',a),{provider});marketQna={provider,agent:a,items:r.items,send:r.send_available,ai:r.ai_available,busy:true};modal(e(commerceChannels[provider])+' 상품 Q&A','<p>'+e(r.items.length)+'건 · 미답변 최근 7일'+(r.partial?' · 250건까지만 조회됨':'')+'</p>'+r.items.map((x,i)=>'<div class="line"><b>'+e(x.name||('상품번호 '+x.product_id))+'</b><p>'+e(x.question)+'</p><small>'+e(x.state)+'</small>'+(['pending','draft'].includes(x.state)?btn('답변 검토',"editMarketplaceQna("+i+")"):'')+'</div>').join('')+actionGroup({keepSize:true},btn('새로고침',"refreshMarketplaceQna('"+provider+"')"),btn('판매처 선택','marketplaceQnaModal()')))})}finally{marketQna.busy=false}}
function editMarketplaceQna(i){const x=marketQna.items[i];if(!x)return;modal('상품 문의 답변 검토','<p>'+e(x.name||('상품번호 '+x.product_id))+'</p>'+label('AI에 전달할 질문 (개인정보 제거 후 검토)',ta('market-qna-question',x.question))+(marketQna.ai&&x.state==='pending'?'<label><input type="checkbox" id="market-qna-ai-consent"> 질문의 개인정보를 제거했고 상담량 1회 사용에 동의합니다.</label>'+btn('AI 답변 초안 생성',"draftMarketplaceQna("+i+")",'primary'):'')+label('최종 공개 답변',ta('market-qna-answer',x.draft||''))+(marketQna.provider==='coupang'?label('응답자 WING ID',input('market-qna-wing')):'')+(marketQna.send?'<label><input type="checkbox" id="market-qna-send-consent"> 공개 답변을 검토했으며 해당 문의로 발송합니다.</label>'+btn('판매처에 답변 발송',"sendMarketplaceQna("+i+")",'primary'):'<p class="muted">실제 자동/수동 API 발송은 운영 검증 전 비활성화되어 있습니다.</p>')+actionGroup({keepSize:true},copyButton('답변 복사','market-qna-answer'),btn('목록',"refreshMarketplaceQna('"+marketQna.provider+"')")))}
async function draftMarketplaceQna(i){if(marketQna.busy)return;if(!checked('market-qna-ai-consent'))return toast('개인정보 확인 및 사용량 동의가 필요합니다.');marketQna.busy=true;try{await act(async()=>{const m=marketQna,x=m.items[i],r=await api(scopedUrl('/api/commerce/qna/draft',m.agent),{provider:m.provider,id:x.remote_id,question:val('market-qna-question'),confirmed:true});x.draft=r.draft;x.state='draft';await refresh();editMarketplaceQna(i);toast('AI 초안 생성 · 발송 전 반드시 확인하세요.')})}finally{marketQna.busy=false}}
async function sendMarketplaceQna(i){if(marketQna.busy)return;if(!checked('market-qna-send-consent'))return toast('공개 답변 승인 필요');marketQna.busy=true;try{await act(async()=>{const m=marketQna,x=m.items[i],r=await api(scopedUrl('/api/commerce/qna/send',m.agent),{provider:m.provider,id:x.remote_id,answer:val('market-qna-answer'),wing:$('#market-qna-wing')?.value||'',confirmed:true});x.state=r.state;modal('발송 결과','<p>'+e(r.state==='sent'?'판매처 발송 확인':'결과 미확인 · 판매처에서 직접 확인하세요. 자동 재전송하지 않습니다.')+'</p>'+btn('문의 목록',"refreshMarketplaceQna('"+m.provider+"')"))})}finally{marketQna.busy=false}}


async function coupangDetailModal(a,pid){await act(async()=>{const path=scopedUrl('/api/commerce/coupang/catalog/products/'+enc(pid)+'/detail',a),r=await api(path),d=r.content;modal('쿠팡 상세상품·옵션','<p>공개 상품 상세정보 수집과 옵션별 가격·재고 조회는 교육 크레딧을 사용하지 않습니다.</p>'+btn('상세정보 가져오기·갱신',"collectCoupangDetail('"+a+"','"+pid+"')",'primary')+(r.collected?'<h3>'+e(d.name||'상세상품')+'</h3><p>'+e(r.stale?'상세정보 갱신 필요':'상세정보 수집됨')+' · 이미지 '+e(d.image_count)+'개 (자동 이미지 분석 미지원)</p><pre style="white-space:pre-wrap;max-height:220px;overflow:auto">'+e(d.text)+'</pre><p>'+e(JSON.stringify(d.fees))+'</p>'+d.variants.map(v=>'<div class="line"><b>'+e(v.name)+'</b><p>옵션번호 '+e(v.id)+'</p>'+btn('가격·재고 조회',"lookupCoupangInventory('"+a+"','"+pid+"','"+v.id+"')")+'</div>').join(''):'')+btn('상품 목록',"viewCoupangCatalog('"+a+"',1)"))})}
async function collectCoupangDetail(a,pid){await act(async()=>{await api(scopedUrl('/api/commerce/coupang/catalog/products/'+enc(pid)+'/detail',a),{});coupangDetailModal(a,pid)})}
async function lookupCoupangInventory(a,pid,iid){await act(async()=>{const r=await api(scopedUrl('/api/commerce/coupang/catalog/products/'+enc(pid)+'/inventory',a),{item_id:iid});modal('옵션 가격·재고 조회','<p>옵션 '+e(r.item_id)+'</p><p>판매가 '+money(r.price)+' · 잔여 수량 '+e(r.stock)+'개</p><p>'+e(r.on_sale?'판매 중':'판매 중지')+'</p><p class="muted">조회 시점 '+e(new Date(r.queried_at*1000).toLocaleString('ko-KR'))+' · 5분 이내 상담 참고 정보로 활용됩니다.</p>'+btn('상세정보 돌아가기',"coupangDetailModal('"+a+"','"+pid+"')"))})}


const ssOrderStatus={PAYMENT_WAITING:'결제 대기',PAYED:'결제 완료',DELIVERING:'배송 중',DELIVERED:'배송 완료',PURCHASE_DECIDED:'구매 확정',EXCHANGED:'교환',CANCELED:'취소',RETURNED:'반품',CANCELED_BY_NOPAYMENT:'미결제 취소'};
async function smartstoreOrderSyncModal(){await act(async()=>{const a=commerceAgent,r=await api(scopedUrl('/api/commerce/smartstore/order-sync',a));modal('스마트스토어 주문 상태 자동 동기화','<p>신규·변경된 상품주문 상태를 10분마다 조회합니다. 처음에는 최근 24시간부터 순차 수집합니다. 조회만 수행하며 주문 변경이나 AI 호출은 없습니다.</p><p>수집 상태 '+e(r.state)+' · '+e(r.count)+'건</p><p>조회 완료 시점 '+e(r.cursor?new Date(r.cursor*1000).toLocaleString('ko-KR'):'미수집')+'</p><p>'+e(r.error||'')+'</p>'+(r.available&&r.connected?btn(r.active?'동기화 요청':'자동 동기화 시작',"setSmartstoreOrderSync('"+a+"',true)",'primary')+(r.active||r.count?actionGroup({keepSize:true},btn('변경 주문 목록',"viewSmartstoreOrderSync('"+a+"',1)"),btn('중지 및 수집 정보 삭제',"setSmartstoreOrderSync('"+a+"',false)")):''):'<p>스마트스토어 연동 및 서버 기능 활성화 필요</p>')+'<p class="muted">판매자 전용 상태 정보이며, 실제 정산액·전체 주문·반품 처리 완료를 보장하지 않습니다. 수동 주문 매출에 합산하지 않습니다.</p>'+btn('상태 새로고침','smartstoreOrderSyncModal()'))})}
async function setSmartstoreOrderSync(a,enabled){if(!confirm(enabled?'변경 주문 상태를 자동으로 수집할까요?':'수집 정보 및 조회 기준을 삭제할까요?'))return;await act(async()=>{await api(scopedUrl('/api/commerce/smartstore/order-sync',a),{enabled});smartstoreOrderSyncModal()})}
async function viewSmartstoreOrderSync(a,page){await act(async()=>{const r=await api(scopedUrl('/api/commerce/smartstore/order-sync/records',a)+'&page='+page);modal('스마트스토어 변경 주문 목록','<p>최근 동기화 '+e(r.last_sync?new Date(r.last_sync*1000).toLocaleString('ko-KR'):'미동기화')+'</p>'+r.records.map(x=>'<div class="line"><b>'+e(ssOrderStatus[x.status]||x.status)+'</b><p>상품주문 '+e(x.reference)+' · 주문 '+e(x.order_id)+'</p><p>'+e([x.claimType,x.claimStatus].filter(Boolean).join(' / '))+'</p><small>'+e(new Date(x.changed_at).toLocaleString('ko-KR'))+'</small></div>').join('')+actionGroup({keepSize:true},(page>1?btn('이전',"viewSmartstoreOrderSync('"+a+"',"+(page-1)+")"):''),(page*100<r.count?btn('다음',"viewSmartstoreOrderSync('"+a+"',"+(page+1)+")"):''),btn('동기화 설정','smartstoreOrderSyncModal()')))})}


const cpOrderLabels={ACCEPT:'결제 완료',INSTRUCT:'상품 준비 중',DEPARTURE:'배송 지시',DELIVERING:'배송 중',FINAL_DELIVERY:'배송 완료',NONE_TRACKING:'직접 배송·추적 불가'};
async function coupangOrderSyncModal(){await act(async()=>{const a=commerceAgent,r=await api(scopedUrl('/api/commerce/coupang/order-sync',a));modal('쿠팡 주문 상태 자동 동기화','<p>오늘 주문과 최근 6일 주문을 상태별로 반복 조회합니다. 배송번호 기준으로 갱신하며 AI 호출은 없습니다.</p><p>'+e(r.state)+' · '+e(r.count)+'건 · 다음 조회 '+e(r.scan_day||'미설정')+'</p><p>'+e(r.error||'')+'</p>'+(r.available&&r.connected?btn(r.active?'동기화 요청':'자동 동기화 시작',"setCoupangOrderSync('"+a+"',true)",'primary')+(r.active||r.count?actionGroup({keepSize:true},btn('수집 주문 목록',"viewCoupangOrderSync('"+a+"',1)"),btn('중지 및 삭제',"setCoupangOrderSync('"+a+"',false)")):''):'<p>쿠팡 연동 및 서버 기능 활성화 필요</p>')+'<p class="muted">발주서 상태만 조회하며 취소·반품·교환은 별도 조회가 필요합니다. 매출에 합산하지 않으며 오래된 정보는 실제 상태와 다를 수 있습니다.</p>'+btn('새로고침','coupangOrderSyncModal()'))})}
async function setCoupangOrderSync(a,enabled){if(!confirm(enabled?'쿠팡 주문 상태 자동 수집을 시작할까요?':'수집된 주문 상태를 삭제할까요?'))return;await act(async()=>{await api(scopedUrl('/api/commerce/coupang/order-sync',a),{enabled});coupangOrderSyncModal()})}
async function viewCoupangOrderSync(a,page){await act(async()=>{const r=await api(scopedUrl('/api/commerce/coupang/order-sync/records',a)+'&page='+page);modal('쿠팡 수집 주문 상태',r.records.map(x=>'<div class="line"><b>'+e(cpOrderLabels[x.status]||x.status)+'</b><p>배송번호 '+e(x.shipment_id)+' · 주문번호 '+e(x.reference)+'</p><p>'+e(x.observed?'마지막 관측 상태':'최근 조회에서 확인되지 않음 · 판매처 확인 필요')+'</p><small>'+e(new Date(x.as_of*1000).toLocaleString('ko-KR'))+'</small></div>').join('')+actionGroup({keepSize:true},(page>1?btn('이전',"viewCoupangOrderSync('"+a+"',"+(page-1)+")"):''),(page*100<r.count?btn('다음',"viewCoupangOrderSync('"+a+"',"+(page+1)+")"):''),btn('동기화 설정','coupangOrderSyncModal()')))})}


async function marketAutoModal(p){await act(async()=>{const a=commerceAgent,r=await api(scopedUrl('/api/commerce/qna/automation',a)+'&provider='+enc(p));modal('승인 FAQ 자동화','<p>상품별로 직접 승인한 고정 질문과 답변만 사용합니다. 질문이 정확히 같고 상품 상세정보가 변경되지 않은 경우에만 후보가 됩니다. AI 사용량은 차감하지 않습니다. 가격·재고·배송·교환·환불·개인정보 문의는 제외합니다.</p><p>현재 '+e(r.mode)+'</p>'+label('하루 최대 발송 (1~10)',input('ma-limit',r.daily_limit,'number'))+(p==='coupang'?label('응답 WING ID',input('ma-wing')):'')+(r.available&&r.connected?btn('미리보기 자동 수집',"marketAutoSet('"+p+"','preview')",'primary')+(r.live_available?btn('실제 자동 발송 활성화',"marketAutoSet('"+p+"','send')"):'<p class="muted">실제 무인 발송은 운영 검증 전 비활성화 상태입니다.</p>')+actionGroup({keepSize:true},btn('중지',"marketAutoSet('"+p+"','off')"),btn('승인 질문·답변 추가',"marketAutoRuleModal('"+p+"')")):'<p>서버 및 판매처 연결 필요</p>')+r.rules.map(x=>'<div class="line"><b>'+e(x.product_id)+' · '+e(x.question)+'</b><p>'+e(x.answer)+'</p>'+btn('승인 삭제',"deleteMarketAutoRule('"+p+"','"+x.id+"',this)")+'</div>').join('')+'<h3>최근 자동화 후보·발송 기록</h3>'+r.logs.map(x=>'<p>'+e(x.remote_id)+' · '+e(x.state)+' · '+e(new Date(x.created*1000).toLocaleString('ko-KR'))+'</p>').join('')+btn('새로고침',"marketAutoModal('"+p+"')"))})}
async function marketAutoSet(p,mode){if(mode!=='off'&&!confirm(mode==='send'?'승인된 고정 FAQ를 실제 판매처에 자동 발송하도록 허용할까요?':'발송 없이 일치하는 문의만 확인할까요?'))return;await act(async()=>{await api(scopedUrl('/api/commerce/qna/automation',commerceAgent),{provider:p,mode,daily_limit:Number(val('ma-limit')),wing:$('#ma-wing')?.value||'',confirmed:true});marketAutoModal(p)})}
function marketAutoRuleModal(p){modal('상품별 승인 FAQ 추가','<p>변하지 않는 공개 상품 정보에 대해서만 등록하세요. 상품 상세정보를 먼저 수집해야 합니다. 가격·배송·재고 등 변동 정보는 허용하지 않습니다.</p>'+label('판매처 상품번호',input('ma-pid'))+label('일치해야 하는 질문',ta('ma-question'))+label('공개할 최종 답변',ta('ma-answer'))+'<label><input type="checkbox" id="ma-confirm"> 해당 상품에 이 답변을 공개할 권한과 정확성을 검토했습니다.</label>'+btn('승인 FAQ 저장',"saveMarketAutoRule('"+p+"')",'primary'))}
async function saveMarketAutoRule(p){await act(async()=>{if(!checked('ma-confirm'))throw Error('공개 답변 승인 필요');await api(scopedUrl('/api/commerce/qna/automation/rules',commerceAgent),{provider:p,product_id:val('ma-pid'),question:val('ma-question'),answer:val('ma-answer'),confirmed:true});marketAutoModal(p)})}
async function deleteMarketAutoRule(platform,id,button){
 const row=button?.closest('.line');
 if(!confirm('승인된 자동 답변을 삭제할까요?'))return;
 await act(async()=>{
  await api(scopedUrl('/api/commerce/qna/automation/rules/'+enc(id),commerceAgent),null,'DELETE');
  await dustDelete(row);
  await marketAutoModal(platform);
 });
}


async function lineModal(agent=''){await act(async()=>{const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available&&!x.archived):[],r=await api(scopedUrl('/api/line',agent));modal('LINE 공식 계정 연결',brandSelect('line-brand',brands,agent,'lineModal(this.value)')+'<p>LINE Developers에서 발급한 Messaging API 액세스 토큰과 채널 시크릿을 등록합니다. 웹훅 서명 검증 뒤 활성화합니다.</p><p>'+e(r.active?'활성':r.verified?'검증됨 · 활성화 필요':r.saved?'웹훅 검증 필요':'미연결')+'</p>'+(r.saved?label('Webhook URL',input('line-webhook',r.webhook))+copyButton('주소 복사','line-webhook')+'<p>LINE Developers의 Webhook URL에 붙여넣고 Verify를 실행하세요.</p>'+actionGroup({keepSize:true},(!r.active&&r.verified&&r.available?btn('상담 활성화',"activateLine('"+agent+"')",'primary'):''),btn('연결 해제',"disconnectLine('"+agent+"')")):r.available?label('Channel access token',input('line-token','','password'))+label('Channel secret',input('line-secret','','password'))+btn('계정 인증 및 등록',"connectLine('"+agent+"')",'primary'):'<p>서버 기능 비활성화</p>')+'<p class="muted">'+e(r.reply_available?'짧은 유효시간의 답장 토큰만 사용합니다.':'현재 수신·수동 상담 기록만 지원합니다.')+' 푸시·그룹·광고 발송은 미지원입니다.</p>'+btn('검증 상태 새로고침',"lineModal('"+agent+"')")+'<p><a href="https://developers.line.biz/console/" target="_blank" rel="noopener noreferrer">LINE Developers Console</a></p>')})}
async function connectLine(agent){if(!confirm('LINE 계정 인증 정보를 암호화하여 저장할까요?'))return;await act(async()=>{const token=val('line-token'),channel_secret=val('line-secret');$('#line-token').value='';$('#line-secret').value='';await api(scopedUrl('/api/line/connect',agent),{token,channel_secret,confirmed:true});lineModal(agent)})}
async function activateLine(agent){await act(async()=>{await api(scopedUrl('/api/line/activate',agent),{confirmed:true});lineModal(agent)})}
async function disconnectLine(agent){if(!confirm('CSAI 연결 정보를 삭제하고 LINE Developers에서도 Webhook을 비활성화하세요. 연결을 해제할까요?'))return;await act(async()=>{await api(scopedUrl('/api/line/disconnect',agent),{confirmed:true});lineModal(agent)})}


async function instagramModal(agent=''){await act(async()=>{const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available&&!x.archived):[],r=await api(scopedUrl('/api/instagram',agent));modal('인스타그램 DM 수신 연결',brandSelect('ig-brand',brands,agent,'instagramModal(this.value)')+'<p>CSAI Meta 앱의 Instagram 메시지 권한 및 웹훅 구독이 완료된 전문 계정만 연결하세요. 계정 인증용 액세스 토큰은 저장하지 않습니다.</p><p>'+e(r.connected?'연결됨 · '+r.account:'미연결')+'</p>'+(r.connected?btn('연결 해제',"disconnectInstagram('"+agent+"')"):r.available?label('Instagram Login access token',input('ig-token','','password'))+'<label><input type="checkbox" id="ig-confirm"> 승인된 Meta 앱의 메시지 권한 및 웹훅 구독을 확인했습니다.</label>'+btn('계정 확인 및 연결',"connectInstagram('"+agent+"')",'primary'):'<p>운영자 Meta 앱 및 서버 설정 필요</p>')+'<p class="muted">개인 텍스트 DM 수신 전용. 자동 답장·직접 발송·이미지·과거 기록 수집은 지원하지 않습니다.</p><p><a href="https://developers.facebook.com/" target="_blank" rel="noopener noreferrer">Meta for Developers</a></p>')})}
async function connectInstagram(agent){await act(async()=>{if(!checked('ig-confirm'))throw Error('Meta 메시지 권한과 구독 확인 필요');const token=val('ig-token');$('#ig-token').value='';await api(scopedUrl('/api/instagram/connect',agent),{token,confirmed:true,subscribed:true});instagramModal(agent)})}
async function disconnectInstagram(agent){if(!confirm('CSAI의 계정 연결을 해제할까요? Meta 웹훅 구독은 별도로 관리해야 합니다.'))return;await act(async()=>{await api(scopedUrl('/api/instagram/disconnect',agent),{confirmed:true});instagramModal(agent)})}

// Catalog-backed page offers; never duplicate an existing purchase notice.
const pagePaidFeatures={
 calendar:['calendar','auto_booking','change_booking','google_calendar','booking_alert'],
 'booking-settings':['calendar','auto_booking','change_booking','google_calendar','booking_alert'],
 customers:['crm','quote','tasks','leads','complaints','stats','export'],
 alerts:['push','email','unknown_alert','new_alert','booking_alert','report'],
 settings:['multilingual','design','unbrand','custom_url'],
 inbox:['retention'],
 'consultation-center':['retention'],
 preview:['design','unbrand','custom_url'],
 'chat-page':['design','unbrand','custom_url'],
 stats:['stats'],
 reports:['report'],
 agents:['extra_agent'],
 developer:['external_api','custom_integration'],
};
function ensurePagePaidNotices(main){
 const existing=new Set([...main.querySelectorAll('.paid-preview-notice[data-paid-feature]')].map(n=>n.dataset.paidFeature));
 if(!me||me.operator)return;
 const catalog=new Set(cfg.catalog.addons.map(a=>a.id));
 const missing=(pagePaidFeatures[route]||[]).filter(key=>catalog.has(key)&&!has(key)&&!existing.has(key));
 if(missing.length)main.insertAdjacentHTML('beforeend',missing.map(key=>previewNotice(key,'',{detailsOnly:true})).join(''));
}
let paidPreviewHeaderObserver=null,paidPreviewScrollCleanup=null,paidPreviewRoute='',paidPreviewExpanded=true;
function prioritizePaidPreviews(){
 paidPreviewHeaderObserver?.disconnect();paidPreviewHeaderObserver=null;
 paidPreviewScrollCleanup?.();paidPreviewScrollCleanup=null;
 if(paidPreviewRoute!==route){paidPreviewRoute=route;paidPreviewExpanded=true;}
 const main=$('.layout main');if(!main)return;
 const header=$('.layout .app-sidebar');
 const setup=main.querySelector(':scope > .dashboard-setup-strip');
 ensurePagePaidNotices(main);
 const notices=[...main.querySelectorAll('.paid-preview-notice')];
 const seen=new Set();for(let i=0;i<notices.length;){const n=notices[i],key=n.dataset.paidFeature;if(key&&(has(key)||seen.has(key))){n.remove();notices.splice(i,1);continue;}if(key)seen.add(key);i++;}
 const ordered=pagePaidFeatures[route]||[];const rank=n=>ordered.includes(n.dataset.paidFeature)?ordered.indexOf(n.dataset.paidFeature):ordered.length;notices.sort((a,b)=>rank(a)-rank(b));
 if(!setup&&!notices.length)return;
 const top=document.createElement('div');top.className='purchase-sticky-stack';
 const first=main.querySelector(':scope > .mobile-service-notice');if(first)first.after(top);else main.prepend(top);
 if(setup)top.append(setup);
 if(notices.length){
  const group=document.createElement('section');group.className='card app-card paid-preview-top paid-preview-always';group.setAttribute('aria-label','구독 및 결제 안내');
  const body=document.createElement('div');body.className='paid-preview-list';body.id='page-paid-preview-list';notices.forEach(n=>body.append(n));
  const toggle=document.createElement('button');toggle.type='button';toggle.className='paid-preview-toggle';toggle.setAttribute('aria-controls',body.id);toggle.innerHTML=uiIcon('chevron-down');
  const sync=()=>{body.hidden=!paidPreviewExpanded;toggle.setAttribute('aria-expanded',String(paidPreviewExpanded));toggle.setAttribute('aria-label',paidPreviewExpanded?'구독 기능 가격표 접기':'구독 기능 가격표 펼치기');toggle.title=toggle.getAttribute('aria-label');};
  // Reopen on a return to the page top, not merely when the user collapses there.
  const pageScrollTop=()=>{const root=document.scrollingElement;let y=root?.scrollTop||0;for(let node=main;node&&node!==document.body&&node!==root;node=node.parentElement){y+=Math.max(0,node.scrollTop||0);}return Math.max(0,y);};
  let previousScroll=pageScrollTop(),leftTop=previousScroll>16;
  const restoreAtTop=()=>{const y=pageScrollTop();if(y===previousScroll)return;if(y>16)leftTop=true;if(!paidPreviewExpanded&&leftTop&&y<=4&&y<previousScroll){paidPreviewExpanded=true;sync();leftTop=false;}previousScroll=y;};
  toggle.addEventListener('click',()=>{paidPreviewExpanded=!paidPreviewExpanded;sync();previousScroll=pageScrollTop();leftTop=previousScroll>16;});
  sync();group.append(body,toggle);top.append(group);
  document.addEventListener('scroll',restoreAtTop,{capture:true,passive:true});
  window.addEventListener('scroll',restoreAtTop,{passive:true});
  paidPreviewScrollCleanup=()=>{document.removeEventListener('scroll',restoreAtTop,true);window.removeEventListener('scroll',restoreAtTop);};
 }
 const update=()=>{if(!matchMedia('(max-width:700px)').matches){top.style.removeProperty('--paid-sticky-offset');return;}if(header&&!header.classList.contains('open'))top.style.setProperty('--paid-sticky-offset',Math.ceil(header.getBoundingClientRect().height)+'px');};
 update();if(header&&typeof ResizeObserver!=='undefined'){paidPreviewHeaderObserver=new ResizeObserver(update);paidPreviewHeaderObserver.observe(header);}
}

async function render(){captureEducationDraft();let id=++renderId;const nextRoute=location.hash.slice(1)||'dashboard';if(activeTemporary&&!['inbox','consultation-center'].includes(nextRoute)){await leaveTemporary();if(id!==renderId)return;}else if(activeTemporary&&activeTemporary.id!==threadId){await leaveTemporary();if(id!==renderId)return;}route=nextRoute;if(inboxDesk()&&route==='inbox')route='consultation-center';if(!me){$('#app').innerHTML=home();return}CSAISetup.initialize();if(id!==renderId)return;let views={dashboard:businessDashboard,'service-notices':serviceNoticePage,commerce:commercePage,setup:qualityHome,education,style,preview:()=>preview(),'chat-page':customerChatPage,stats:statsPage,reports:reportsPage,test:()=>preview(true),inbox,'consultation-center':inbox,'reply-assistant':replyAssistantPage,alerts,settings,calendar,team:teamPage,'staff-desk':staffDesk,fields:fieldsPage,'booking-settings':bookingSettings,customers,channels,developer,pricing,features,'service-plan':servicePlanPage,credits,addons,allinone,orders,agents,invites,costs};try{let html=await (views[route]||education)();if(id!==renderId)return;captureEducationDraft();$('#app').innerHTML=inboxDesk()&&inboxCenter()?inboxDeskShell(html):shell(html);prioritizePaidPreviews();restoreEducationDraft();updatePrice();mountCalendarMotion();mountInboxPullRefresh();mountSettingsStack();const ownerChat=$('.inbox-conversation');if(ownerChat)ownerChat.scrollTop=ownerChat.scrollHeight;requestAnimationFrame(fitPreviewToScreen);}catch(x){if(id===renderId)$('#app').innerHTML=shell(card('오류',`<p class="error">${e(x.message)}</p>${btn('다시 시도','render()')}`))}}
async function init(){try{if(location.hash.startsWith('#staff-invite=')){sessionStorage.setItem('csai-staff-invite',location.hash.slice(14));history.replaceState(null,'',location.pathname+'#staff-desk')}if(location.hash.startsWith('#invite=')){sessionStorage.setItem('csai-invite',location.hash.slice(8));history.replaceState(null,'',location.pathname+'#education')}cfg=await api('/api/config');if(publicMode){$('#app-design-system').media='all';pub=await api('/api/public/'+enc(slug));let saved=sessionStorage.getItem('csai-session-'+slug);if(!saved){try{const r=await api('/api/customer/resume',{slug,action:'load'});saved=r.token||null;if(saved)sessionStorage.setItem('csai-session-'+slug,saved)}catch{}}if(saved){try{chatMessages=await api('/api/session/'+enc(saved)+'/messages');chatSession=saved}catch{sessionStorage.removeItem('csai-session-'+slug)}}$('#app').innerHTML=`<div class="${publicChatClass()}">${phone(pub)}</div>`;setInterval(async()=>{if(!chatSession||sending||$('#booking-box'))return;try{const pollingToken=chatSession;let ms=await api('/api/session/'+enc(pollingToken)+'/messages');if(pollingToken!==chatSession)return;if(ms.length!==chatMessages.length){chatMessages=ms;$('#messages').innerHTML=welcomeMarkup(pub)+ms.map(m=>photoBubble(m,'customer')).join('');$('#messages').scrollTop=$('#messages').scrollHeight}}catch{}},4000);return}try{await refresh();if(sessionStorage.getItem('csai-desk-return')&&!inboxDesk()){sessionStorage.removeItem('csai-desk-return');location.replace('/?desk=1#consultation-center');return;}if(sessionStorage.getItem('csai-staff-invite'))history.replaceState(null,'',location.pathname+'#staff-desk');selectedPlan=me.plan==='free'?'lite':me.plan;selectedAdd=new Set(me.addons);}catch(x){if(x.status!==401)throw x}await render()}catch(x){$('#app').innerHTML=`<div class="hero"><div class="hero-inner"><h1>CS AI</h1><p class="error">${e(x.message)}</p><a href="/">처음으로</a></div></div>`}}
/* v0.2 operational UI */
function resources(){return (route==='calendar'?calendarProfile?.resources:null)||me?.settings.resources||[{id:'default',name:'기본 담당자'}]}
function clearSlots(){if($('#slots'))$('#slots').innerHTML=''}
let resourceDraft=[];
function resourceModal(reset=true){if(!requirePreviewAccess('calendar'))return;if(reset)resourceDraft=structuredClone(resources());modal('담당자 관리',resourceDraft.map((r,i)=>`<div class="row line">${input('res-'+i,r.name)}${r.id!=='default'?btn('삭제',`resourceDraft.splice(${i},1);resourceModal(false)`):''}</div>`).join('')+actionGroup({keepSize:true},btn('담당자 추가',"resourceDraft.forEach((r,i)=>r.name=val('res-'+i));resourceDraft.push({id:'r_'+crypto.randomUUID().slice(0,8),name:'새 담당자'});resourceModal(false)"),btn('저장',"act(async()=>{resourceDraft.forEach((r,i)=>r.name=val('res-'+i));if(calendarAgent&&route==='calendar')await api('/api/brand-calendar/'+enc(calendarAgent)+'/settings',{resources:resourceDraft});else await api('/api/settings',{resources:resourceDraft},'PATCH');$('.modal').remove();render()})",'primary'))+'<p class="muted">담당자마다 중복 예약을 검사합니다. 영업시간은 업체 공통입니다.</p>')}
const reviewFields={
 rules:{title:'응대 규칙',item:'규칙',limit:100,maxLength:1000},
 faq:{title:'모범 질문·답변',item:'질문·답변',limit:200},
 conflicts:{title:'확인 필요 항목',item:'확인 항목',limit:100,maxLength:500},
};
function reviewRow(key,value){
 const field=reviewFields[key];
 const fields=key==='faq'?
  `<label class="ui-field"><span>질문</span><textarea data-review-q maxlength="500" rows="2">${e(value.q)}</textarea></label>
   <label class="ui-field"><span>답변</span><textarea data-review-a maxlength="2000" rows="3">${e(value.a)}</textarea></label>`:
  `<label class="ui-field"><span>${field.item}</span><textarea data-review-text maxlength="${field.maxLength}" rows="2">${e(value)}</textarea></label>`;
 return `<div class="training-review-row" data-review-row>${fields}${actionFooter([
  `<button type="button" class="ui-button tertiary ui-sm" onclick="this.closest('[data-review-row]').remove()">${field.item} 삭제</button>`,
 ],{divided:false})}</div>`;
}
function reviewGroup(key,result){
 const field=reviewFields[key];
 return section('training-review-'+key,field.title,
  `<div class="ui-stack" data-review-list="${key}">${(result[key]||[]).map(value=>reviewRow(key,value)).join('')}</div>`+
  actionFooter([btn(field.item+' 추가',`addTrainingReviewRow(this.form,'${key}')`,'secondary ui-sm')],{divided:false}));
}
function addTrainingReviewRow(form,key){
 const field=reviewFields[key],list=form.querySelector(`[data-review-list="${key}"]`);
 if(list.children.length>=field.limit){toast(`${field.item}은 최대 ${field.limit}개입니다.`);return;}
 list.insertAdjacentHTML('beforeend',reviewRow(key,key==='faq'?{}:''));
 list.lastElementChild.querySelector('textarea').focus();
}
async function reviewModal(id){await act(async()=>{
 const [jobs,comparison]=await Promise.all([api('/api/training'),api('/api/quality/training/'+id+'/compare')]);
 const job=jobs.find(item=>item.id===id&&item.state==='review');
 if(!job?.result)throw Error('검토 중인 교육 초안만 수정할 수 있습니다.');
 const d=comparison;
 const notes=helperText(`새 FAQ ${d.added_questions.length}개 · 중복 ${d.duplicates.length}개 · 기존 답변 충돌 ${d.conflicts.length}개`)+
  d.conflicts.map(x=>`<div class="line"><b>${e(x.question)}</b><p>기존: ${e(x.previous)}</p><p>초안: ${e(x.proposed)}</p></div>`).join('');
 const editor=`<form class="training-review-form ui-stack" data-training-id="${e(id)}" onsubmit="event.preventDefault();saveTrainingReview(this)">
  ${helperText('말투, 규칙, 질문과 답변을 직접 고칠 수 있습니다. 수정 저장과 승인에는 AI 호출이나 추가 차감이 없습니다.')}
  ${label('상담 말투',`<textarea id="review-style" maxlength="1000">${e(job.result.style)}</textarea>`)}
  ${reviewGroup('rules',job.result)}
  ${reviewGroup('faq',job.result)}
  ${accordion('기존 답변 비교 및 확인 필요 항목',notes+reviewGroup('conflicts',job.result))}
  ${actionFooter(['<button class="ui-button primary" type="submit">수정 저장</button>'])}
 </form>`;
 modal('교육 초안 수정',editor,{dismissOnBackdrop:false});
})}
async function saveTrainingReview(form){
 const button=form.querySelector('[type="submit"]');
 if(button.disabled)return;
 await act(async()=>{
  const list=key=>[...form.querySelectorAll(`[data-review-list="${key}"] [data-review-text]`)].map(x=>x.value.trim()).filter(Boolean);
  const faq=[...form.querySelectorAll('[data-review-list="faq"] [data-review-row]')].map(row=>({
   q:row.querySelector('[data-review-q]').value.trim(),a:row.querySelector('[data-review-a]').value.trim(),
  })).filter(pair=>pair.q||pair.a);
  if(faq.some(pair=>!pair.q||!pair.a))throw Error('모범 질문과 답변을 모두 입력하세요.');
  const result={style:form.querySelector('#review-style').value,rules:list('rules'),faq,conflicts:list('conflicts')};
  button.disabled=true;button.setAttribute('aria-busy','true');
  try{
   await api('/api/training/'+enc(form.dataset.trainingId)+'/review',{result},'PATCH');
   form.closest('.modal')?.remove();toast('교육 초안을 수정했습니다.');await render();
  }finally{button.disabled=false;button.removeAttribute('aria-busy');}
 });
}
const oldEducation=education;education=async function(){let html=await oldEducation(),vs=educationAgent?(await api('/api/agents/versions')).filter(v=>v.agent===educationAgent):await api('/api/knowledge/versions');return html+card('교육 버전 이력',vs.map(v=>`<div class="row between line"><span>${e(v.label||'교육 반영 전 버전')} · ${e(new Date(v.created*1000).toLocaleString())}</span>${actionGroup({keepSize:true},btn('비교',`qualityCompare('${v.id}','${educationAgent}')`),btn('복원',educationAgent?`act(async()=>{await api('/api/agents/versions/${v.id}/restore',{});render()})`:`restoreVersion('${v.id}')`))}</div>`).join('')||emptyState('교육을 승인하면 이전 버전이 저장됩니다.',{title:'저장된 교육 이력이 없습니다',icon:'list'}))+responseControl(await api('/api/response-style?agent='+enc(educationAgent)))};
async function restoreVersion(id){if(!confirm('이전 교육 규칙으로 복원할까요? 현재 버전도 자동 백업됩니다.'))return;await act(async()=>{await api('/api/knowledge/versions/'+id+'/restore',{});render()})}
async function decideChange(id,action){await act(async()=>{await api(calendarAgent?'/api/brand-calendar/'+enc(calendarAgent)+'/changes/'+enc(id):'/api/booking-changes/'+enc(id),{action});render()})}
async function customerBookings(){await act(async()=>{let t=await getChatSession(),r=await api('/api/customer/bookings/'+enc(t));modal('내 예약',r.bookings.map(b=>`<div class="line"><b>${e(states[b.status])} · ${e(new Date(b.start).toLocaleString())}</b>${b.fields.map(f=>`<p>${e(f.label)}: ${e(b.payload[f.key]||'')}</p>`).join('')}${r.canChange&&b.status==='confirmed'?actionGroup({keepSize:true},btn('변경 요청',`customerChange('${b.id}','change')`),btn('취소 요청',`customerChange('${b.id}','cancel')`)):''}${r.canRecover!==false&&['confirmed','pending','pending_payment'].includes(b.status)?btn('복구 코드 발급',`issueRecovery('${b.id}')`):''}</div>`).join('')+(r.bookings.length?'':'<p>이 브라우저 세션에 등록된 예약이 없습니다.</p>')+r.requests.map(x=>`<p class="muted">${x.action==='cancel'?'취소':'변경'} 요청: ${e(x.state==='pending'?'승인 대기':x.state==='approved'?'승인 완료':'거절')}</p>`).join('')+(r.canRecover!==false?btn('다른 기기 예약 불러오기','recoverModal()'):'<p class="muted">추가 브랜드의 다른 기기 예약 복구는 담당자에게 문의하세요.</p>')+'<p class="muted">외부 플랫폼의 환불은 해당 판매처에서 진행하세요.</p>')})}
function customerChange(id,action){modal(action==='cancel'?'예약 취소 확인':'예약 변경 확인',(action==='change'?label('변경할 업체 현지 시간',input('customer-start','','datetime-local')):'<p>예약 취소를 요청합니다. 결제 환불은 별도입니다.</p>')+btn('확인 및 요청',`act(async()=>{let r=await api('/api/customer/bookings/${id}/change',{token:chatSession,action:'${action}',start:$('#customer-start')?.value||'',confirmed:true});toast(r.state==='approved'?'요청 처리 완료':'업체 승인 대기');await customerBookings()})`,'primary'))}
async function customerRequest(){await act(async()=>{let t=await getChatSession(),rs=await api('/api/customer/requests/'+enc(t));if(!rs.length)throw Error('등록 가능한 업무가 없습니다.');modal('업무 요청',label('유형',select('req-kind',rs.map(k=>[k,({quote:'견적 요청',complaints:'불만·민원',tasks:'기타 요청'})[k]]),rs[0]))+label('제목',input('req-title'))+label('상세 내용',ta('req-detail'))+btn('확인 및 접수',"act(async()=>{let r=await api('/api/customer/requests',{token:chatSession,kind:val('req-kind'),title:val('req-title'),details:val('req-detail'),confirmed:true});$('.modal').remove();toast(r.duplicate?'이미 접수된 요청이 있습니다.':'요청이 접수되었습니다.')})",'primary'))})}
async function convertModal(){await act(async()=>{let t=await api('/api/inbox/'+threadId),ks=['crm','quote','tasks','leads','complaints'].filter(has);modal('상담에서 업무 등록',label('분류',select('convert-kind',ks.map(k=>[k,cfg.catalog.addons.find(x=>x.id===k).name]),ks[0]))+label('제목',input('convert-title',(t.messages.find(x=>x.role==='user')?.body||'상담 요청').slice(0,120)))+label('내용',ta('convert-detail',t.messages.map(x=>x.role+': '+x.body).join('\n').slice(0,2000)))+btn('등록',"act(async()=>{let r=await api('/api/inbox/'+threadId+'/work',{kind:val('convert-kind'),title:val('convert-title'),details:val('convert-detail')});$('.modal').remove();toast(r.duplicate?'이미 등록된 업무입니다.':'업무 등록 완료')})",'primary'))})}
async function workEdit(id){await act(async()=>{let w=(await api(workPath())).find(x=>x.id===id);modal('업무 수정',label('제목',input('edit-title',w.title))+label('내용',ta('edit-details',w.details))+label('상태',select('edit-status',[['open','진행 중'],['pending','대기'],['resolved','완료']],w.status))+btn('저장',`act(async()=>{await api(workPath('${id}'),{title:val('edit-title'),details:val('edit-details'),status:val('edit-status')},'PATCH');$('.modal').remove();render()})`,'primary'))})}
async function workDelete(id,button){if(confirm('업무를 삭제할까요?'))await deleteVisibleRow(workPath(id),button);}
const oldAlerts=alerts;
alerts=async function(){
 let html=await oldAlerts();
 const events=await api('/api/events');html+=focusEvents(sharedPreviewEnabled()?events.concat(previewData().events):events);
 const readOnly=!has('email');if(readOnly&&!freeFeaturePreview())return html;
 const n=readOnly?previewData().email:await api('/api/notifications');
 const status=readOnly?'샘플 체험 · 실제 발송 없음':n.live_enabled?'실제 발송 활성화 · 검증 필요':cfg.demo?'로컬 모의 전송 · 이메일은 발송되지 않음':'실제 발송 비활성화';
 const controls=stack(
  actionGroup({keepSize:true},
   btn('저장',readOnly?'previewEmailAction(false)':"act(async()=>{await api('/api/notifications',{email:val('notify-email'),enabled:checked('notify-enabled')});render()})"),
   btn('대기 알림 보내기',readOnly?'previewEmailAction(true)':"act(async()=>{let r=await api('/api/notifications/dispatch',{});toast('처리 '+r.results.length+'건');render()})",'primary')
  )+
  helperText(status+' / 관련 알림 옵션 필요 / '+(n.auto_enabled?'자동 발송 설정 ON (워커 실행 필요)':'현재 수동 전송')),
  {gap:'compact'}
 );
 return html+(readOnly?previewNotice('email','이메일 알림 설정 체험'):'')+card('이메일 알림',helperText('신규 상담, 담당자 확인 요청 등 지원되는 업무 알림을 등록된 이메일로 받아봅니다.')+stack(
  `<div class="alert-fields">${stack(label('수신 주소',input('notify-email',n.settings.email||n.verified_email||'','email'))+
   helperText(cfg.demo?'개발 환경에서는 발송하지 않습니다.':'실제 이메일은 확인된 로그인 주소로만 발송합니다.')+
   `<label><input type="checkbox" class="ui-switch" id="notify-enabled" ${n.settings.enabled?'checked':''}> 전송 활성화</label>`)}</div>`+
  controls+(readOnly||!me.sample_tools||!sharedPreviewEnabled()?n.deliveries:n.deliveries.concat(previewData().email.deliveries)).map(d=>`<div class="line">${e(d.status)} ${e(d.error)}</div>`).join('')
 ));
};
let channelEvent=null;function channelModal(k){channelEvent=crypto.randomUUID();modal('외부 채널 메시지 검증',label('테스트 고객 ID',input('external-user','demo-user'))+label('질문',ta('external-text'))+btn('메시지 처리',`channelTest('${k}')`,'primary')+'<pre id="channel-result" class="scrolltext"></pre><p class="muted">외부 채널로 전송하지 않습니다. 실제 메시지 형식과 동일 상담 엔진을 테스트합니다.</p>')}
async function channelTest(k){await act(async()=>{let u=val('external-user'),m=val('external-text'),p=k==='naver'?{event:'send',user:u,textContent:{text:m}}:{userRequest:{user:{id:u},utterance:m}};let r=await api('/api/channels/simulate',{channel:k,event_id:channelEvent,payload:p});channelEvent=crypto.randomUUID();$('#channel-result').textContent=JSON.stringify(r,null,2)})}

let checkoutPending=null;
function checkoutSummary(order,change){
 const item=order.items;
 const rows=[];
 if(order.kind==='subscription'){
  const plan=cfg.catalog.plans.find(plan=>plan.id===item.plan);
  const addons=[...cfg.catalog.addons,...cfg.catalog.packages];
  rows.push(['상담 구독',plan?.name||item.plan]);
  if(item.addons.length)rows.push(['추가 기능',item.addons.map(id=>addons.find(addon=>addon.id===id)?.name||id).join(', ')]);
  if(item.brand_quantity)rows.push(['추가 브랜드 수량',item.brand_quantity+'개']);
  if(change){
   rows.push(['기존 월 요금',money(change.current_monthly)],['변경 후 월 요금',money(change.next_monthly)],['월 차액',money(change.monthly_delta)]);
   if(change.estimated_upgrade_proration!==null)rows.push(['잔여 기간 추가요금 참고값',money(change.estimated_upgrade_proration)]);
  }
 }else if(order.kind==='assistance'){
  rows.push(['연동 대행',Object.keys(item.details).map(k=>assistNames[k]).join(', ')],['연락 이메일',item.email]);
 }else if(order.kind==='education'){
  rows.push(['교육 크레딧',item.quantity.toLocaleString('ko-KR')+' C']);
 }else if(order.kind==='memory_import'){
  rows.push(['상품','외부 AI 기억 이전 이용권']);
 }else{
  rows.push(['메시지 충전',item.name+' · '+item.quantity.toLocaleString('ko-KR')+'건']);
 }
 return `<dl class="ui-checkout-summary">${rows.map(([name,value])=>`<div><dt>${e(name)}</dt><dd>${e(value)}</dd></div>`).join('')}
  <div class="ui-checkout-total"><dt>주문 금액</dt><dd>${money(order.amount)}</dd></div></dl>`;
}
function showCheckout(order,change=null){
 checkoutPending=order;
 modal('테스트 주문 확인',`<form class="ui-flow-body" onsubmit="event.preventDefault();finishCheckout(this)" onchange="syncCheckoutConfirmation(this)">
  ${flowNotice('테스트 환경입니다. 실제 결제되지 않습니다.','development')}
  ${checkoutSummary(order,change)}
  ${change?helperText('테스트 주문은 전체 월 요금으로 표시됩니다. 실제 일할 결제·차기 적용은 PG 연결 및 검증 후 제공됩니다.'):''}
  <a class="ui-flow-return" href="/policies/billing" target="_blank" rel="noopener">결제·해지·환불 안내 보기</a>
  ${checkbox('checkout-confirm','주문 내역과 테스트 결제임을 확인했습니다.',{className:'ui-checkout-confirm'})}
  ${flowActions('<button type="submit" class="ui-button primary" disabled>테스트 결제 완료</button>',
    btn('주문 취소','cancelCheckout(this.form)','tertiary ui-flow-secondary'))}
 </form>`,{closeLabel:'나중에 확인'});
}
function syncCheckoutConfirmation(form){
 const submit=form.querySelector('[type=submit]');
 submit.disabled=!form.querySelector('#checkout-confirm').checked||submit.hasAttribute('aria-busy');
 return !submit.disabled;
}
async function openCheckout(body,client=crypto.randomUUID()){
 const quote=await api('/api/billing/quote',body);
 const order=await api('/api/billing/orders',{...body,client});
 showCheckout(order,quote.change);
}
async function resumeCheckout(id){
 await act(async()=>{
  const history=await api('/api/billing/history');
  const order=history.orders.find(item=>item.id===id&&item.status==='pending');
  if(!order)throw Error('확인할 수 있는 대기 주문이 없습니다.');
  showCheckout(order);
 });
}
async function finishCheckout(form){
 if(!syncCheckoutConfirmation(form))return;
 const order=checkoutPending,submit=form.querySelector('[type=submit]'),cancel=form.querySelector('[type=button]');
 submit.setAttribute('aria-busy','true');
 submit.disabled=cancel.disabled=true;
 try{
  await act(async()=>{
   await api('/api/billing/orders/'+order.id+'/sandbox-confirm',{});
   form.closest('.modal')?.remove();
   await refresh();
   if(order.kind==='subscription')CSAISetup.afterPurchase();
   toast('테스트 주문 처리 완료');
   await render();
   if(order.kind==='memory_import'&&memoryTransfer&&memoryTransfer.agent===educationAgent){
    memoryTransfer.order=order.id;
    await openMemoryTransfer();
   }else if(order.kind==='subscription'){
    if(sessionStorage.getItem('assist-return:'+me.slug)){sessionStorage.removeItem('assist-return:'+me.slug);await openAssistance(true)}else await offerReadyDrafts('');
   }
  });
 }finally{
  cancel.disabled=false;
  submit.removeAttribute('aria-busy');
  syncCheckoutConfirmation(form);
 }
}
async function cancelCheckout(form){
 const order=checkoutPending,submit=form.querySelector('[type=submit]'),cancel=form.querySelector('[type=button]');
 submit.setAttribute('aria-busy','true');
 submit.disabled=cancel.disabled=true;
 try{
  await act(async()=>{
   await api('/api/billing/orders/'+order.id+'/cancel',{});
   form.closest('.modal')?.remove();
   await render();
  });
 }finally{
  cancel.disabled=false;
  submit.removeAttribute('aria-busy');
  syncCheckoutConfirmation(form);
 }
}
async function orders(){let r=await api('/api/billing/history');return pageTop('주문 및 구독 내역','테스트 결제 내역입니다. 실제 청구되지 않습니다.')+billingTabs()+card('구독 상태',r.subscription?`<p>이용 종료: ${e(new Date(r.subscription.period_end*1000).toLocaleString())}</p><p>${r.subscription.cancel_at_end?'기간 종료 후 해지 예정':'테스트 구독 · 자동 갱신 없음'}</p>${!r.subscription.cancel_at_end&&r.subscription.period_end*1000>Date.now()?btn('기간 종료 후 해지',"act(async()=>{await api('/api/billing/subscription/cancel',{});render()})"):''}`:'<p>주문으로 생성된 구독이 없습니다.</p>')+card('주문 내역',r.orders.map(o=>`<div class="line"><b>${e(o.kind==='assistance'?'연동 대행':o.kind)} · ${money(o.amount)}</b><p>${e(o.kind==='assistance'?({review:'확인 요청 접수',pending:'결제 대기',paid:'대행 접수 완료'}[o.status]||o.status):o.status)} · ${e(new Date(o.created*1000).toLocaleString())}</p>${o.status==='pending'&&me.sandbox_allowed?actionGroup({keepSize:true},btn('테스트 주문 확인',`resumeCheckout('${o.id}')`),btn('취소',`act(async()=>{await api('/api/billing/orders/${o.id}/cancel',{});render()})`),btn('결제 실패 테스트',`sandboxFail('${o.id}')`)):o.status==='paid'&&me.sandbox_allowed?btn('환불 테스트',`sandboxRefund('${o.id}')`):''}</div>`).join('')||'<p>주문 내역 없음</p>')+card('메시지 충전 잔액',r.messages.map(m=>`<p>${e(m.kind)} ${m.n}건</p>`).join('')||'<p>충전 내역 없음</p>')+card('메시지 테스트 충전',me.sandbox_allowed?cfg.catalog.messages.map((m,i)=>`<div class="row between line"><span>${e(m.name)} ${m.quantity}건 · ${money(m.price)}</span>${btn('선택',`act(async()=>{let m=cfg.catalog.messages[${i}];await openCheckout({kind:'message',name:m.name,quantity:m.quantity})})`)}</div>`).join('')+'<p class="muted">메시지 충전 후 알림 화면에서 수신 설정을 진행하세요. 실제 발송은 외부 서비스 설정 및 검증이 필요합니다.</p>':'<p>실제 결제 미연결</p>')}

async function googleCalendarModal(){await act(async()=>{let r=await api('/api/integrations/calendar');modal('구글 캘린더 연결',`<p>${r.connected?'연결됨':r.configured?'연결 준비 완료':'환경변수 설정 필요'}</p><p class="muted">연결된 기본 캘린더의 외부 일정과 예약 충돌을 확인하고, CS AI 예약을 자동 동기화할 수 있습니다.</p>${r.configured?btn('Google 권한 연결',"location.href='/auth/calendar/connect'",'primary'):''}${r.connected?btn('외부 일정 조회','previewCalendar()')+`<div class="line"><label><input class="check" type="checkbox" id="gc-auto" ${r.policy.auto_sync?'checked':''}> 예약 자동 동기화</label><label><input class="check" type="checkbox" id="gc-busy" ${r.policy.block_busy?'checked':''}> 외부 일정 충돌 차단</label><p class="muted">${r.worker_enabled?'자동 워커 설정됨':'자동 워커 환경 설정 필요'} · 조회 범위 90일 · 5분 이상 지난 외부 일정은 예약 차단</p>${r.policy.error?`<p class="error">${e(r.policy.error)}</p>`:''}${r.errors.length?`<p class="error">동기화 재확인 필요 ${r.errors.length}건</p>`:''}</div>`+actionGroup({keepSize:true},btn('자동 연동 설정 저장','saveCalendarPolicy()','primary'),btn('외부 일정 새로고침','refreshCalendarBusy()'),btn('연결 해제',"act(async()=>{await api('/api/integrations/calendar/disconnect',{});$('.modal').remove();render()})")):''}<div id="calendar-external"></div>`)})}
async function previewCalendar(){await act(async()=>{let r=await api('/api/integrations/calendar/preview');$('#calendar-external').innerHTML=r.map(x=>`<div class="line">${e(x.start.dateTime||x.start.date)} ~ ${e(x.end.dateTime||x.end.date)} ${x.owned?'· CS AI':''}</div>`).join('')||'<p>예정 일정 없음</p>'})}
async function syncCalendar(id){await act(async()=>{let r=await api('/api/integrations/calendar/sync/'+id,{});toast(r.status==='deleted'?'외부 예약 삭제 처리':'구글 캘린더 동기화 완료')})}
function kakaoChatbotNotice(){return '<div class="line"><strong>카카오톡에서도 나의 CS AI 상담사</strong><p>기존 카카오 채널에서 고객이 AI에 질문하면 CS AI에 교육한 지식과 상담 스타일을 바탕으로 답변합니다. AI로 전달된 질문과 답변은 통합 상담함에서 확인할 수 있습니다.</p><p>CS AI에서는 사람의 직접 발송을 지원하지 않습니다. 수동 상담과 수동 기록은 카카오 채널 관리자센터에서 확인하세요. 챗봇 응답 범위와 예약 화면 등은 카카오 API 지원 범위에 따릅니다.</p><a href="https://chatbot.kakao.com/" target="_blank" rel="noopener noreferrer">카카오 챗봇 관리자센터</a></div>'}
let liveChannelAgent='';
async function liveChannelModal(k,agent=''){await act(async()=>{const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available):[];let r=await api('/api/integrations/channels/'+k+'?agent='+enc(agent));liveChannelAgent=agent;modal(k==='naver'?'네이버 톡톡 연결':'카카오 AI 챗봇 연결',brandSelect('live-channel-brand',brands,agent,`liveChannelModal('${k}',this.value)`)+channelSetupGuide(k)+(k==='kakao'?kakaoChatbotNotice():'')+label(k==='naver'?'파트너 ID':'봇 ID',input('channel-partner',r.partner))+ (k==='naver'?label('보내기 API Authorization',input('channel-secret','','password')):'')+`<p class="muted">${r.configured?'HTTPS 연동 허용 환경':'실제 웹훅 비활성화 · 키 설정 및 HTTPS 필요'}</p><label><input type="checkbox" class="check" id="channel-active" ${r.active?'checked':''}> 실제 수신 활성화</label>`+btn('설정 저장',`saveLiveChannel('${k}')`,'primary')+(r.saved?label('Webhook / 스킬 URL (비공개)',input('channel-webhook',r.webhook))+btn('연결 해제',`act(async()=>{await api('/api/integrations/channels/${k}/disconnect?agent='+enc(liveChannelAgent),{});$('.modal').remove();render()})`):'')+`<p class="muted">실제 공급자 인증과 권한 검증 전 운영에 사용하지 마세요. 카카오 AI 챗봇은 승인된 콜백 설정이 필요합니다. AI에 전달된 상담만 기록하며 사람 답변 기록은 가져오지 않습니다.</p>`+r.jobs.map(j=>`<div class="line">${e(j.status)} ${e(j.error)}</div>`).join(''))})}
async function saveLiveChannel(k){await act(async()=>{await api('/api/integrations/channels/'+k,{agent:liveChannelAgent,partner:val('channel-partner'),credential:$('#channel-secret')?.value||'',active:checked('channel-active')});await liveChannelModal(k,liveChannelAgent)})}

function settingsAppearance(r){
 const logo=me.public_access?
  `<div class="logo-preview">${r.logo?`<img src="${e(r.logo)}" alt="현재 업체 로고">`:'<p class="muted">현재 기본 CS 원형 표시를 사용합니다.</p>'}</div>`:'';
 const upload=fileUpload('logo-file',{accept:'image/png,image/jpeg,image/webp',buttonText:'이미지 선택',
  description:me.public_access?'정사각형 이미지 권장 · 400KB 이하 · 채팅 상단 원형에 표시':'정사각형 이미지 권장 · 400KB 이하 · 저장 시 128×128px 이내 PNG로 변환'});
 const logoActions=actionFooter([
  btn('로고 저장','saveLogo()'),
  me.public_access&&r.logo?btn('로고 제거',"act(async()=>{await api('/api/appearance',{logo:''});render()})"):'',
 ],{divided:false});
 const design=has('design')?
  label('채팅 테마',select('chat-theme',[['dark','기존 다크'],['toss','토스형'],['messenger','메신저형'],['premium','프리미엄형']],r.theme))+
  colorField('chat-color','상담창 테마 색상',r.color)+
  label('메시지 간격',select('chat-density',chatDesignChoices.density,r.density))+
  label('말풍선 모서리',select('chat-radius',chatDesignChoices.bubble_radius,r.bubble_radius))+
  actionFooter([btn('디자인 저장',"act(async()=>{await api('/api/appearance',{color:val('chat-color'),theme:val('chat-theme'),density:val('chat-density'),bubble_radius:val('chat-radius')});await refresh();render()})",'primary')],{divided:false}):
  locked('design','상담창 테마 색상 설정');
 const brand=has('unbrand')?
  checkbox('unbrand','CS AI 브랜드 간소화 (AI 안내는 유지)',{checked:r.unbrand})+
  actionFooter([btn('저장',"act(async()=>{await api('/api/appearance',{unbrand:checked('unbrand')});render()})")],{divided:false}):
  locked('unbrand','브랜드 표시 간소화');
 const alias=has('custom_url')?
  label('지정 상담 주소 (영문 소문자/숫자)',input('alias',r.alias))+
  actionFooter([btn('주소 저장',"act(async()=>{await api('/api/appearance',{alias:val('alias')});render()})")],{divided:false})+
  (r.alias?`<p><a href="/c/${e(r.alias)}" target="_blank" rel="noopener noreferrer">/c/${e(r.alias)}</a></p>`:''):
  locked('custom_url','원하는 상담 주소 설정');
 return stack(
  section('settings-logo-heading','업체 로고',logo+upload+logoActions)+
  section('settings-design-heading','채팅 디자인',design)+
  section('settings-brand-heading','브랜드 표시',brand)+
  section('settings-alias-heading','지정 상담 주소',alias)+
  section('settings-chat-preview-heading','채팅창 디자인 미리보기',
   actionFooter([btn('채팅창 디자인 보기',"go('preview')",'primary')],{divided:false}),
   '로고와 채팅 테마를 바꾸기 전에 실제 화면에서 확인하세요.'),
  {gap:'sections'});
}
async function saveLogo(){await act(async()=>{let f=$('#logo-file').files[0];if(!f||f.size>400000)throw Error('400KB 이하 이미지 파일을 선택하세요.');let data=await new Promise((resolve,reject)=>{let r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f)});await api('/api/appearance',{logo:data});render()})}
function appearanceSelect(id,title,description,key,design){
 const control=select(id,chatDesignChoices[key],design[key])
  .replace('<select',`<select aria-describedby="${id}-hint" onchange="previewChatDesign()"`);
 return settingRow(id,title,description,control);
}
const chatColorPresets=[
 ['파랑','#3182F6'],['초록','#168048'],['보라','#7639DE'],['차콜','#191F28'],['빨강','#C83B45'],
];
function appearanceColor(color){
 return `<div class="appearance-color">
  <div class="appearance-color-custom">
   <div class="appearance-color-swatch" style="--swatch:${color}">
    <input type="color" id="chat-color-picker" value="${color}" aria-label="사용자 지정 색상 선택" title="사용자 지정 색상 선택" oninput="applyChatColor(this.value)">
   </div>
   <input id="chat-color" type="text" value="${color}" maxlength="7" aria-describedby="chat-color-hint chat-color-error" autocomplete="off" spellcheck="false" oninput="editChatColor(this)">
  </div>
  ${morphTooltipGroup('appearance-palette','추천 색상',chatColorPresets.map(([name,hex])=>
   `<button type="button" data-color="${hex}" data-morph-label="${e(name+' '+hex)}" style="--swatch:${hex}" aria-label="${e(name+' '+hex)}" aria-pressed="${hex===color}" onclick="applyChatColor(this.dataset.color)"><span aria-hidden="true"></span></button>`
  ).join(''))}
  <p class="appearance-color-error" id="chat-color-error" role="status" hidden></p>
 </div>`;
}
function appearanceSample(design,logo,brand,wave){
 return `<div class="appearance-sample"><h4>실시간 디자인 미리보기</h4>
  <div class="phone appearance-sample-chat ${chatDesignClasses(design).join(' ')}" style="--chat-color:${design.color}">
   <div class="phone-head"><div class="avatar">${appearanceImage(logo,'<span>CS</span>')}</div><div class="phone-identity">${chatBrandName(brand,wave)}</div></div>
   <div class="messages">${bubble('assistant','안녕하세요. 무엇을 도와드릴까요?')}${bubble('user','상품을 문의하고 싶어요.')}</div>
  </div>
 </div>`;
}
function appearanceImage(src,fallback){
 return src?`<img src="${e(src)}" alt="">`:fallback;
}
function chatBrandWaveSetting(wave,agent=''){
 const id='chat-brand-wave';
 return settingRow(id,'업체 이름 강조 효과','고객 채팅창을 열면 업체 이름이 한 번 강조됩니다. 변경하면 바로 저장돼요.',
  `<input type="checkbox" class="ui-switch" role="switch" id="${id}" aria-describedby="${id}-hint" data-agent="${e(agent)}" onchange="saveChatBrandWave(this)"${wave!==false?' checked':''}>`);
}
async function saveChatBrandWave(field){
 const enabled=field.checked;
 if(field.getAttribute('aria-busy')==='true'){field.checked=!enabled;return;}
 const names=document.querySelectorAll('.preview-stage .chat-brand-name, .appearance-sample-chat .chat-brand-name');
 field.setAttribute('aria-busy','true');
 field.setAttribute('aria-disabled','true');
 for(const name of names)name.classList.toggle('has-name-wave',enabled);
 try{
  await api('/api/appearance',{agent:field.dataset.agent,brand_name_wave:enabled});
  toast(enabled?'업체 이름 강조 효과를 켰습니다.':'업체 이름 강조 효과를 껐습니다.');
 }catch(error){
  field.checked=!enabled;
  for(const name of names)name.classList.toggle('has-name-wave',!enabled);
  toast(error.message);
 }finally{
  field.removeAttribute('aria-busy');
  field.removeAttribute('aria-disabled');
 }
}
function previewAppearance(r,brand){
 const design=chatDesign(r),canDesign=has('design');
 return `<details class="card app-card preview-appearance"><summary><strong>업체 이미지·채팅 디자인</strong><span>로고 및 채팅 테마</span>${uiIcon('chevron-down')}</summary>
  <div class="preview-appearance-body">
   <section class="appearance-section" aria-labelledby="appearance-logo-heading">
    <h3 id="appearance-logo-heading">업체 로고</h3>
    ${fileUpload('logo-file',{accept:'image/png,image/jpeg,image/webp',thumbnail:appearanceImage(r.logo,uiIcon('image')),buttonText:'이미지 선택',description:'무료 · 정사각형 권장 · PNG, JPG, WebP · 최대 400KB',onChange:'previewLogo(this)'})}
    ${actionFooter([
     `<button type="button" class="ui-button tertiary" data-logo-remove onclick="updatePreviewLogo(this,true)" ${r.logo?'':'hidden'}>로고 제거</button>`,
     '<button type="button" class="ui-button secondary" data-logo-save onclick="updatePreviewLogo(this)" disabled>로고 저장</button>',
    ],{divided:false})}
   </section>
   <section class="appearance-section" aria-labelledby="appearance-design-heading">
    <h3 id="appearance-design-heading">채팅 디자인</h3>
    <div class="ui-setting-list">
     ${appearanceSelect('chat-theme','채팅 테마','채팅창의 기본 분위기','theme',design)}
     ${settingRow('chat-color','테마 색상','전송 버튼과 말풍선에 쓰는 강조 색상',appearanceColor(design.color))}
     ${appearanceSelect('chat-density','메시지 간격','말풍선 사이의 여백','density',design)}
     ${appearanceSelect('chat-radius','말풍선 모서리','말풍선의 둥근 정도','bubble_radius',design)}
     ${chatBrandWaveSetting(r.brand_name_wave)}
    </div>
    ${appearanceSample(design,r.logo,brand,r.brand_name_wave)}
    ${actionFooter([
     btn('기본값 복원','resetChatDesign()','tertiary'),
     canDesign?btn('디자인 저장','saveChatDesign(this)','primary'):btn('고급 디자인 옵션 보기',"go('addons')"),
    ],{note:canDesign?'':'디자인 저장은 유료 옵션입니다.'})}
   </section>
  </div></details>`;
}
function previewChatDesign(){
 const design=chatDesign({
  theme:val('chat-theme'),color:val('chat-color-picker'),density:val('chat-density'),bubble_radius:val('chat-radius'),
 });
 for(const phone of document.querySelectorAll('.preview-stage .phone, .appearance-sample-chat')){
  for(const name of [...phone.classList]){
   if(/^(theme|density|radius)-/.test(name))phone.classList.remove(name);
  }
  phone.classList.add(...chatDesignClasses(design));
  phone.style.setProperty('--chat-color',design.color);
 }
}
function applyChatColor(value){
 const color=value.toUpperCase();
 $('#chat-color-picker').value=color;
 $('#chat-color').value=color;
 $('.appearance-color-swatch').style.setProperty('--swatch',color);
 for(const swatch of document.querySelectorAll('.appearance-palette [data-color]')){
  swatch.setAttribute('aria-pressed',swatch.dataset.color===color);
 }
 validateChatColor($('#chat-color'));
 previewChatDesign();
}
function editChatColor(field){
 const color=field.value.trim().replace(/^#?/,'#');
 if(/^#[0-9a-f]{6}$/i.test(color))applyChatColor(color);
}
function validateChatColor(field){
 const valid=/^#[0-9a-f]{6}$/i.test(field.value);
 if(valid)field.removeAttribute('aria-invalid');
 else field.setAttribute('aria-invalid','true');
 const hint=$('#chat-color-error');
 hint.textContent=valid?'':'HEX 색상은 # 뒤에 영문 A–F 또는 숫자 6자리를 입력하세요.';
 hint.hidden=valid;
 return valid;
}
function resetChatDesign(){
 $('#chat-theme').value=chatDesignDefaults.theme;
 $('#chat-density').value=chatDesignDefaults.density;
 $('#chat-radius').value=chatDesignDefaults.bubble_radius;
 applyChatColor(chatDesignDefaults.color);
}
function showPreviewLogo(panel,src){
 panel.querySelector('.ui-file-thumbnail').innerHTML=appearanceImage(src,uiIcon('image'));
 for(const avatar of document.querySelectorAll('.preview-stage .phone .avatar, .appearance-sample-chat .avatar')){
  avatar.innerHTML=appearanceImage(src,'<span>CS</span>');
 }
}
function readLogoFile(file){
 return new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onload=()=>resolve(reader.result);
  reader.onerror=()=>reject(Error('이미지 파일을 읽을 수 없습니다.'));
  reader.readAsDataURL(file);
 });
}
async function previewLogo(field){
 const file=field.files[0],panel=field.closest('.preview-appearance');
 if(!file)return;
 const save=panel.querySelector('[data-logo-save]'),status=panel.querySelector('#logo-file-status');
 panel.savedLogo??=panel.querySelector('.appearance-sample-chat .avatar img')?.getAttribute('src')||'';
 save.disabled=true;
 status.textContent='';
 try{
  if(file.size>400000)throw Error('400KB 이하의 이미지를 선택하세요.');
  const src=await readLogoFile(file),image=new Image();
  image.src=src;
  await image.decode().catch(()=>{throw Error('유효한 이미지 파일을 선택하세요.')});
  if(!field.isConnected||field.files[0]!==file)return;
  showPreviewLogo(panel,src);
  status.textContent=file.name;
  status.dataset.error='false';
  save.disabled=false;
 }catch(error){
  if(!field.isConnected||field.files[0]!==file)return;
  field.value='';
  showPreviewLogo(panel,panel.savedLogo);
  status.textContent=error.message;
  status.dataset.error='true';
 }
}
async function updatePreviewLogo(button,remove=false){
 const panel=button.closest('.preview-appearance'),field=panel.querySelector('#logo-file');
 const save=panel.querySelector('[data-logo-save]'),removeButton=panel.querySelector('[data-logo-remove]');
 const picker=panel.querySelector('.ui-file-details button'),status=panel.querySelector('#logo-file-status');
 const file=field.files[0];
 if(!remove&&!file)return;
 const existing=panel.savedLogo??panel.querySelector('.appearance-sample-chat .avatar img')?.src??'';
 for(const control of [save,removeButton,picker])control.disabled=true;
 button.setAttribute('aria-busy','true');
 try{
  const logo=remove?'':(await readLogoFile(file)).split(',')[1];
  await api('/api/appearance',{logo});
  const saved=remove?'':(await api('/api/appearance')).logo;
  if(!panel.isConnected)return;
  panel.savedLogo=saved;
  showPreviewLogo(panel,saved);
  field.value='';
  removeButton.hidden=!saved;
  status.textContent=remove?'로고를 제거했습니다.':'로고를 저장했습니다.';
  status.dataset.error='false';
  picker.disabled=false;
  picker.focus();
 }catch(error){
  status.textContent=error.message;
  status.dataset.error='true';
  if(!field.files[0])showPreviewLogo(panel,existing);
 }finally{
  save.disabled=!field.files[0];
  removeButton.disabled=false;
  picker.disabled=false;
  button.removeAttribute('aria-busy');
 }
}
async function saveChatDesign(button){
 const field=$('#chat-color');
 if(!validateChatColor(field)){field.focus();return;}
 const design=chatDesign({color:field.value,theme:val('chat-theme'),density:val('chat-density'),bubble_radius:val('chat-radius')});
 button.disabled=true;
 button.setAttribute('aria-busy','true');
 try{
  await act(async()=>{
   await api('/api/appearance',design);
   toast('채팅 디자인을 저장했습니다.');
  });
 }finally{
  button.disabled=false;
  button.removeAttribute('aria-busy');
 }
}
function agentUseCases(){
 return `<section class="card agent-guide"><h2>언제 추가 브랜드 상담원이 필요한가요?</h2><p>기본 상담원 한 명으로 하나의 업체를 상담한다면 추가하지 않아도 됩니다. 네이버·카카오·홈페이지에서 같은 내용으로 상담할 때도 기본 상담원을 쓰면 됩니다.</p><div class="agent-use-grid"><div><strong>예: 촬영 서비스가 두 종류일 때</strong><p>기본 상담원은 가족사진, 추가 브랜드 상담원은 웨딩 촬영을 맡깁니다. 고객에게 서로 다른 상담 링크를 안내하고 첫 인사·말투·교육 지식을 따로 관리합니다.</p></div><div><strong>두 번째 상담원이 하는 일</strong><p>별도 상담 링크에서 응대합니다. 상담량과 교육 크레딧은 계정에서 공유합니다. 브랜드별 예약·CRM 및 외부 채널 분리는 준비 중입니다. 자동으로 네이버·카카오 문의를 나누지는 않습니다.</p></div></div><p class="muted">추가 브랜드 상담원은 구매 수량만큼 만들 수 있습니다. 기존 상담원은 그대로 유지됩니다.</p></section>`
}
async function agents(){
 let intro=pageTop('AI 상담원 관리','업체 안에서 상담 주제나 브랜드를 나눠 운영할 때 사용하세요.')+agentUseCases();
 const readOnly=!has('extra_agent');
 if(readOnly&&!freeFeaturePreview())return intro+locked('extra_agent','다른 브랜드·사업의 전용 상담 링크와 독립적인 말투·교육 지식이 필요할 때 추가하세요. 한 브랜드의 여러 업무에는 기본 상담원 하나면 충분합니다.');
 if(readOnly)intro+=previewNotice('extra_agent','추가 브랜드 상담원 설정 체험');
 let r=readOnly?{agents:[],quantity:0}:await api('/api/agents/list'),brands=r.agents.filter(x=>x.available),a=brandEditor==='new'?null:(brands.find(x=>x.id===brandEditor)||brands[0]);brandEditor=a?.id||'new';let s=a?.settings||{brand:'추가 브랜드 상담원',tone:'자연스럽고 정중하게',prompt:'등록된 정책으로만 상담하세요.',welcome:'안녕하세요. 무엇을 도와드릴까요?',fallback:'담당자 확인이 필요합니다.',emoji:false};
 let form=card('추가 브랜드 상담원 설정',label('브랜드 이름',input('agent-brand',s.brand))+label('업종 (쉼표 구분)',ta('agent-industries',(s.industries||[]).join(', ')))+label('업무 (쉼표 구분)',ta('agent-work',(s.desired_work||[]).join(', ')))+label('상담 방식',select('agent-consultation',[['ai','AI 우선'],['staff','담당자 직접 상담']],s.consultation_mode||'ai'))+label('상품·가격 안내',ta('agent-price',s.price||''))+label('위치 안내',ta('agent-location',s.location||''))+label('영업시간',ta('agent-hours',s.hours||''))+label('공지',ta('agent-notice',s.notice||''))+label('판매처 링크 (이름 | HTTPS 주소)',ta('agent-links',(s.links||[]).map(x=>x.name+' | '+x.url).join('\n')))+label('말투',input('agent-tone',s.tone))+label('첫 인사',input('agent-welcome',s.welcome))+label('모르는 질문 안내',ta('agent-fallback',s.fallback))+`<div class="agent-toggle-row"><label><input class="check" id="agent-emoji" type="checkbox" ${s.emoji?'checked':''}> 이모지 사용</label><label><input type="checkbox" class="ui-switch" id="agent-enabled" ${a?.enabled?'checked':''}> 추가 브랜드 상담원 공개</label></div>`  +btn('저장','saveAgent()','primary')+(a?btn('채팅창 프로필 설정',`openProfileEditor('${a.id}')`):'')+(a?btn(a.archived?'보관 복구':'브랜드 보관',`archiveBrand('${a.id}',${!a.archived})`):'')+(a?`<p>별도 상담 주소: <a href="/c/${e(a.slug)}" target="_blank" rel="noopener noreferrer">/c/${e(a.slug)}</a></p><p class="muted">채팅창 미리보기 및 상담 테스트에서 브랜드를 선택하세요. 상담 내역은 업체의 통합 상담함에 함께 쌓입니다.</p>${actionGroup({keepSize:true},btn('관리자 테스트',`previewAgent='${a.id}';chatSession=null;chatMessages=[];go('test')`),btn('추가 브랜드 상담원 채팅창 열기',`window.open('/c/${e(a.slug)}','_blank','noopener')`,'primary'))}`:'')+'<p class="muted">교육 지식과 기본 사업 정보는 브랜드별로 분리되며, 상담량과 교육 크레딧은 계정 공통입니다.</p>');
 let training=a?card('추가 브랜드 상담원 교육',`<p class="muted">AI 교육 화면에서 이 상담원을 선택해 별도 자료와 말투를 가르치세요. 교육 크레딧은 업체 공통 잔액에서 차감됩니다.</p>`+btn('이 상담원 교육하기',`educationAgent='${a.id}';trainingChat=[];estimate=null;resetEducationDraft();$('#education-workspace')?.remove();go('education')`,'primary')+`<pre class="scrolltext">${e(JSON.stringify(a.published,null,2))}</pre>`+(await api('/api/agents/versions')).map(v=>btn(new Date(v.created*1000).toLocaleString()+' 복원',`act(async()=>{await api('/api/agents/versions/${v.id}/restore',{});render()})`)).join('')):'';
 return intro+card('브랜드 목록',`<p>구매한 추가 브랜드 ${r.quantity}개 · 등록 ${brands.length}개</p>${brands.map(x=>btn(x.settings.brand+(x.archived?' · 보관':''),`brandEditor='${x.id}';render()`)).join('')}${brands.length<r.quantity?btn('새 브랜드 등록',"brandEditor='new';render()",'primary'):btn('브랜드 수량 추가',"go('pricing')")}`)+form+training;
}

async function saveAgent(){if(!requirePreviewAccess('extra_agent'))return;await act(async()=>{let saved=await api('/api/agents',{id:brandEditor==='new'?'':brandEditor,create:brandEditor==='new',brand:val('agent-brand'),industries:val('agent-industries').split(',').map(x=>x.trim()).filter(Boolean),desired_work:val('agent-work').split(',').map(x=>x.trim()).filter(Boolean),consultation_mode:val('agent-consultation'),price:val('agent-price'),location:val('agent-location'),hours:val('agent-hours'),notice:val('agent-notice'),links:val('agent-links').split('\n').filter(x=>x.trim()).map(x=>{let [name,url]=x.split('|').map(y=>y.trim());return {name,url}}),tone:val('agent-tone'),welcome:val('agent-welcome'),fallback:val('agent-fallback'),emoji:checked('agent-emoji'),enabled:checked('agent-enabled')});brandEditor=saved.id;render()})}

function showWorkDraft(w){$('#work-draft')?.remove();$('#messages').insertAdjacentHTML('beforeend',`<section id="work-draft" class="card booking-form"><h3>업무 요청 내용 확인</h3>${label('제목',input('draft-title',w.title))}${label('상세 내용',ta('draft-detail',w.details))}${actionGroup({keepSize:true},btn('확인 및 접수',`submitWorkDraft('${w.kind}')`,'primary'),btn('닫기',"$('#work-draft').remove()"))}</section>`)}
/* v0.5: direct examples are a real training job, never an immediate free knowledge write. */
async function invites(){let rows=await api('/api/operator/invites');return pageTop('초청 및 체험 관리','발급 직후에만 원문 코드를 확인할 수 있습니다.')+card('초청 링크 발급',label('상담 체험',select('invite-chat',[['50','50회'],['100','100회'],['300','300회']],'50'))+label('교육 크레딧',input('invite-credit','100','number'))+label('체험 기간 (1~30일)',input('invite-days','14','number'))+btn('1회용 링크 발급','createInvite()','primary'))+card('발급 내역',rows.map(x=>`<div class="line"><b>${e(x.chat_limit)}회 · ${e(x.credit_limit)}C · ${e(x.days)}일</b><p class="muted">${x.revoked?'회수됨':x.used_by?'사용 완료':'수락 대기'} · 수락 기한 ${new Date(x.expires*1000).toLocaleString()}</p>${!x.revoked?btn('회수',`act(async()=>{await api('/api/operator/invites/${x.id}/revoke',{});render()})`):''}</div>`).join('')||emptyState('아직 발급한 초청 링크가 없습니다.'))}
async function createInvite(){await act(async()=>{let x=await api('/api/operator/invites',{chat_limit:Number(val('invite-chat')),credit_limit:Number(val('invite-credit')),days:Number(val('invite-days'))});modal('초청 링크를 지금 복사하세요',`<div class="invite-reveal"><div class="invite-badges" aria-hidden="true"><span>업체</span><span>CS AI</span><span>체험</span></div><p>1회용 초청 링크가 발급됐습니다. 이 코드는 다시 표시되지 않습니다. 링크를 전달받은 업체가 Google 로그인 후 체험을 수락할 수 있습니다.</p>${label('초청 링크',input('invite-code',location.origin+x.accept_path))}${copyButton('초청 링크 복사','invite-code','primary')}<small>메일은 자동으로 발송되지 않습니다. 복사한 링크를 직접 전달하세요.</small></div>`);render()})}
async function costs(){let x=await api('/api/operator/costs');return pageTop('사용량 및 원가','운영자 전용 · 모의 사용량은 실제 매출이나 원가에 포함하지 않습니다.')+card('모델 설정',`<p>교육: ${e(x.models.training)} · 상담: ${e(x.models.chat)}</p><p class="muted">공식 단가 기준의 추정치이며, 실제 청구서·세금·서버비와 다를 수 있습니다.</p>`)+card('모델 사용량',table(['유형','모델','모드','입력','출력','추정 USD'],x.rows.map(r=>[r.kind,r.model,r.mode,Number(r.input_tokens).toLocaleString(),Number(r.output_tokens).toLocaleString(),Number(r.estimated_cost_usd).toFixed(6)])))}
async function submitWorkDraft(k){await act(async()=>{let r=await api('/api/customer/requests',{token:chatSession,kind:k,title:val('draft-title'),details:val('draft-detail'),confirmed:true});$('#work-draft').innerHTML=`<p>${r.duplicate?'이미 접수된 요청입니다.':'요청이 접수되었습니다. 담당자 확인 후 안내드립니다.'}</p>`})}

window.addEventListener('hashchange',()=>{if(!publicMode){if(location.hash!=='#test'){chatSession=null;chatMessages=[]}if(location.hash!=='#fields')fields=null;if(location.hash!=='#settings')settingsStackPage='root';render()}});init();

async function issueRecovery(id){if(!confirm('기존 복구 코드가 있다면 폐기됩니다. 새 코드를 발급할까요?'))return;await act(async()=>{let r=await api('/api/customer/bookings/'+id+'/recovery-code',{token:await getChatSession()});modal('예약 복구 코드',`<p>다른 기기에서 이 예약만 불러올 수 있는 일회용 코드입니다. 누구에게도 공유하지 마세요. 기존 상담 내용은 이전되지 않습니다.</p>${input('recovery-issued',r.code)}<p class="muted">만료: ${e(new Date(r.expires*1000).toLocaleString())}</p>${copyButton('코드 복사','recovery-issued')}`)})}
function recoverModal(){modal('예약 불러오기',label('예약 복구 코드',input('recovery-code'))+'<p class="muted">동일 업체의 상담 링크에서 발급받은 코드를 입력하세요. 이 기기로 예약 관리 권한이 이전됩니다.</p>'+btn('예약 불러오기',"act(async()=>{await api('/api/customer/bookings/recover',{token:await getChatSession(),code:val('recovery-code').trim()});toast('예약 불러오기 완료');customerBookings()})",'primary'))}

function showEducationQuote(q){modal('AI 교육 비용 확인',`<p>최대 ${q.maxCredits} C 예약 · 보유 ${q.credits} C</p><p>분석을 시작하면 실제 사용량만 차감됩니다. 초안을 직접 수정하거나 승인할 때에는 추가 차감이 없습니다.</p>${q.enough?btn('교육 시작',`act(async()=>{let r=await api('/api/training/${q.id}/run',{});$('.modal')?.remove();await refresh();toast('교육 결과 생성 · '+r.cost+' C');if(route==='education')render();else go('education')})`,'primary'):btn('크레딧 충전',"$('.modal')?.remove();go('credits')")}`)}

function developerSetupStatus({scopes,keys}){
 const active=keys.filter(key=>!key.revoked);
 return {scopes:scopes.length,active:active.length,used:active.filter(key=>key.last_used).length};
}
function developerTaskList(summary,{state='',note=''}={}){
 const tasks=[
  {label:'외부 API 이용 권한',status:'done',note:'사용 가능',children:[
   {label:'사용 가능한 API 권한',status:summary.scopes?'done':'pending',note:summary.scopes+'개'},
  ]},
  {label:'API 키 발급',status:state||(summary.active?'done':'pending'),note:note||(summary.active+'개 활성')},
  {label:'활성 키 사용 기록',status:summary.used?'done':'pending',note:summary.used?summary.used+'개 키 사용':'첫 요청 대기'},
 ];
 const count=tasks.flatMap(task=>[task,...(task.children||[])]);
 const names={pending:'대기',running:'진행 중',done:'완료',failed:'실패'};
 const row=task=>`<li class="dev-task" data-state="${task.status}">
  <div class="dev-task-row"${task.status==='running'?' aria-current="step"':''}>
   <svg class="dev-task-mark" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
    <rect x="1.5" y="1.5" width="13" height="13" rx="4"></rect>
    ${task.status==='done'?'<path class="dev-task-check" d="m4.5 8 2.4 2.4 4.6-4.8" pathLength="1"></path>':
     task.status==='failed'?'<path d="M6 6l4 4m0-4-4 4"></path>':''}
   </svg>
   <span class="dev-task-name">${e(task.label)} <small class="dev-task-state">${names[task.status]}</small></span>
   <span class="dev-task-note">${e(task.note)}</span>
  </div>
  ${task.children?`<ol>${task.children.map(row).join('')}</ol>`:''}
 </li>`;
 return `<p class="ui-helper dev-task-count" role="status">${count.filter(task=>task.status==='done').length} / ${count.length} 완료</p><ol class="dev-task-list">${tasks.map(row).join('')}</ol>`;
}
function developerKeyList(keys){
 return keys.map(k=>`<div class="line"><b>${e(k.label)}</b><p>${e(k.scopes.join(', '))} · ${k.revoked?'폐기됨':'활성'}</p>
  ${!k.revoked?btn('폐기',`act(async()=>{await api('/api/developer/keys/${e(k.id)}/revoke',{});render()})`):''}</div>`).join('')
  ||emptyState('발급한 키가 없습니다.');
}
async function developer(){
 const readOnly=!has('external_api');if(readOnly&&!freeFeaturePreview())return pageTop('개발자 센터','구매한 기능을 외부 서비스에서 호출합니다.')+locked('external_api','API 키와 상담·예약·업무·교육 API를 제공합니다.');
 const x=readOnly?{scopes:[],keys:[]}:await api('/api/developer/keys');
 const summary=developerSetupStatus(x);
 const tasks=card('API 연동 체크리스트',`<div id="developer-tasks" data-summary="${e(JSON.stringify(summary))}">${readOnly?helperText('구독 후 API 권한 및 키 발급 상태를 확인할 수 있습니다.'):developerTaskList(summary)}</div>`+
  actionFooter([btn('상태 새로고침','refreshDeveloperTasks(this)','secondary ui-sm')],{divided:false}));
 const form=card('API 키 발급',`<form onsubmit="event.preventDefault();createDevKey(this)">
  ${label('키 이름',input('dev-key-name','외부 서비스'))}
  <fieldset class="ui-fieldset developer-scopes"><legend>API 권한</legend>
   ${x.scopes.map((s,i)=>checkbox('dev-scope-'+i,s,{className:'developer-scope'}).replace('type="checkbox"',`type="checkbox" name="scope" value="${e(s)}"`)).join('')}
  </fieldset>
  ${actionFooter(['<button id="dev-issue-button" class="ui-button primary" type="submit">API 키 발급</button>'],{divided:false})}
 </form>`);
 return (readOnly?previewNotice('external_api','API 연동 화면 체험'):'')+pageTop('개발자 센터','서버 전용 API 키 · 기존 상담량 및 교육 크레딧 사용')+
  splitContent(tasks,form,{balanced:true})+
  card('API 키 관리',`<div id="developer-key-list">${developerKeyList(x.keys)}</div>`)+
  card('개발 문서','<p>Authorization: Bearer YOUR_KEY</p><p>POST /v1/chat/sessions → POST /v1/chat</p><p>구매 기능에 따라 예약, 업무, 교육, 통계 API를 사용할 수 있습니다.</p><a href="/api/docs" target="_blank" rel="noopener noreferrer">API 문서 열기</a><p class="muted">키는 서버 환경변수에 보관하고 브라우저 코드에 노출하지 마세요.</p>');
}
async function refreshDeveloperTasks(button){
 if(!requirePreviewAccess('external_api'))return;
 const panel=$('#developer-tasks'),issue=$('#dev-issue-button');
 if(button.disabled||issue.disabled)return;
 button.disabled=true;button.setAttribute('aria-busy','true');
 try{
  const x=await api('/api/developer/keys');
  if(!panel.isConnected||issue.disabled)return;
  const summary=developerSetupStatus(x);
  panel.dataset.summary=JSON.stringify(summary);
  panel.innerHTML=developerTaskList(summary);
  $('#developer-key-list').innerHTML=developerKeyList(x.keys);
 }catch(error){toast(error.message);}
 finally{button.disabled=false;button.removeAttribute('aria-busy');}
}
async function createDevKey(form){
 if(!requirePreviewAccess('external_api'))return;
 const button=form.querySelector('[type="submit"]');
 const panel=$('#developer-tasks');
 if(button.disabled||!panel)return;
 const summary=JSON.parse(panel.dataset.summary);
 const owner=me?.slug;
 button.disabled=true;button.setAttribute('aria-busy','true');
 panel.innerHTML=developerTaskList(summary,{state:'running',note:'발급 요청 중'});
 try{
  const r=await api('/api/developer/keys',{label:val('dev-key-name'),scopes:new FormData(form).getAll('scope')});
  if(me?.slug!==owner)return;
  modal('API 키 발급 완료',`<p>지금 한 번만 확인할 수 있습니다. 안전하게 보관하세요.</p>${input('issued-dev-key',r.key)}${copyButton('복사','issued-dev-key')}`);
  if(panel.isConnected)await render();
 }catch(error){
  if(panel.isConnected)panel.innerHTML=developerTaskList(summary,{state:'failed',note:error.message});
  toast(error.message);
 }finally{button.disabled=false;button.removeAttribute('aria-busy');}
}

async function importEducationUrl(){await act(async()=>{if(educationBusy)return;const url=val('education-url');educationBusy=true;try{let r=await api('/api/files/url',{url,agent:educationAgent});toast(r.duplicate?'이미 등록된 자료입니다.':'웹페이지 자료 등록 완료');if(route==='education')await render()}finally{educationBusy=false;renderEducationQuote()}})}

async function saveCalendarPolicy(){await act(async()=>{await api('/api/integrations/calendar/policy',{auto_sync:checked('gc-auto'),block_busy:checked('gc-busy')});toast('캘린더 설정 저장 완료');googleCalendarModal()})}
async function refreshCalendarBusy(){await act(async()=>{let r=await api('/api/integrations/calendar/refresh',{});toast('외부 일정 '+r.count+'건 확인');googleCalendarModal()})}

let crmAgent='';
function workPath(id=''){return '/api/work'+(id?'/'+enc(id):'')+'?agent='+enc(crmAgent)}
function leadPath(id=''){return '/api/leads'+(id?'/'+enc(id):'')+'?agent='+enc(crmAgent)}
function crmPath(id=''){return '/api/crm/contacts'+(id?'/'+enc(id):'')+'?agent='+enc(crmAgent)}
async function crmPanel(){let brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available):[];if(crmAgent&&!brands.some(x=>x.id===crmAgent))crmAgent='';let contacts=has('crm')?await api(crmPath()):previewData().contacts;if(has('crm')&&me.sample_tools&&sharedPreviewEnabled()&&!crmAgent)contacts=contacts.concat(previewData().contacts);let archived=brands.some(x=>x.id===crmAgent&&x.archived);return card('고객 CRM','<p class="muted">고객 정보와 업무는 선택 브랜드에만 표시됩니다.</p>'+(archived?'<p>보관된 브랜드 · 조회 및 삭제만 가능</p>':btn('고객 등록','crmEdit()','primary'))+contacts.map(x=>`<div class="line${sampleRecord(x)?' sample-record':''}"><b>${e(sampleTitle(x.name,sampleRecord(x)))}</b><p>${e([x.email,x.phone].filter(Boolean).join(' · '))}</p><p>${e(x.notes)}</p>${x.threads.map(t=>btn('상담 이력',`inboxAgent=crmAgent;threadId='${t.thread}';go('inbox')`)).join('')}${actionGroup({keepSize:true},archived?'':btn('수정',`crmEdit('${x.id}')`),btn('삭제',`crmDelete('${x.id}',this)`))}</div>`).join(''))}
async function crmEdit(id=''){if((!has('crm')&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))){const x=previewData().contacts.find(z=>z.id===id)||{};modal('샘플 고객 등록·수정',helperText('실제 개인정보를 입력하지 마세요.')+label('이름',input('crm-name',x.name||''))+label('메모',ta('crm-notes',x.notes||''))+btn('저장',`saveCrm('${id}')`,'primary'));return;}if(!requirePreviewAccess('crm'))return;await act(async()=>{let items=await api(crmPath()),x=items.find(z=>z.id===id)||{},threads=(await api('/api/inbox?agent='+enc(crmAgent))).filter(t=>t.kind!=='test'&&!t.sample);if(id&&!x.id)throw Error('고객 정보 없음');modal(id?'고객 정보 수정':'고객 등록',label('이름',input('crm-name',x.name||''))+label('이메일',input('crm-email',x.email||'','email'))+label('연락처',input('crm-phone',x.phone||''))+label('메모',ta('crm-notes',x.notes||''))+label('연결할 상담',select('crm-thread',[['','선택 안 함'],...threads.map(t=>[t.id,(t.last||'고객 상담').slice(0,50)])],''))+btn('저장',`saveCrm('${id}')`,'primary'))})}
async function saveCrm(id){if((!has('crm')&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))){if(!val('crm-name').trim())return toast('이름을 입력하세요.');previewUpsert(previewData().contacts,id,{name:'샘플 · '+val('crm-name').replace(/^샘플 · /,''),notes:val('crm-notes'),email:'',phone:'',threads:[]});$('.modal')?.remove();render();return;}if(!requirePreviewAccess('crm'))return;await act(async()=>{await api(crmPath(id),{agent:crmAgent,name:val('crm-name'),email:val('crm-email'),phone:val('crm-phone'),notes:val('crm-notes'),thread:val('crm-thread')},id?'PATCH':'POST');$('.modal').remove();render()})}
async function crmDelete(id,button){if((!has('crm')&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))){const data=previewData();data.contacts=data.contacts.filter(x=>x.id!==id);render();return;}if(confirm('고객 정보만 삭제하고 상담 내역은 유지할까요?'))await deleteVisibleRow(crmPath(id),button);}
async function leadPanel(archived=false){let xs=has('leads')?await api(leadPath()):[],labels={inquiry:'일반 문의',interested:'관심 고객',ready:'구매·예약 의사'};return card('잠재 고객 자동 분류',`<p class="muted">실제 상담의 구매 의사에 따라 분류하며, 담당자가 수정할 수 있습니다.</p>`+xs.map(x=>`<div class="line"><b>${e(labels[x.stage]||x.stage)}</b><p class="muted">${e(x.source==='ai'?'AI 분류':x.source==='staff'?'담당자 분류':'규칙 기반 분류')}</p>${archived?'':select('lead-'+x.thread,Object.entries(labels),x.stage)+btn('분류 저장',`saveLead('${x.thread}')`)}${btn('상담 열기',`inboxAgent=crmAgent;threadId='${x.thread}';go('inbox')`)}</div>`).join(''))}
async function saveLead(id){await act(async()=>{await api(leadPath(id),{stage:val('lead-'+id)},'PATCH');render()})}
function quotePath(path){return '/api/quotes/'+path+'?agent='+enc(crmAgent)}
async function quotePanel(list,archived=false){let items=has('quote')?await api(quotePath('items')):previewData().quoteItems,offers=has('quote')?await api(quotePath('offers')):previewData().quoteOffers;if(has('quote')&&me.sample_tools&&sharedPreviewEnabled()&&!crmAgent){items=items.concat(previewData().quoteItems);offers=offers.concat(previewData().quoteOffers);}return card('견적 상품·가격 관리',(archived?'<p>보관된 브랜드 · 조회만 가능</p>':label('상품명',input('quote-item-name'))+label('원화 단가',input('quote-item-price','','number'))+btn('상품 등록','saveQuoteItem()','primary'))+items.map(x=>`<div class="line${sampleRecord(x)?' sample-record':''}"><b>${e(sampleTitle(x.name,sampleRecord(x)))} · ${money(x.price)}</b> ${e(x.active?'판매 중':'중지')} ${archived?'':btn('수정',`quoteItemEdit('${x.id}')`)}</div>`).join(''))+card('견적서 작성 및 전송',`<p class="muted">등록된 단가로 계산합니다. 담당자 승인 전에는 고객에게 금액을 전송하지 않습니다.</p>`+list.filter(x=>x.kind==='quote'&&!x.sample).map(x=>`<div class="line"><b>${e(x.title)}</b><p>${e(x.details)}</p>${archived?'':btn('견적서 작성',`quoteCompose('${x.id}')`)}</div>`).join('')+offers.map(x=>`<div class="line${sampleRecord(x)?' sample-record':''}"><b>${money(x.amount)}</b><p>${e(x.items.map(z=>z.name+' × '+z.quantity).join(', '))}</p><small>${x.status==='sent'?'전송 완료':'검토 대기'}</small>${!archived&&x.status==='draft'?btn('고객에게 전송',x.id.startsWith('preview-')?`previewSendQuote('${x.id}')`:`sendQuote('${x.id}')`,'primary'):''}</div>`).join(''))}
async function saveQuoteItem(){if(!has('quote')&&freeFeaturePreview()){if(!val('quote-item-name').trim())return toast('상품명을 입력하세요.');previewUpsert(previewData().quoteItems,'',{name:'샘플 · '+val('quote-item-name'),price:Number(val('quote-item-price')),active:true});render();return;}if(!requirePreviewAccess('quote'))return;await act(async()=>{await api(quotePath('items'),{name:val('quote-item-name'),price:Number(val('quote-item-price'))});render()})}
async function quoteItemEdit(id){if((!has('quote')&&freeFeaturePreview())||(me.sample_tools&&sharedPreviewEnabled()&&String(id).startsWith('preview-'))){const x=previewData().quoteItems.find(z=>z.id===id);if(!x)return;modal('샘플 견적 상품 수정',label('상품명',input('qe-name',x.name))+label('단가',input('qe-price',x.price,'number'))+btn('저장',`savePreviewQuoteItem('${id}')`,'primary'));return;}await act(async()=>{let x=(await api(quotePath('items'))).find(z=>z.id===id);modal('견적 상품 수정',label('상품명',input('qe-name',x.name))+label('단가',input('qe-price',x.price,'number'))+`<label><input class="check" type="checkbox" id="qe-active" ${x.active?'checked':''}> 판매 중</label>`+btn('저장',`act(async()=>{await api(quotePath('items'),{id:'${id}',name:val('qe-name'),price:Number(val('qe-price')),active:checked('qe-active')});$('.modal').remove();render()})`,'primary'))})}
async function quoteCompose(id){await act(async()=>{let items=(await api(quotePath('items'))).filter(x=>x.active);if(!items.length)throw Error('견적 상품을 먼저 등록하세요.');let suggested=await api(quotePath('suggestions/'+enc(id)));modal('견적 작성','<p class="muted">상담에서 파악한 항목과 수량을 미리 입력합니다. 담당자가 반드시 검토하세요.</p>'+items.map(x=>`<div class="line"><label>${e(x.name)} · ${money(x.price)}</label><input class="quote-qty" data-id="${e(x.id)}" type="number" min="0" max="1000" value="${suggested.find(s=>s.id===x.id)?.quantity||0}"></div>`).join('')+label('추가 안내',ta('quote-note'))+btn('서버 금액 계산 및 저장',`createQuote('${id}')`,'primary'))})}
async function createQuote(id){await act(async()=>{let items=[...document.querySelectorAll('.quote-qty')].map(x=>({id:x.dataset.id,quantity:Number(x.value)})).filter(x=>x.quantity>0);let r=await api(quotePath('offers'),{work:id,items,note:val('quote-note')});$('.modal').remove();toast('견적 '+money(r.amount)+' 저장 완료');render()})}
async function sendQuote(id){if(!confirm('검토한 견적 금액을 고객 채팅창에 전송할까요?'))return;await act(async()=>{await api(quotePath('offers/'+enc(id)+'/send'),{confirmed:true});toast('견적 전송 완료');render()})}

function landingBenefits(){
 const benefits=[
 '나의 사업 비밀과 민감한 정보까지 교육할 수 있습니다.',
 '나의 분신처럼 나처럼 상담할 수 있습니다.',
 '나의 말투와 상담 스타일을 반영하고 수정할 수 있습니다.',
 '직원 간의 인간관계 문제가 없습니다.',
 '사람으로 인한 스트레스가 없습니다.',
 '하루 24시간, 365일 일합니다.',
 '퇴직금이 없습니다.',
 '불만과 불평이 없습니다.',
 '직원 고용 및 노동관계 신고·분쟁에 대한 부담이 없습니다.',
 '일을 배워서 스스로 독립할 일이 없습니다.',
 '갑작스러운 퇴사나 퇴직 문제가 없습니다.',
 '나의 사업을 가장 잘 이해합니다.',
 '단순한 직원을 넘어 사업 파트너의 역할까지 수행합니다.',
 '사람에게 사업 정보를 공유할 때 발생하는 신뢰와 정보 유출에 대한 걱정을 줄일 수 있습니다.',
 '채용 스트레스가 없습니다.',
 '식비가 들지 않습니다.',
 '교육을 통해 업무를 잘 수행하도록 만들 수 있습니다.',
 '상담부터 예약, 비서 역할까지 해냅니다.',
 '교육할수록 일을 더 잘합니다.',
 '지속적인 교육을 통해 업무 능력이 향상됩니다.',
 '고객에게 더 많은 서비스를 제공할 수 있습니다.',
 '인건비를 절약할 수 있습니다.',
 '저렴하고 합리적인 비용으로 이용할 수 있습니다.'
 ];
 return `<section class="landing-benefits" aria-labelledby="landing-benefit-title"><div class="landing-benefits-inner"><p class="landing-benefits-kicker">WHY CS AI</p><h2 id="landing-benefit-title" aria-label="나의 사업을 이해하는 나의 클론 상담사.">${['나의 사업을 이해하는','나의 클론 상담사.'].map((line,i)=>`<span class="benefit-roll-line">${line.split(' ').map((word,j)=>`<span class="benefit-roll-word">${[...word].map((letter,k)=>`<span class="benefit-roll-letter" style="--letter-delay:${(i*9+j*3+k)*24}ms">${e(letter)}</span>`).join('')}</span>`).join(' ')}</span>`).join('')}</h2><p class="landing-lead">사실 직원을 직접 고용하는 것이 더 저렴할 수도 있습니다. 하지만 나의 클론 상담직원은 다릅니다.</p><div class="landing-benefit-grid" role="list" aria-label="나의 클론 상담직원의 23가지 장점">${benefits.map((item,i)=>`<div class="landing-benefit" role="listitem"><span class="landing-benefit-number">${String(i+1).padStart(2,'0')}</span><span class="landing-roll-title">${e(item)}</span></div>`).join('')}</div><div class="landing-benefits-cta"><div><h3>내 상담 방식, 직접 가르쳐볼까요?</h3><p>첫 상담 테스트 1회와 교육 크레딧 20C로 시작할 수 있습니다.</p></div><button type="button" onclick="google()">내 클론 상담사 만들어보기 <span aria-hidden="true">↗</span></button></div><p class="landing-benefits-note">AI 응답에는 오류가 있을 수 있으며, 24시간 이용은 서비스 상태와 구독 한도에 따릅니다. 예약·견적·외부 연동 등은 해당 기능의 구매 및 설정이 필요하며 일부는 개발·검증 중입니다. 교육 자료는 서비스 및 AI 처리에 사용될 수 있으므로 비밀번호, 결제 정보, 불필요한 개인정보는 입력하지 마세요. 정보 유출이 없다고 보장할 수 없으며, 실제 데이터 보호와 비용 절감은 운영 방식에 따라 달라집니다.</p></div></section>`
}

function landingUnification(){
 const steps=(labels,detail,sources,target)=>`<div class="unify-stepper" data-step-progress><div class="unify-source-list">${sources.map(name=>`<span>${e(name)}</span>`).join('')}</div><div class="unify-merge-line" aria-hidden="true"><span></span></div><div class="unify-destination">${e(target)}</div><div class="unify-step-track"><span class="unify-step-bar"></span>${labels.map((name,i)=>`<button type="button" class="unify-step" data-step="${i}" aria-label="${i+1}단계 ${e(name)}" title="${e(detail[i])}"><span class="unify-step-dot"><b>${i+1}</b><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></span><span class="unify-step-name">${e(name)}</span></button>`).join('')}</div><p class="unify-step-detail" aria-live="polite">${e(detail[0])}</p></div>`;
 return `<section class="landing-unify" aria-labelledby="landing-unify-title"><div class="landing-unify-inner"><p class="landing-benefits-kicker">ONE CUSTOMER CENTER</p><h2 id="landing-unify-title">판매처는 여러 곳이어도,<br>상담 관리는 한 곳에서.</h2><p class="landing-lead">AI가 답변한 뒤에도 상담 기록을 찾고 예약·민원을 처리하는 일은 남습니다. CS AI에서 상담과 후속 업무를 함께 관리하세요.</p><div class="unify-paths"><article class="unify-path"><span class="unify-number">01</span><h3>기존 채널을 연결해 관리</h3><p>고객은 익숙한 채널에서 문의하고, 업체는 CS AI가 처리한 상담을 통합 상담함에서 확인합니다.</p>${steps(['문의 유입','AI 응대','통합 상담함'],['네이버 톡톡·카카오톡 채널·홈페이지에서 고객이 문의합니다.','연결과 승인된 채널에서 CS AI가 상담합니다.','CS AI가 처리한 대화와 후속 업무를 한곳에서 확인합니다.'],['네이버 톡톡','카카오톡 채널','홈페이지 위젯'],'CS AI 통합 상담함')}<p class="unify-foot">채널별 연결·승인 후 CS AI가 처리한 대화만 표시됩니다. 기존 1:1 상담 이력 수집과 외부 채널 담당자 답변 전송은 현재 지원하지 않습니다.</p></article><article class="unify-path"><span class="unify-number">02</span><h3>하나의 공식 상담 링크로 안내</h3><p>판매처마다 같은 상담을 반복할 필요 없이 업체 전용 CS AI 링크로 고객을 안내할 수 있습니다.</p>${steps(['링크 안내','공식 채팅','상담 관리'],['판매처·SNS·자사몰·오프라인 QR에 같은 상담 링크를 안내합니다.','고객이 업체 전용 CS AI 채팅창에서 문의합니다.','AI 상담과 담당자 답변, 기록·예약·업무를 함께 관리합니다.'],['판매처','SNS','자사몰','오프라인 QR'],'업체 전용 상담 링크')}<p class="unify-foot">자체 채팅에서는 AI 상담과 담당자 직접 답변, 상담 기록과 예약·업무 연결을 관리합니다. 각 판매처의 외부 링크 정책은 확인해 주세요.</p></article></div><div class="unify-summary"><strong>나의 클론 상담사, 그리고 하나의 고객센터.</strong><span>채널이 늘어나도 상담을 정리하는 곳은 CS AI가 되도록 만들고 있습니다.</span></div><div class="unify-cta"><span>내 사업의 공식 상담 창구를 시작하세요.</span><button class="primary" type="button" onclick="google()">CS AI 시작하기</button></div></div></section>`
}

let analyticsDays=30;
async function analyticsPanel(){let r=await api('/api/analytics?days='+analyticsDays),brandRows=await api('/api/quality/brand-metrics'),brands=has('extra_agent')?(await api('/api/agents/list')).agents:[],max=Math.max(1,...r.daily.map(d=>d.threads));return card('고급 상담 통계',`<details class="ui-disclosure"><summary>브랜드별 최근 30일 상담</summary>${table(['브랜드','상담','완료'],brandRows.map(x=>[brands.find(a=>a.id===x.agent)?.settings.brand||(x.agent?'이전 브랜드':me.settings.brand),x.threads,x.resolved]))}</details>`+label('조회 기간',select('analytics-days',[['7','최근 7일'],['30','최근 30일'],['90','최근 90일']],String(analyticsDays)))+btn('조회', "analyticsDays=Number(val('analytics-days'));render()")+table(['고객 상담','메시지','미학습','완료'],[[r.threads,r.messages,r.unknown,r.resolved]])+`<div style="display:flex;align-items:end;height:120px;gap:2px;margin:18px 0">${r.daily.map(d=>`<div title="${e(d.date)}: ${d.threads}건" style="flex:1;min-width:0;background:#3182f6;border-radius:3px 3px 0 0;height:${Math.max(1,d.threads/max*100)}%"></div>`).join('')}</div><p class="muted">일별 고객 상담 수 · 관리자 테스트 제외</p>`+table(['채널','상태','건수'],r.channels.map(x=>[x.kind,states[x.status]||x.status,x.n]))+table(['예약 상태','건수'],r.bookings.map(x=>[states[x.status]||x.status,x.n]))+table(['업무 유형','상태','건수'],r.work.map(x=>[cfg.catalog.addons.find(a=>a.id===x.kind)?.name||x.kind,states[x.status]||x.status,x.n])))}
const reportAlerts=alerts;
alerts=async function(){
 const html=await reportAlerts();
 if(!has('report')&&!freeFeaturePreview())return html;
 return html+await reportPanel();
}
async function reportPanel(){
 const readOnly=!has('report');if(readOnly&&!freeFeaturePreview())return locked('report','일간·주간 리포트 권한이 필요합니다.');
 const r=readOnly?previewData().report:await api('/api/reports');
 const settings=stack(label('생성 주기',select('report-frequency',[['daily','매일'],['weekly','매주']],r.settings.frequency))+
  `<label><input class="check" type="checkbox" id="report-enabled" ${r.settings.enabled?'checked':''}> 자동 생성</label>`);
 const actions=stack(helperText(`${r.worker_enabled?'자동 워커 설정됨':'자동 워커 환경 설정 필요'} · 지난 완료 기간 기준 집계`)+
  actionGroup({keepSize:true},btn('설정 저장','saveReportSettings()','primary'),btn('리포트 생성','generateReport()')),{gap:'compact'});
 const reports=r.reports.map(x=>reportSummaryCard(x)).join('')+(!readOnly&&me.sample_tools&&sharedPreviewEnabled()?previewData().report.reports.map(reportSummaryCard).join(''):'');
 return (readOnly?previewNotice('report','상담 리포트 설정 체험'):'')+card('일간·주간 상담 리포트',helperText('기간별 상담 현황과 완료율, 미학습 질문을 확인하고 엑셀에서 열 수 있는 CSV로 저장하세요.')+stack(`<div class="alert-fields">${settings}</div>`+actions+
  (reports?divider()+section('report-history','생성 내역',actionGroup(btn('CSV 다운로드','downloadReportCsv()'))+reports):'')));
}
async function reportsPage(){return pageTop('일간·주간 리포트','상담 현황과 완료율을 확인하고 CSV로 저장하세요.')+await reportPanel();}
async function statsPage(){
 const top=pageTop('상담 통계','기간별 상담 현황과 채널·업무 통계를 확인하세요.');
 if(has('stats')&&!(me.sample_tools&&sharedPreviewEnabled()))return top+await analyticsPanel();
 if(!sharedPreviewEnabled())return top+locked('stats','고급 상담 통계 권한이 필요합니다.');
 const values=[2,4,3,5,2,1,3],max=Math.max(...values);
 return top+(has('stats')?await analyticsPanel():previewNotice('stats','상담 통계 체험'))+card('최근 7일 상담 통계',helperText('샘플 데이터 · 실제 고객 상담 기록이 아닙니다.')+table(['고객 상담','메시지','미학습','완료'],[[20,82,3,15]])+`<div style="display:flex;align-items:end;height:120px;gap:4px;margin:18px 0">${values.map((n,i)=>`<div title="샘플 ${i+1}일: ${n}건" style="flex:1;background:#3182f6;border-radius:3px 3px 0 0;height:${n/max*100}%"></div>`).join('')}</div>`+table(['채널','상담'],[['웹 채팅',16],['외부 채널',4]]));
}
async function customerChatPage(){
 const html=await preview();
 const canOpen=me.public_access&&me.enabled;
 return pageTop('고객 채팅 페이지','고객에게 제공하는 페이지형 상담창을 확인하세요.')+card('고객 상담 페이지 열기',canOpen?`<a class="ui-button primary" href="/c/${enc(me.slug)}" target="_blank" rel="noopener">공개 채팅 페이지 열기</a>`:helperText('공개 채팅이 활성화되면 실제 고객 페이지를 열 수 있습니다. 아래에서 미리 확인하세요.'))+html;
}
function reportSummaryCard(x){
 const v=x.summary||{},n=k=>Math.max(0,Number(v[k])||0),total=n('threads'),done=n('resolved'),unknown=n('unknown'),rate=total?Math.round(done/total*100):0,max=Math.max(1,total,done,unknown);
 const bars=[['전체 상담',total],['완료',done],['미학습',unknown]].map(([name,value])=>`<div class="report-bar-row"><span>${name}</span><div class="report-bar-track"><span style="width:${value/max*100}%"></span></div><b>${value}건</b></div>`).join('');
 return `<div class="line report-summary-card"><b>${e(x.period)}</b><div class="report-metric-pair"><div><small>상담 완료율</small><strong>${total?rate+'%':'집계 없음'}</strong></div><div><small>메시지</small><strong>${n('messages')}개</strong></div></div><div class="report-bars">${bars}</div><p class="muted">${unknown?'미학습 질문을 검토하고 반복 문의를 교육에 반영하세요.':total?'이번 기간 미학습 질문이 없습니다.':'집계된 상담이 없습니다.'}</p></div>`;
}
async function downloadReportCsv(){await act(async()=>{
 const sample=!has('report');if(sample&&!freeFeaturePreview())return;
 const r=sample?previewData().report:await api('/api/reports');
 const cell=v=>{let t=String(v??'');if(/^[=+@-]/.test(t))t="'"+t;return '"'+t.replace(/"/g,'""')+'"';};
 const rows=[['기간','상담 건수','완료 건수','완료율(%)','미학습 건수','메시지 수'],...r.reports.map(x=>{const v=x.summary||{};return [x.period,v.threads,v.resolved,v.threads?Math.round(v.resolved/v.threads*100):'',v.unknown,v.messages]})];
 const blob=new Blob(['\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8;'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=(sample?'csai-sample-report':'csai-report')+'.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
})}
async function saveReportSettings(){if(!has('report')&&freeFeaturePreview()){previewData().report.settings={frequency:val('report-frequency'),enabled:checked('report-enabled')};toast('샘플 리포트 설정 저장');render();return;}if(!requirePreviewAccess('report'))return;await act(async()=>{await api('/api/reports/settings',{frequency:val('report-frequency'),enabled:checked('report-enabled')});toast('설정 저장 완료');render()})}
async function generateReport(){if(!has('report')&&freeFeaturePreview()){previewData().report.reports.unshift({period:'샘플 · '+(previewData().report.settings.frequency==='weekly'?'주간':'일간')+' 리포트',summary:{threads:18,resolved:14,unknown:3,messages:82}});toast('샘플 리포트 생성 완료');render();return;}if(!requirePreviewAccess('report'))return;await act(async()=>{await api('/api/reports/generate',{});toast('리포트 생성 완료');render()})}

const pushAlerts=alerts;
alerts=async function(){
 const html=await pushAlerts();
 const readOnly=!has('push');if(readOnly&&!freeFeaturePreview())return html+locked('push','브라우저가 닫혀 있어도 지원되는 기기에서 업무 알림을 받을 수 있습니다.');
 const r=readOnly?previewData().push:await api('/api/push'),current=localStorage.getItem('csai-push-id');
 const status=readOnly?'샘플 체험 · 실제 기기 등록 없음':r.configured?(r.live?'실제 발송 활성화 · 기기 확인 필요':'모의 발송 모드'):'VAPID 환경변수 설정 필요';
 const settings=stack(
  helperText(status+' · 구매한 알림 종류만 발송 · HTTPS 필요. iPhone은 홈 화면에 추가 후 실행하세요.')+
  helperText('화면이 닫혀 있을 때는 기기의 기본 알림음·진동 설정을 따릅니다. 무음 및 방해금지 설정을 강제로 해제하지 않습니다.')+
  actionGroup({keepSize:true},btn('알림 등록',readOnly?"previewPushAction('register')":'registerPush()','primary'),btn('알림 해제',readOnly?"previewPushAction('remove')":'unregisterPush()'),btn('알림 테스트',readOnly?"previewPushAction('test')":'testPushOnDevice()')).replace('ui-actions-keep-size','ui-actions-keep-size push-device-actions'),
  {gap:'compact'});
 const devices=r.devices.map(d=>`<div class="line">
  <b>${d.id===current?'현재 기기':'등록 기기'}</b><p>${e(new Date(d.created*1000).toLocaleString())}</p>
  <details class="ui-disclosure"><summary>알림 종류 및 무음 설정</summary>
   ${r.kinds.map(k=>`<label class="line"><input type="checkbox" class="check" data-push-kind="${e(k.id)}" ${d.preferences.kinds.includes(k.id)?'checked':''} ${k.available?'':'disabled'}> ${e(k.label)}${k.available?'':' · 추가 기능 필요'}</label>`).join('')}
   <label><input type="checkbox" class="check" data-push-silent ${d.preferences.silent?'checked':''}> 무음 요청</label>
   <button type="button" onclick="saveDevicePush(this,'${e(d.id)}')">설정 저장</button>
  </details>${btn('등록 해제',d.id==='preview-device'?"previewPushAction('remove')":`removePush('${d.id}')`)}
 </div>`).join('');
 const sound=section('foreground-sound','화면이 열려 있을 때 추가 효과음',stack(
  helperText('이 브라우저에서 직접 켜면 화면이 열린 동안만 효과음을 재생합니다. 백그라운드 커스텀 사운드는 지원하지 않습니다.')+
  actionGroup({keepSize:true},btn('켜기·미리 듣기','enableForegroundSound()'),btn('끄기','disableForegroundSound()')).replace('ui-actions-keep-size','ui-actions-keep-size push-sound-actions'),
  {gap:'compact'}));
 const deliveries=r.deliveries.map(d=>helperText(new Date(d.created*1000).toLocaleString()+' · '+d.status)).join('');
 return html+(readOnly?previewNotice('push','기기 알림 설정 체험'):'')+card('모바일·PC 웹 푸시 알림',helperText('등록한 브라우저나 홈 화면 앱에서 업무 알림을 받습니다. 지원 환경과 기기 권한이 필요합니다.')+stack(settings+
  (devices?divider()+section('push-devices','등록 기기',devices):'')+divider()+sound+
  (deliveries?divider()+section('push-deliveries','웹 푸시 발송 내역',stack(deliveries,{gap:'compact'})):'')
 ));
};
async function saveDevicePush(button,id){if(id==='preview-device'){const d=previewData().push.devices[0];if(d)d.preferences.silent=button.closest('details').querySelector('[data-push-silent]').checked;toast('샘플 알림 설정 저장');return;}await act(async()=>{const root=button.closest('details');const kinds=[...root.querySelectorAll('[data-push-kind]:checked')].map(x=>x.dataset.pushKind);await api('/api/push/'+enc(id),{kinds,silent:root.querySelector('[data-push-silent]').checked},'PATCH');toast('기기 알림 설정 저장');render()})}
async function testPushOnDevice(){await act(async()=>{if(!('Notification'in window)||Notification.permission!=='granted')throw Error('먼저 알림 권한을 허용하세요.');const reg=await navigator.serviceWorker.getRegistration('/');if(!reg)throw Error('먼저 이 기기를 등록하세요.');await reg.showNotification('CS AI · 기기 알림 테스트',{body:'이 알림은 기기 자체 테스트입니다. 서버 발송 검증은 별도입니다.',tag:'csai-device-test',data:{path:'/#alerts'}});toast('기기 테스트 알림 요청 완료')})}
let foregroundAudio=null,foregroundSound=false,lastPushSound='';
function playForegroundSound(urgent=false){if(!foregroundSound||!foregroundAudio||foregroundAudio.state!=='running'||document.hidden)return;const t=foregroundAudio.currentTime;for(const [i,hz] of (urgent?[650,850,650]:[540,720]).entries()){const osc=foregroundAudio.createOscillator(),gain=foregroundAudio.createGain(),at=t+i*.14;osc.frequency.value=hz;gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(.065,at+.025);gain.gain.exponentialRampToValueAtTime(.001,at+.12);osc.connect(gain);gain.connect(foregroundAudio.destination);osc.start(at);osc.stop(at+.14)}}
async function enableForegroundSound(){await act(async()=>{const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio)throw Error('이 브라우저는 효과음을 지원하지 않습니다.');foregroundAudio=foregroundAudio||new Audio();await foregroundAudio.resume();foregroundSound=true;playForegroundSound();toast('이 화면의 효과음을 켰습니다.')})}
function disableForegroundSound(){foregroundSound=false;toast('추가 효과음을 껐습니다.')}
if('serviceWorker'in navigator)navigator.serviceWorker.addEventListener('message',event=>{if(!me||publicMode||event.data?.type!=='csai-push'||event.data.event===lastPushSound)return;lastPushSound=event.data.event;playForegroundSound(event.data.kind==='handoff_urgent')});

function vapidBytes(key){let b=atob(key.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-key.length%4)%4));return Uint8Array.from(b,x=>x.charCodeAt(0))}
async function registerPush(){await act(async()=>{if(!('serviceWorker'in navigator)||!('PushManager'in window)||!('Notification'in window))throw Error('웹 푸시를 지원하는 HTTPS 브라우저가 필요합니다.');let r=await api('/api/push');if(!r.configured)throw Error('푸시 서버 설정이 필요합니다.');if(await Notification.requestPermission()!=='granted')throw Error('브라우저에서 알림 권한을 허용하세요.');let reg=await navigator.serviceWorker.register('/push-sw.js');await navigator.serviceWorker.ready;let sub=await reg.pushManager.getSubscription();if(!sub)sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:vapidBytes(r.public_key)});let x=await api('/api/push',sub.toJSON());localStorage.setItem('csai-push-id',x.id);toast('이 기기 등록 완료');render()})}
async function unregisterPush(){await act(async()=>{let id=localStorage.getItem('csai-push-id');if(id)await api('/api/push/'+id,undefined,'DELETE');let reg=await navigator.serviceWorker?.getRegistration('/');let sub=await reg?.pushManager.getSubscription();if(sub)await sub.unsubscribe();localStorage.removeItem('csai-push-id');toast('알림 해제 완료');render()})}
async function removePush(id){if(!confirm('이 기기의 푸시 등록을 해제할까요?'))return;await act(async()=>{if(localStorage.getItem('csai-push-id')===id){await unregisterPush();return}await api('/api/push/'+id,undefined,'DELETE');render()})}

const domainChannels=channels;
channels=async function(){let html=await domainChannels();const readOnly=!has('domain');if(readOnly&&!freeFeaturePreview())return html+locked('domain','보유한 도메인에서 고객 상담을 제공합니다.');let r=readOnly?{domain:null,configured:false}:await api('/api/domains'),d=r.domain;return html+(readOnly?previewNotice('domain','자체 도메인 설정 체험'):'')+card('자체 도메인',label('고객 상담 도메인',input('domain-host',d?.hostname||'','text','chat.example.com'))+btn('등록','saveDomain()','primary')+`<p class="muted">${r.configured?'Cloudflare 확인 설정 완료':'운영자 Cloudflare for SaaS 설정 필요'}</p>`+(d?`<p>상태: ${d.active?'DNS·HTTPS 검증 완료':'확인 대기'}</p><p class="muted">아래 DNS 레코드를 추가하고 운영자가 Custom Hostname 및 TLS 인증서를 연결한 후 확인하세요.</p>`+table(['종류','이름','값'],[['TXT',d.txt_name,d.txt_value],['CNAME',d.hostname,r.target||'운영자 설정 필요']])+actionGroup({keepSize:true},btn('DNS 및 HTTPS 확인','verifyDomain()'),btn('연결 해제','removeDomain()'))+(d.active?`<p><a href="https://${e(d.hostname)}" target="_blank" rel="noopener noreferrer">고객 상담 열기</a></p>`:''):''))};
async function saveDomain(){if(!requirePreviewAccess('domain'))return;await act(async()=>{await api('/api/domains',{hostname:val('domain-host')});render()})}
async function verifyDomain(){await act(async()=>{await api('/api/domains/verify',{});toast('DNS·HTTPS 확인 완료');render()})}
async function removeDomain(){if(!confirm('자체 도메인 연결을 해제할까요?'))return;await act(async()=>{await api('/api/domains',undefined,'DELETE');render()})}

const smsAlerts=alerts;
alerts=async function(){
 const html=await smsAlerts(),r=await api('/api/message-notifications'),s=r.settings||{};
 const settings=stack(label('수신 번호',input('sms-phone','','tel',s.phone||'01012345678'))+
  label('수신 방식',select('sms-kind',[['SMS','SMS'],['알림톡','알림톡']],s.kind||'SMS'))+
  `<label><input class="check" type="checkbox" id="sms-enabled" ${s.enabled?'checked':''}> 자동 발송</label>
   <label><input class="check" type="checkbox" id="sms-consent"> 본인 번호이며 업무 알림 수신 및 연락처 처리에 동의합니다.</label>`);
 const actions=stack(
  helperText(`${s.verified?'번호 확인 완료':'번호 확인 대기'} · ${r.live[s.kind||'SMS']?'실제 발송 활성화':cfg.demo?'모의 발송':'실제 발송 미설정'}`)+
  actionGroup({keepSize:true},btn('저장','saveMessageNotify()','primary'),btn('알림 해제','disableMessageNotify()'),btn('메시지 충전','openMessageRecharge()')),
  {gap:'compact'});
 const rechargeNotice=`<section class="card app-card paid-preview-notice" aria-label="메시지 충전"><div class="paid-preview-copy"><strong>알림톡·SMS</strong><span class="paid-preview-price">건별 충전</span></div>${actionGroup({keepSize:true},btn('충전하기','openMessageRecharge()','primary'))}</section>`;
 return stack(html+rechargeNotice+card('알림톡·SMS 업무 알림',stack(
  stack(helperText('등록한 본인 휴대전화로 구매한 업무 알림을 받습니다. 1건당 충전 잔액 1건을 차감하며, 실제 발송에는 번호 소유권 확인이 필요합니다.')+
   `<p>SMS ${r.balance.SMS}건 · 알림톡 ${r.balance['알림톡']}건</p>`,{gap:'compact'})+
  `<div class="alert-fields">${settings}</div>`+actions+
  table(['유형','발송 상태','일시'],r.deliveries.map(x=>[x.kind,x.status,new Date(x.created*1000).toLocaleString()]))
 )),{gap:'sections'});
};
function openMessageRecharge(){
 const packages=cfg.catalog.messages||[];
 const choices=packages.map((m,i)=>`<div class="row between line"><span>${e(m.name)} ${m.quantity}건 · ${money(m.price)}</span>${me.sandbox_allowed?btn('테스트 충전',`selectMessageRecharge(${i})`,'secondary'):'<span class="muted">실결제 준비 중</span>'}</div>`).join('');
 modal('알림톡·SMS 충전',helperText(me.sandbox_allowed?'테스트 충전입니다. 실제 청구되지 않습니다.':'실제 결제 연결 전입니다. 충전 요금을 확인할 수 있습니다.')+choices+actionGroup(btn('충전 내역 보기',"$('.modal')?.remove();go('orders')")));
}
async function selectMessageRecharge(i){
 const item=cfg.catalog.messages[i];if(!me.sandbox_allowed||!item)return;
 await act(async()=>{$('.modal')?.remove();await openCheckout({kind:'message',name:item.name,quantity:item.quantity});});
}
async function saveMessageNotify(){await act(async()=>{await api('/api/message-notifications',{phone:val('sms-phone'),kind:val('sms-kind'),enabled:checked('sms-enabled'),consent:checked('sms-consent')});toast('설정 저장 완료');render()})}
async function disableMessageNotify(){await act(async()=>{await api('/api/message-notifications',undefined,'DELETE');render()})}
const messageInvites=invites;
invites=async function(){let html=await messageInvites(),xs=await api('/api/operator/message-notifications');return html+card('업무 알림 번호 확인',`<p class="muted">실제 번호 소유권과 수신 동의를 별도로 확인한 뒤 승인하세요. 승인 자체는 메시지를 보내지 않습니다.</p>`+xs.map(x=>`<div class="line"><b>${e(x.phone)}</b><p>${e(x.kind)} · ${x.verified?'확인 완료':'확인 필요'}</p>${x.verified?'':btn('소유권 확인 승인',`verifyMessagePhone('${x.ws}','${x.phone}')`)}</div>`).join(''))};
async function verifyMessagePhone(ws,phone){if(!confirm('번호 소유권 및 수신 동의를 실제로 확인했습니까?'))return;await act(async()=>{await api('/api/operator/message-notifications/'+ws+'/verify',{phone,confirmed:true});render()})}

const customDeveloper=developer;
developer=async function(){let html=await customDeveloper();const readOnly=!has('custom_integration')||!has('external_api');if(readOnly&&!freeFeaturePreview())return html+locked('custom_integration','직접 승인한 업무를 외부 서비스의 서버 API로 실행하고 결과를 회수합니다.');let r=readOnly?{workflows:[],jobs:[]}:await api('/api/custom-workflows'),work=readOnly?[]:await api('/api/work');return html+(readOnly?previewNotice('custom_integration','맞춤 외부 업무 설정 체험'):'')+card('맞춤 외부 업무 API',`<p class="muted">외부 시스템은 custom:jobs 권한 키로 대기 업무를 조회하고 claim → complete 순서로 실행합니다. 승인하지 않은 고객정보는 자동으로 보내지 않습니다.</p>`+label('업무 이름',input('custom-name'))+label('업무 설명',ta('custom-desc'))+btn('업무 등록','saveCustomWorkflow()','primary')+r.workflows.map(x=>`<div class="line"><b>${e(x.name)}</b><p>${e(x.description)} · ${x.active?'활성':'중지'}</p>${x.active?btn('중지',`disableCustomWorkflow('${x.id}')`):''}</div>`).join(''))+card('외부 실행 요청',label('업무 방식',select('custom-flow',r.workflows.filter(x=>x.active).map(x=>[x.id,x.name]),''))+label('연결 업무',select('custom-work',work.map(x=>[x.id,x.title]),''))+label('외부 전달 데이터 (JSON)',ta('custom-payload','{}'))+btn('내용 확인 및 실행 대기 등록','createCustomJob()','primary')+r.jobs.map(x=>`<div class="line"><b>${e(x.state)}</b><p>${e(x.result||'결과 대기')}</p>${x.state==='queued'?btn('취소',`cancelCustomJob('${x.id}')`):''}</div>`).join(''))};
async function saveCustomWorkflow(){if(!requirePreviewAccess('custom_integration')||!requirePreviewAccess('external_api'))return;await act(async()=>{await api('/api/custom-workflows',{name:val('custom-name'),description:val('custom-desc')});render()})}
async function disableCustomWorkflow(id){if(!confirm('업무를 중지하고 아직 실행되지 않은 요청을 취소할까요?'))return;await act(async()=>{await api('/api/custom-workflows/'+id+'/disable',{});render()})}
async function createCustomJob(){if(!requirePreviewAccess('custom_integration')||!requirePreviewAccess('external_api'))return;if(!confirm('선택한 외부 시스템에 입력한 데이터가 전달될 수 있습니다. 계속할까요?'))return;await act(async()=>{await api('/api/custom-jobs',{workflow:val('custom-flow'),work:val('custom-work'),payload:JSON.parse(val('custom-payload')),confirmed:true});render()})}
async function cancelCustomJob(id){await act(async()=>{await api('/api/custom-jobs/'+id+'/cancel',{});render()})}

async function sandboxFail(id){if(!confirm('테스트 주문을 결제 실패 상태로 변경할까요?'))return;await act(async()=>{await api('/api/billing/orders/'+id+'/sandbox-fail',{});await refresh();render()})}
async function sandboxRefund(id){if(!confirm('실제 돈은 환불되지 않습니다. 테스트 주문의 이용 권한이나 잔액을 회수할까요?'))return;await act(async()=>{await api('/api/billing/orders/'+id+'/sandbox-refund',{confirmed:true});await refresh();render()})}

/* Versioned policy drafts: separate required acknowledgements and automation risk check. */
const policyLinks=()=>`<nav class="policy-links" aria-label="서비스 정책"><a href="/policies/terms" target="_blank">이용약관</a><a href="/policies/privacy" target="_blank">개인정보처리방침</a><a href="/policies/ai" target="_blank">AI 이용 안내</a><a href="/policies/dpa" target="_blank">처리위탁 조건</a><a href="/policies/automation" target="_blank">자동화 책임 안내</a><a href="/policies/billing" target="_blank">결제·해지·환불</a></nav>`;
const businessFooter=()=>{const b=cfg?.business||{};if(!b.name)return '<p class="business-pending">정식 서비스 운영 사업자 정보 확정 전 · 현재 개발용 테스트 사이트</p>';return `<div class="business-identity"><strong>${e(b.name)}</strong><span>대표 ${e(b.representative)}</span><span>사업자등록번호 ${e(b.registration)}</span>${b.mail_order?`<span>통신판매업 신고 ${e(b.mail_order)}</span>`:''}<span>${e(b.address)}</span><span>고객 문의 ${e(b.phone)} · ${e(b.email)}</span><span>개인정보 보호책임자 ${e(b.privacy_officer)} · ${e(b.privacy_email)}</span></div>`};
const oldHome=home;
home=()=>oldHome()+`<footer class="site-policy-footer"><b>CS AI</b><p>정책 문서는 개발용 초안이며 출시 전 법률 및 운영 검토가 필요합니다.</p>${policyLinks()}${businessFooter()}</footer>`;
const oldShell=shell;
shell=body=>oldShell(body).replace('</main>',`<footer class="app-policy-footer">${policyLinks()}${businessFooter()}</footer></main>`);
const oldPhone=phone;
phone=(s,test=false,preview=false)=>oldPhone(s,test,preview).replace('</header>','</header><div class="ai-disclosure"><b>AI 상담 안내</b> · 답변에 오류가 있을 수 있습니다. 예약·결제·환불 조건은 업체 담당자에게 확인해 주세요. <a href="/policies/ai" target="_blank">AI 이용 안내</a> · <a href="/policies/privacy" target="_blank">개인정보 안내</a></div>');
function settingsAutomation(){
 return stack(`<p class="muted">예약 자동 확정은 별도 확인 후 사용할 수 있습니다. 견적 확정·실제 환불·보상 약속은 담당자 승인이 필요합니다.</p><p><a href="/policies/automation" target="_blank">자동화 및 책임 정책 보기</a></p>${['errors|AI 답변과 처리 결과에 오류가 생길 수 있음을 확인합니다.','accuracy|등록한 가격·예약 정보와 정책을 정확히 관리합니다.','approval|계약·결제·환불·보상 결정은 담당자가 승인합니다.'].map(x=>{let [k,v]=x.split('|');return checkbox('auto-'+k,v)}).join('')}${btn(me.policy?.automation_accepted?'확인 기록 갱신':'자동화 위험 확인 저장','saveAutomationAck()','primary')}`);
}
async function saveAutomationAck(){await act(async()=>{await api('/api/policies/automation-ack',{version:me.policy.version,errors:checked('auto-errors'),accuracy:checked('auto-accuracy'),approval:checked('auto-approval')});await refresh();toast('자동화 위험 확인을 기록했습니다.');render()})}
const requiredPolicies=[
 ['terms','서비스 이용약관'],['privacy','개인정보처리방침 확인'],
 ['ai','AI 이용 및 책임 안내'],['dpa','개인정보 처리위탁 조건'],
];
function flowScreen(id,title,description,content,className=''){
 return `<main class="ui-flow-screen ${className}">
  <section class="card app-card ui-flow-card" aria-labelledby="${id}">
   <header class="ui-flow-heading"><div class="brand"><b>CS</b> AI</div><h1 id="${id}">${e(title)}</h1>${helperText(description)}</header>
   ${content}
  </section>
 </main>`;
}
function flowNotice(message,tone='info'){
 return `<p class="ui-flow-notice" data-tone="${e(tone)}">${uiIcon('info')}<span>${e(message)}</span></p>`;
}
function flowActions(primary,secondary=''){
 return `<div class="ui-flow-actions">${primary}${secondary}</div>`;
}
function loginScreen(){
 const providerButton=(name,kind,action)=>`<button type="button" class="ui-button secondary ui-auth-provider" data-provider="${kind}" onclick="${e(action)}">
  <img src="/assets/${kind}.svg" alt=""><span>${e(name)}</span></button>`;
 return flowScreen('login-title','CS AI 시작하기','Google 계정으로 로그인하세요. 처음이라면 같은 과정에서 계정이 생성됩니다.',
  `<div class="ui-flow-body">
   ${flowActions(providerButton('Google로 계속하기','google-g','startGoogleLogin()'))}
   <div class="ui-auth-unavailable">${providerButton('네이버 로그인 안내','naver-n',"modal('준비 중',helperText('네이버 로그인은 준비 중입니다.'))")}
    ${providerButton('카카오 로그인 안내','kakao-talk',"modal('준비 중',helperText('카카오 로그인은 준비 중입니다.'))")}</div>
   ${cfg.demo?flowNotice('개발 환경에서 서비스 연결을 점검하고 있습니다.','development'):''}
   <nav class="ui-flow-links" aria-label="로그인 관련 정책">
    <a href="/policies/terms" target="_blank" rel="noopener">서비스 이용약관</a><a href="/policies/privacy" target="_blank" rel="noopener">개인정보처리방침</a>
   </nav>
   <a class="ui-flow-return" href="/">홈으로 돌아가기</a>
  </div>`,'login-screen');
}
function consentScreen(){
 const rows=requiredPolicies.map(([key,name])=>`<li class="ui-confirm-row">
  ${checkbox('policy-'+key,name,{hint:'(필수)'})}
  <a href="/policies/${key}" target="_blank" rel="noopener" aria-label="${e(name)} 내용 보기">
   내용 보기 ${uiIcon('chevron-right')}
  </a>
 </li>`).join('');
 return flowScreen('policy-title','서비스 정책 확인','서비스 이용을 위해 아래 필수 정책을 확인해 주세요.',`
  <form class="ui-flow-body" onsubmit="event.preventDefault();savePolicyConsent(this)" onchange="syncPolicyConfirmation(this,event.target)">
   ${checkbox('policy-all','필수 정책 전체 확인',{className:'ui-confirm-all'})}
   <ul class="ui-confirm-list" aria-label="필수 정책">${rows}</ul>
   ${flowNotice('마케팅 수신 동의는 실제 운영 방식이 정해진 뒤 별도로 요청합니다.')}
   ${me.policy?.draft?flowNotice('개발용 초안입니다. 정식 출시 전 법률 검토와 운영 정보 확정이 필요합니다.','development'):''}
   ${flowActions('<button type="submit" class="ui-button primary" disabled>확인하고 계속하기</button>',btn('로그아웃','logout()','tertiary ui-flow-secondary'))}
  </form>`,'policy-consent');
}
function syncPolicyConfirmation(form,changed){
 const all=form.querySelector('#policy-all'),fields=requiredPolicies.map(([key])=>form.querySelector('#policy-'+key));
 if(changed===all)fields.forEach(field=>{field.checked=all.checked;});
 const count=fields.filter(field=>field.checked).length;
 all.checked=count===fields.length;
 all.indeterminate=count>0&&count<fields.length;
 const submit=form.querySelector('[type=submit]');
 submit.disabled=!all.checked||submit.hasAttribute('aria-busy');
 return all.checked;
}
async function savePolicyConsent(form){
 const submit=form.querySelector('[type=submit]');
 if(submit.hasAttribute('aria-busy')||!syncPolicyConfirmation(form))return;
 submit.setAttribute('aria-busy','true');
 submit.disabled=true;
 const fields=form.querySelectorAll('input[type=checkbox]');
 fields.forEach(field=>{field.disabled=true;});
 try{
  await api('/api/policies/accept',{version:me.policy.version,...Object.fromEntries(requiredPolicies.map(([key])=>[key,checked('policy-'+key)]))});
  await refresh();
  await render();
 }catch(err){
  if(err.status===409){
   await act(async()=>{await refresh();await render();});
  }
  toast(err.message);
 }finally{
  fields.forEach(field=>{field.disabled=false;});
  submit.removeAttribute('aria-busy');
  syncPolicyConfirmation(form);
 }
}
function showPartnerInvite(){
 const code=sessionStorage.getItem('csai-invite');
 if(!code)return;
 sessionStorage.removeItem('csai-invite');
 modal('협력업체 무료 체험',`<form id="partner-invite-form" class="ui-flow-body">
  ${helperText('초청받은 계정에서 무료 체험을 시작할 수 있습니다.')}
  ${flowActions('<button type="submit" class="ui-button primary">무료 체험 시작</button>',
   btn('나중에',"this.closest('.modal')?.remove()",'tertiary ui-flow-secondary'))}
 </form>`);
 const form=$('#partner-invite-form'),submit=form.querySelector('[type=submit]');
 form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(submit.disabled)return;
  submit.disabled=true;
  submit.setAttribute('aria-busy','true');
  try{
   await act(async()=>{
    await api('/api/invites/accept',{code});
    form.closest('.modal')?.remove();
    await refresh();
    toast('무료 체험이 시작되었습니다.');
    await render();
   });
  }finally{
   submit.disabled=false;
   submit.removeAttribute('aria-busy');
  }
 });
}
const oldRender=render;
render=async function(){
 const onLogin=loginRoute();
 $('#app-design-system').media=me||onLogin?'all':'not all';
 if(me&&!me.policy?.accepted){$('#app').innerHTML=consentScreen();return;}
 if(onLogin){
  if(me){location.replace('/#dashboard');return;}
  $('#app').innerHTML=loginScreen();
  return;
 }
 await oldRender();
 if(me)showPartnerInvite();
};

const pricedAddonsPage=addons;
addons=()=>pricedAddonsPage()+card('추가 연동 개발 예정',`<p class="muted">아래 항목은 기획 목록입니다. 현재 구매·연결할 수 없으며 요금과 제공 시기는 미정입니다. 외부 플랫폼 권한과 정책 확인 후 개발합니다.</p>${table(['예정 기능','우선순위','검토 방식','요금'],(cfg.catalog.roadmap||[]).map(x=>[x.name,x.priority,x.method,'미정']))}`);

let qualityAgent='';
function ratingGroup(kind,title,desc){return '<fieldset class="db-rating" data-kind="'+kind+'"><legend>'+e(title)+'</legend><p class="muted">'+e(desc)+'</p><div class="db-stars">'+[1,2,3,4,5].map(n=>'<label class="db-star"><input type="radio" name="rating-'+kind+'" value="'+n+'" aria-label="'+n+'점 '+DBMotion.labels[n]+'"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+DBMotion.starPath+'"/></svg></label>').join('')+'</div><div class="db-rating-word" aria-hidden="true"><span class="db-rating-col">'+DBMotion.labels.map(x=>'<b>'+e(x)+'</b>').join('')+'</span></div><span class="db-rating-status db-motion-sr" role="status">별점을 선택하세요</span><button type="button" class="db-rating-clear" onclick="DBMotion.mountRating(this.closest(\'.db-rating\')).select(0)">선택 취소</button></fieldset>';}
async function rateConsultation(){
 if(!chatSession||!chatMessages.some(m=>['assistant','staff'].includes(m.role))){toast('상담 답변을 받은 뒤 평가할 수 있습니다.');return;}
 modal('이용 만족도', '<p>상담과 업체·상품에 대한 만족도를 각각 평가할 수 있습니다. 두 평가 모두 선택 사항입니다.</p>'+ratingGroup('consultation','상담 만족도','답변의 친절함과 도움 정도')+ratingGroup('business','업체·상품 만족도','실제로 이용한 업체 또는 상품에 대한 종합 평가')+'<p class="muted">평가는 업체 운영자에게 전달되며 공개 리뷰로 게시되지 않습니다. 개별 상품 리뷰가 아닌 업체 단위 평가입니다.</p>'+actionGroup({keepSize:true},btn('평가 제출','submitRatings()','primary'),btn('평가 없이 마치기',"$('.modal')?.remove()")));DBMotion.mountRatings($('.modal'));
}
async function submitRatings(){
 const consultation=Number(document.querySelector('input[name="rating-consultation"]:checked')?.value||0),business=Number(document.querySelector('input[name="rating-business"]:checked')?.value||0);
 if(!consultation&&!business){toast('별점을 선택하거나 평가 없이 마치기를 눌러 주세요.');return;}
 await act(async()=>{await api('/api/customer/feedback',{token:chatSession,...(consultation?{score:consultation}:{}),...(business?{business_score:business}:{})});$('.modal')?.remove();toast('평가가 저장되었습니다.')})
}
async function qualityHome(){
 const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(a=>a.available):[];
 if(qualityAgent&&!brands.some(a=>a.id===qualityAgent))qualityAgent='';
 const r=await api('/api/quality/overview?agent='+enc(qualityAgent)),notes=await api('/api/quality/private-notes?agent='+enc(qualityAgent)),queue=await api('/api/workflow/queue?agent='+enc(qualityAgent));
 const selected=brands.find(a=>a.id===qualityAgent),profile=selected?.settings||me.settings;
 const ready=!!profile.industries?.length&&!!profile.desired_work?.length;
 const steps=[
  ['업종 및 업무 설정',ready,qualityAgent?'agents':'settings'],
  ['AI 교육',r.knowledge.faq+r.knowledge.rules>0,'education'],
  ['상담 테스트',false,'test'],
  ['구독 및 공개 설정',me.public_access&&!!(selected?selected.enabled:me.enabled),'pricing'],
 ];
 const complete=steps.filter(([,done])=>done).length;
 const checklist=`<div class="quality-progress">
   <span>${complete} / ${steps.length} 완료</span>
   <progress aria-label="시작 체크리스트 진행률" value="${complete}" max="${steps.length}"></progress>
  </div>
  <ul class="quality-checklist">${steps.map(([name,done,dest])=>`<li><div><strong>${e(name)}</strong>${statusBadge(done?'확인 완료':'확인 필요',done?'success':'neutral')}</div>${btn('이동',"qualityGo('"+dest+"')",'secondary ui-sm')}</li>`).join('')}</ul>`+
  actionFooter([flowActions(btn(me.settings.onboarding_done?'시작 체크리스트 확인됨':'시작 안내 확인 완료',"act(async()=>{await api('/api/settings',{onboarding_done:true},'PATCH');await refresh();render()})",'primary'))]);
 const ratings=[['상담 만족도',r.ratings],['업체·상품 만족도',r.business_ratings]];
 const overview=`<dl class="dashboard-metrics quality-metrics">
  ${metric('실제 상담',r.threads)}${metric('완료',r.resolved)}${metric('담당자 전환',r.manual)}${metric('미학습',r.unknown_count+(r.unknown_count_capped?'+':''))}
 </dl><dl class="quality-ratings">${ratings.map(([name,rating])=>`<div><dt>${e(name)}</dt><dd>${rating.n?Number(rating.average).toFixed(1)+' / 5 · '+rating.n+'건':'평가 없음 · 0건'}</dd></div>`).join('')}</dl>
 <p class="muted">관리자 테스트와 샘플은 제외합니다. 완료 상태는 사업주가 표시한 값이며 AI 정확도를 뜻하지 않습니다.</p>`;
 const handoffActions=actionArea(btn('업무 권한·자동 전환 설정','workflowModal()','primary'),btn('승인된 교육 백업','downloadKnowledge()'),
  btn('교육 백업 가져오기','importKnowledgeModal()'),btn('구매한 기능 설정 적용',`offerReadyDrafts('${qualityAgent}',true)`)).replace('class="ui-actions ui-inline"','class="ui-actions ui-inline quality-handoff-actions"');
 return pageTop('시작 및 교육 개선','실제 기록을 바탕으로 필요한 작업만 확인합니다.')+brandSelect('quality-agent',brands,qualityAgent,'qualityAgent=this.value;render()')+
 `<div class="quality-overview">${card('시작 체크리스트',checklist)}${card('최근 30일 상담 개선',overview)}</div>`+
 card('업무 인수인계 및 처리할 상담','<p class="muted">30분 이상 고객 답변 대기 및 오류 신고를 확인합니다. 외부 알림은 연결 검증이 필요합니다.</p>'+
  queue.waiting.map(t=>`<div class="line">${t.urgent_keyword?'긴급 키워드 · ':''}${t.minutes}분 대기 ${btn('상담 열기',`openQualityThread('${t.id}')`)}</div>`).join('')+
  queue.issues.map(t=>`<div class="line"><p>${e(t.note||'AI 답변 오류 신고')}</p>${actionGroup(btn('상담 확인',`openQualityThread('${t.thread}')`),btn('정정 답변 교육',`prepareIssueEducation('${t.id}')`),btn('검토 완료',`resolveAnswerIssue('${t.id}')`))}</div>`).join('')+
  (!queue.waiting.length&&!queue.issues.length?emptyState('확인할 상담이 없습니다.'):'')+handoffActions)+
 card('반복 미학습 질문',r.suggestions.map((x,i)=>'<div class="line"><b>'+e(x.question)+'</b><p>'+x.count+'회 · 동일 문장 기준</p>'+btn('교육 후보로 선택','qualitySelectQuestion('+i+')')+'</div>').join('')||emptyState('아직 미학습 질문이 없습니다.'))+
 card('직접 상담 일괄 교육','<p class="muted">같은 브랜드의 상담 최대 20개를 선택하고 검토하세요. AI 분석 전에는 크레딧 견적을 확인합니다.</p>'+r.staff_threads.map(t=>'<label class="line"><input class="check quality-staff" type="checkbox" value="'+e(t.id)+'"> '+e(new Date(t.created*1000).toLocaleString())+' · '+e(t.id.slice(0,8))+'</label>').join('')+btn('선택 기록 검토','qualityBatch()','primary'))+
 card('사업주 전용 비공개 메모','<p class="muted">이 메모는 AI 교육이나 고객 답변에 전달하지 않습니다. 비밀번호·API 키는 저장하지 마세요.</p>'+ta('private-note')+btn('메모 저장',"act(async()=>{await api('/api/quality/private-notes',{agent:qualityAgent,body:val('private-note')});render()})",'primary')+notes.map(n=>'<div class="line"><p>'+e(n.body)+'</p>'+btn('삭제',"deleteVisibleRow('/api/quality/private-notes/"+n.id+"',this)")+'</div>').join(''));
}
function qualityGo(dest){if(educationBusy||sending)return;if(dest==='education'){if(educationAgent!==qualityAgent){resetEducationDraft();trainingChat=[];estimate=null;}educationAgent=qualityAgent;}if(dest==='test'){previewAgent=qualityAgent;chatSession=null;chatMessages=[];}if(dest==='agents')brandEditor=qualityAgent;go(dest)}
async function qualitySelectQuestion(i){await act(async()=>{const r=await api('/api/quality/overview?agent='+enc(qualityAgent)),q=r.suggestions[i];if(!q||educationBusy)return;resetEducationDraft();educationAgent=qualityAgent;trainingChat=[];estimate=null;educationDraft={values:{'faq-q':q.question},dates:[],files:[],upload:[],memory:[],open:[true,true]};go('education')})}
async function qualityBatch(){await act(async()=>{const threads=[...document.querySelectorAll('.quality-staff:checked')].map(x=>x.value);if(!threads.length){toast('상담을 선택하세요.');return;}if(!confirm('선택한 상담을 교육 자료로 검토할 권한이 있나요?'))return;const r=await api('/api/quality/staff-source',{agent:qualityAgent,threads,consent:true});staffSourceAgent=r.agent;modal('직접 상담 기록으로 교육',label('교육 자료 검토',ta('staff-education-source',r.text))+'<label><input type="checkbox" id="staff-education-consent"> 개인정보·기밀을 확인했습니다.</label>'+btn('교육 화면으로 가져오기','loadStaffTraining()','primary'))})}
async function qualityCompare(id,agent){await act(async()=>{const d=await api('/api/quality/version/'+id+'/compare?agent='+enc(agent));modal('교육 버전 비교',table(['추가 FAQ','동일 FAQ','충돌 FAQ','기존 규칙','복원 규칙'],[[d.added_questions.length,d.duplicates.length,d.conflicts.length,d.old_rule_count,d.new_rule_count]])+d.conflicts.map(x=>'<div class="line"><b>'+e(x.question)+'</b><p>현재: '+e(x.previous)+'</p><p>복원: '+e(x.proposed)+'</p></div>').join(''))})}
async function featureDraft(k){await act(async()=>{const r=await api('/api/quality/feature-draft/'+enc(k));modal('기능 설정 체험','<p>실제 기능 활성화 없이 설정 초안을 저장합니다. 개인정보와 비밀키는 입력하지 마세요.</p>'+r.fields.map((f,i)=>label(f,ta('feature-draft-'+i,r.config[f]||''))).join('')+btn('초안 저장',"saveFeatureDraft('"+k+"')",'primary'))})}
async function saveFeatureDraft(k){await act(async()=>{const r=await api('/api/quality/feature-draft/'+enc(k));await api('/api/quality/feature-draft/'+enc(k),{config:Object.fromEntries(r.fields.map((f,i)=>[f,val('feature-draft-'+i)]))});$('.modal')?.remove();toast('설정 초안 저장 완료')})}

async function prepareMemorySelection(files,ids,output){
 if(educationBusy)return;
 if(!ids.length){toast('이전할 대화를 선택하세요.');return;}
 if(!files?.every(f=>/\.json$/i.test(f.name))){toast('유료 이전은 ZIP을 푼 JSON 파일에서 선택해 주세요.');return;}
 if(!me.sandbox_allowed){toast('실제 유료 이전 결제는 준비 중입니다.');return;}
 if(!confirm('선택한 대화 내용을 기기에서 추출해 검토할까요? 아직 서버 전송이나 크레딧 차감은 없습니다.'))return;
 const progress=memoryProgress(['선택한 대화를 기기에서 추출','이전할 대화 준비']);
 output.querySelector('[data-memory-extraction]')?.remove();
 progress.element.dataset.memoryExtraction='';
 output.append(progress.element);
 progress.set(0,'running');
 progress.element.scrollIntoView({block:'nearest'});
 educationBusy=true;
 let step=0;
 try{
  const r=await memoryLocalPreview(files,'','',p=>progress.set(0,'running',p),ids);
  progress.set(step++,'done');
  progress.set(step,'running');
  memoryTransfer={agent:educationAgent,batches:r.batches,index:0,selected:r.selected,done:new Set(),order:''};
  const resume=$('#memory-resume');
  if(resume)resume.innerHTML=memoryResume();
  progress.set(step,'done');
  await openMemoryTransfer();
 }catch(err){progress.set(step,'error',err.message);toast(err.message)}finally{educationBusy=false}
}
async function openMemoryTransfer(){
 await act(async()=>{
  const t=memoryTransfer;
  if(!t||t.agent!==educationAgent){toast('이전 자료를 다시 선택하세요.');return;}
  const orders=await api('/api/memory-import/paid-orders?agent='+enc(t.agent));
  if(!orders.some(x=>x.id===t.order))t.order=orders[0]?.id||'';
  const order=orders.find(x=>x.id===t.order);
  let controls='<p>선택한 대화 '+t.selected+'개 · '+t.batches.length+'개 구간 · 현재 '+(t.index+1)+'번</p><p class="muted">테스트 이전 이용권 '+money(cfg.catalog.memory_import.price)+' · AI 교육 크레딧은 별도입니다. 구간별 검토와 비용 확인 후 분석합니다.</p>';
  controls+=orders.length?label('이전 이용권',select('memory-paid-order',orders.map(x=>[x.id,new Date(x.paid_at*1000).toLocaleString()+' · '+x.batches.length+'/'+x.max_batches+' 구간']),t.order).replace('<select','<select onchange="memoryTransfer.order=this.value;openMemoryTransfer()"')):'<p>이 브랜드에 사용할 테스트 이전 이용권이 없습니다.</p>';
  controls+=btn('이전 이용권 테스트 구매',"act(async()=>{await openCheckout({kind:'memory_import',agent:memoryTransfer.agent})})");
  if(order)controls+='<p>이전 기록: 검토·반영 완료 '+order.batches.filter(b=>['review','published'].includes(b.state)).length+'구간</p>';
  controls+=label('전송 전 자료 검토 및 수정',ta('memory-batch-text',t.batches[t.index]),{hint:'개인정보·비밀정보·개인 대화·확정되지 않은 사업 아이디어를 제외하세요.'})+checkbox('memory-batch-consent','처리 권한과 개인정보·기밀을 확인했고 이 구간의 서버 분석에 동의합니다.')+actionFooter([
   t.index>0?btn('이전 구간','moveMemoryBatch(-1)'):'',
   t.index+1<t.batches.length?btn('다음 구간','moveMemoryBatch(1)'):'',
   order?btn('교육 비용 확인','quoteMemoryBatch()','primary'):'',
  ]);
  modal('외부 AI 기억 이전',controls);
 });
}
function moveMemoryBatch(delta){if(!memoryTransfer)return;memoryTransfer.batches[memoryTransfer.index]=val('memory-batch-text');memoryTransfer.index=Math.max(0,Math.min(memoryTransfer.batches.length-1,memoryTransfer.index+delta));openMemoryTransfer()}
async function quoteMemoryBatch(){await act(async()=>{
 const t=memoryTransfer;if(!t||t.agent!==educationAgent)return;
 if(!checked('memory-batch-consent')){toast('자료 처리 동의가 필요합니다.');return;}
 const text=val('memory-batch-text').trim();if(!text||text.length>50000){toast('구간은 50,000자 이하로 입력하세요.');return;}
 t.batches[t.index]=text;
 const q=await api('/api/memory-import/prepare',{order:t.order,agent:t.agent,text,consent:true});
 if(q.state!=='estimated'){toast(q.state==='running'?'이미 분석 중입니다.':'이미 분석한 구간입니다. 교육 결과를 확인하세요.');openMemoryTransfer();return;}
 modal('기억 이전 교육 비용 확인','<p>최대 '+q.maxCredits+' C 예약 · 현재 '+q.credits+' C</p><p>실제 사용량만 정산되고 결과를 검토하여 승인해야 합니다.</p>'+actionGroup({keepSize:true},(q.enough?btn('구간 분석 시작',"runMemoryBatch('"+q.id+"')",'primary'):btn('크레딧 충전',"$('.modal')?.remove();go('credits')")),btn('구간 검토로 돌아가기','openMemoryTransfer()')));
})}
async function runMemoryBatch(id){if(educationBusy)return;educationBusy=true;try{const r=await api('/api/training/'+id+'/run',{});toast('구간 교육 결과 생성 · '+r.cost+' C');await refresh();$('.modal')?.remove();await render();}catch(err){toast(err.message);await openMemoryTransfer()}finally{educationBusy=false}}

async function brandDesign(id){await act(async()=>{
 const a=await api('/api/appearance?agent='+enc(id));
 modal('브랜드 디자인',fileUpload('brand-logo-file',{accept:'image/png,image/jpeg,image/webp',thumbnail:appearanceImage(a.logo,uiIcon('image')),buttonText:'이미지 선택',description:'브랜드 로고 · 400KB 이하'})+actionGroup({keepSize:true},btn('로고 저장',"saveBrandLogo('"+id+"')"),btn('로고 제거',"act(async()=>{await api('/api/appearance',{agent:'"+id+"',logo:''});$('.modal').remove();render()})"))+
 (has('design')?label('테마',select('brand-theme',[['dark','기본'],['toss','토스형'],['messenger','메신저형'],['premium','프리미엄형']],a.theme))+colorField('brand-color','테마 색상',a.color)+label('간격',select('brand-density',[['normal','기본'],['compact','촘촘하게'],['roomy','여유롭게']],a.density))+label('모서리',select('brand-radius',[['rounded','둥글게'],['square','각지게']],a.bubble_radius))+btn('디자인 저장',"saveBrandDesign('"+id+"')",'primary'):'<p>고급 디자인은 계정의 디자인 추가 기능을 구매하면 모든 브랜드에서 사용할 수 있습니다.</p>'));
})}
async function saveBrandLogo(id){await act(async()=>{const f=$('#brand-logo-file').files[0];if(!f||f.size>400000){toast('400KB 이하 이미지 파일을 선택하세요.');return;}const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f)});await api('/api/appearance',{agent:id,logo:data});$('.modal').remove();render()})}
async function saveBrandDesign(id){await act(async()=>{await api('/api/appearance',{agent:id,theme:val('brand-theme'),color:val('brand-color'),density:val('brand-density'),bubble_radius:val('brand-radius')});$('.modal').remove();render()})}

function showHandoffStatus(message){const area=$('#messages');if(!area)return;area.querySelector('.handoff-status')?.remove();const note=document.createElement('p');note.className='handoff-status muted';note.setAttribute('role','status');note.textContent=message;area.append(note);area.scrollTop=area.scrollHeight;}
async function requestStaffHandoff(){if(sending)return;if(!confirm('AI 자동 상담을 중지하고 담당자에게 연결을 요청할까요?'))return;await act(async()=>{const token=await getChatSession();const result=await api('/api/customer/handoff',{token});showHandoffStatus(result.notice||'담당자 연결을 요청했습니다. 답변은 이 창에서 확인할 수 있습니다.')});}

const workflowTasks={general:'일반 상담',price:'상품·가격',location:'위치·영업시간',purchase:'구매·결제 안내',booking:'예약 접수',change:'예약 변경',quote:'견적',refund:'환불 문의',complaint:'불만 문의'};
async function workflowModal(){await act(async()=>{
 const p=await api('/api/workflow?agent='+enc(qualityAgent)),days=['월','화','수','목','금','토','일'];
 modal('업무 인수인계 및 자동 전환', '<p>업무별 AI 상담 또는 담당자 처리를 지정합니다. 점검 완료는 사업주가 표시하며 자동 정확도 평가가 아닙니다. 기존 자동화 권한과 결제·예약 승인 제한은 유지됩니다.</p>'+Object.entries(workflowTasks).map(([k,n])=>'<div class="line"><label><input type="checkbox" data-work-check="'+k+'" '+(p.checked_tasks.includes(k)?'checked':'')+'> '+e(n)+' 교육·테스트 확인</label>'+select('workflow-'+k,[['auto','AI 상담 허용'],['staff','담당자 확인'],['off','자동 상담 금지']],p.tasks[k]||'auto')+'</div>').join('')+
 label('담당자에게 넘길 금지 키워드 (한 줄에 하나)',ta('workflow-blocked',p.blocked_terms.join('\n')))+label('긴급 확인 키워드 (한 줄에 하나)',ta('workflow-urgent',p.urgent_terms.join('\n')))+'<label><input type="checkbox" id="workflow-schedule" '+(p.schedule.enabled?'checked':'')+'> 설정한 시간 외에는 직접 상담으로 전환</label><div class="row">'+days.map((d,i)=>'<label><input type="checkbox" data-work-day="'+i+'" '+(p.schedule.days.includes(i)?'checked':'')+'> '+d+'</label>').join('')+'</div>'+label('AI 시작 시간',input('workflow-start',p.schedule.start,'time'))+label('AI 종료 시간',input('workflow-end',p.schedule.end,'time'))+'<p class="muted">업체 시간대 기준 · 키워드 일치 방식이라 모든 상황을 식별하지는 않습니다. 직접 상담으로 전환된 대화는 담당자가 명시적으로 AI를 재개해야 합니다.</p>'+btn('권한 저장','saveWorkflow()','primary'));
})}
async function saveWorkflow(){await act(async()=>{await api('/api/workflow',{agent:qualityAgent,tasks:Object.fromEntries(Object.keys(workflowTasks).map(k=>[k,val('workflow-'+k)])),blocked_terms:val('workflow-blocked').split('\n').map(s=>s.trim()).filter(Boolean),urgent_terms:val('workflow-urgent').split('\n').map(s=>s.trim()).filter(Boolean),checked_tasks:[...document.querySelectorAll('[data-work-check]:checked')].map(x=>x.dataset.workCheck),schedule:{enabled:checked('workflow-schedule'),days:[...document.querySelectorAll('[data-work-day]:checked')].map(x=>Number(x.dataset.workDay)),start:val('workflow-start'),end:val('workflow-end')}});$('.modal')?.remove();toast('업무 권한을 저장했습니다.');render()})}
async function downloadKnowledge(){await act(async()=>{const data=await api('/api/workflow/backup?agent='+enc(qualityAgent)),url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='csai-knowledge-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)})}
function openQualityThread(id){threadId=id;inboxAgent=qualityAgent;inboxKind='customer';go('inbox')}
async function reportCustomerAnswer(){if(!chatSession){toast('AI 답변을 받은 뒤 신고해 주세요.');return;}modal('AI 답변 오류 신고',label('어떤 내용이 잘못되었나요? (선택)',ta('answer-report-note'))+btn('신고 보내기',"act(async()=>{await api('/api/customer/answer-issue',{token:chatSession,note:val('answer-report-note')});$('.modal')?.remove();toast('운영자에게 전달했습니다.')})",'primary'))}
async function reportOwnerAnswer(){modal('최근 AI 답변 오류 표시',label('수정할 내용 (선택)',ta('owner-answer-note'))+btn('교육 검토에 추가',"act(async()=>{await api('/api/workflow/answer-issue',{thread:threadId,note:val('owner-answer-note')});$('.modal')?.remove();toast('교육 검토 목록에 추가했습니다.')})",'primary'))}
async function resolveAnswerIssue(id){await act(async()=>{await api('/api/workflow/answer-issue/'+id+'/resolve',{});render()})}
async function showAnswerContext(id){await act(async()=>{const r=await api('/api/workflow/answer-context/'+id);modal('답변 참고 교육 정보',r.available?'<p>정확 일치 자료 또는 모델에 전달한 교육 후보입니다. 모델이 실제로 사용한 근거라고 단정할 수 없습니다.</p><pre class="scrolltext">'+e(JSON.stringify(r.context,null,2))+'</pre>':'<p>기록된 참고 정보가 없습니다.</p>')})}
async function archiveBrand(id,archived){if(!confirm(archived?'공개 상담을 중지하고 브랜드를 보관할까요? 데이터와 구독 요금은 유지됩니다.':'보관을 해제할까요? 공개 설정은 별도로 켜야 합니다.'))return;await act(async()=>{await api('/api/workflow/archive',{agent:id,archived,confirmed:true});render()})}

async function rememberChatDevice(){if(sending)return;if(!confirm('공용 기기가 아니라면 현재 상담을 이 브라우저에서 최대 24시간 이어갈 수 있습니다. 새 상담을 시작하면 기억을 지웁니다. 기억할까요?'))return;await act(async()=>{const token=await getChatSession();await api('/api/customer/resume',{slug,token,action:'remember'});toast('이 기기에서 최대 24시간 상담을 이어갈 수 있습니다.')})}
async function newPublicChat(){if(sending)return;if(!confirm('이 기기의 상담 기억을 지우고 새 상담을 시작할까요? 업체의 기존 상담 기록은 삭제되지 않습니다.'))return;await act(async()=>{await api('/api/customer/resume',{slug,action:'forget'});sessionStorage.removeItem('csai-session-'+slug);chatSession=null;chatMessages=[];$('.modal')?.remove();$('#app').innerHTML='<div class="'+publicChatClass()+'">'+phone(pub)+'</div>';toast('새 상담을 시작하세요.')})}
async function prepareIssueEducation(id){await act(async()=>{if(educationBusy)return;const r=await api('/api/workflow/answer-issue/'+id+'/education');modal('정정 답변으로 교육','<p>기존 답변: '+e(r.previous)+'</p><p>신고 내용: '+e(r.note||'없음')+'</p>'+label('고객 질문',ta('issue-question',r.question))+label('정정 답변',ta('issue-answer'))+'<label><input type="checkbox" id="issue-consent"> 개인정보 및 교육 자료 사용 권한을 확인했습니다.</label>'+btn('교육 화면으로 가져오기',"loadIssueEducation("+JSON.stringify(r.agent).replaceAll('"','&quot;')+")",'primary'))})}
function loadIssueEducation(agent){if(educationBusy)return;if(!checked('issue-consent')||!val('issue-question').trim()||!val('issue-answer').trim()){toast('질문·정정 답변과 자료 이용 동의를 확인하세요.');return;}const q=val('issue-question'),a=val('issue-answer');resetEducationDraft();educationAgent=agent;trainingChat=[];estimate=null;educationDraft={values:{'faq-q':q,'faq-a':a},dates:[],files:[],upload:[],memory:[],open:[true,true]};$('.modal')?.remove();go('education')}

let readyDraftAgent='',readyDraftList=[];
async function offerReadyDrafts(agent='',always=false){
 await act(async()=>{const list=await api('/api/quality/ready-drafts?agent='+enc(agent));if(!list.length&&!always)return;readyDraftAgent=agent;readyDraftList=list;
 const labels={theme:'테마',color:'색상',open:'운영 시작',close:'운영 종료',duration:'소요 시간(분)'};
 modal('구매한 기능의 설정 초안','<p>구매 권한이 확인된 기능의 초안입니다. 실제 적용할 내용을 검토하고 승인하세요. 적용할 수 없는 자유 형식 메모는 보존합니다.</p>'+list.map((d,i)=>'<div class="line"><b>'+e(cfg.catalog.addons.find(x=>x.id===d.feature)?.name||d.feature)+'</b><p>'+Object.entries(d.config).map(([k,v])=>e(k)+': '+e(v)).join(' / ')+'</p>'+ (Object.keys(d.candidate).length?'<p>적용 값: '+Object.entries(d.candidate).map(([k,v])=>e(labels[k]||k)+': '+e(v)).join(' / ')+'</p>'+btn('이 설정 적용','applyReadyDraft('+i+')','primary'):'<p class="muted">수동 설정 필요</p>')+'</div>').join('')+(list.length?'':'<p class="muted">구매한 기능의 초안이 없습니다.</p>'));
 })
}
async function applyReadyDraft(i){const d=readyDraftList[i],agent=readyDraftAgent;if(!d||!confirm('표시된 설정만 실제로 적용할까요?'))return;await act(async()=>{await api('/api/quality/feature-draft/'+enc(d.feature)+'/apply',{agent,updated:d.updated,candidate:d.candidate,confirmed:true});await refresh();$('.modal')?.remove();toast('설정 적용 완료');render()})}

function calendarBookingPath(id=''){return (calendarAgent?'/api/brand-calendar/'+enc(calendarAgent)+'/bookings':'/api/bookings')+(id?'/'+enc(id):'')}
function switchCalendarBrand(agent){calendarAgent=agent;calendarProfile=null;calendarRange=null;calendarRangeAnchor='';selectedDate=null;render()}
function brandCalendarSettings(){const s=calendarProfile;if(!s)return;modal('브랜드 예약 설정',`<div class="booking-settings-form">${label('고객 예약 모드',select('bc-booking-mode',[['off','고객 예약 끄기'],['manual','수동 승인'],['auto','자동 확정']],s.booking_mode||'off'))}${helperText('자동 확정은 자동 예약 옵션 및 위험 안내 동의가 필요합니다.')}${bookingScheduleFields('bc',s)}<h3>예약 불가 일정</h3>${helperText('지정한 시간에는 신규 예약 및 변경이 차단됩니다.')}${bookingBlockFields('bc',s)}${checkbox('bc-payment','외부 결제 확인 필요',{checked:s.payment_required})}${has('change_booking')?checkbox('bc-change','고객 변경·취소 요청 허용 (담당자 승인)',{checked:s.allow_customer_change}):''}${actionFooter([btn('저장','saveBrandCalendarSettings()','primary')])}</div>`);}
async function saveBrandCalendarSettings(){await act(async()=>{await api('/api/brand-calendar/'+enc(calendarAgent)+'/settings',{booking_mode:val('bc-booking-mode'),timezone:val('bc-tz'),open:val('bc-open'),close:val('bc-close'),duration:Number(val('bc-duration')),buffer:Number(val('bc-buffer')),closed_days:[...document.querySelectorAll('.bc-closed:checked')].map(x=>Number(x.value)),blocked_times:readBookingBlocks('bc'),payment_required:checked('bc-payment'),...($('#bc-change')?{allow_customer_change:checked('bc-change')}:{})});$('.modal')?.remove();render()})}
let brandCalendarFieldsDraft=[];
function brandCalendarFields(reset=true){if(!calendarProfile)return;if(reset)brandCalendarFieldsDraft=structuredClone(calendarProfile.fields);modal('브랜드 맞춤 일정 양식',brandCalendarFieldsDraft.map((f,i)=>'<div class="line">'+label('항목 이름',input('bc-field-'+i,f.label))+label('형식',select('bc-type-'+i,['text','phone','number','date','time','select','boolean'].map((x,j)=>[x,['텍스트','전화','숫자','날짜','시간','선택','예/아니오'][j]]),f.type))+label('선택지 (쉼표 구분)',input('bc-options-'+i,(f.options||[]).join(',')))+'<label><input type="checkbox" id="bc-required-'+i+'" '+(f.required?'checked':'')+'> 필수</label>'+btn('삭제','changeBrandCalendarFields('+i+')')+'</div>').join('')+actionGroup({keepSize:true},btn('항목 추가','changeBrandCalendarFields(-1)'),btn('양식 저장','saveBrandCalendarFields()','primary')))}
function captureBrandCalendarFields(){brandCalendarFieldsDraft.forEach((f,i)=>{f.label=val('bc-field-'+i);f.type=val('bc-type-'+i);f.options=val('bc-options-'+i).split(',').map(x=>x.trim()).filter(Boolean);f.required=checked('bc-required-'+i)})}
function changeBrandCalendarFields(i){captureBrandCalendarFields();if(i<0)brandCalendarFieldsDraft.push({key:'f_'+crypto.randomUUID().slice(0,8),label:'새 항목',type:'text',required:false,options:[]});else brandCalendarFieldsDraft.splice(i,1);brandCalendarFields(false)}
async function saveBrandCalendarFields(){await act(async()=>{captureBrandCalendarFields();await api('/api/brand-calendar/'+enc(calendarAgent)+'/settings',{fields:brandCalendarFieldsDraft});$('.modal')?.remove();render()})}

// Focus is a local display preference, not a delivery policy.
function focusKey(){return 'csai-focus-'+me.slug}
function focusEvents(events){const seenSamples=new Set();events=[...events].sort((a,b)=>(b.created||0)-(a.created||0)).filter(x=>{if(!x.sample)return true;const key=x.kind+'|'+sampleDisplayText(x.title,true);if(seenSamples.has(key))return false;seenSamples.add(key);return true;});let on=false;try{on=sessionStorage.getItem(focusKey())==='1'}catch{}const held=events.filter(x=>x.kind!=='handoff_urgent'),urgent=events.filter(x=>x.kind==='handoff_urgent');const row=x=>`<div class="line focus-event${x.sample?' sample-record':''}"><div class="sample-title-row"><b>${e(sampleTitle(x.title,x.sample))}</b></div><p class="muted">${e(new Date(x.created*1000).toLocaleString())} · ${x.seen?'읽음':'새 알림'}</p></div>`;return card('업무 알림 기록',`<div class="focus-bar"><div><b>화면 집중 모드</b><small>일반 알림을 접어두고 긴급 알림을 우선 확인합니다. 실제 알림 수신과 읽음 상태는 그대로 유지됩니다.</small></div><span class="focus-count">${held.filter(x=>!x.seen).length}개</span><button class="focus-toggle" type="button" role="switch" aria-label="화면 집중 모드" aria-checked="${on}" onclick="toggleFocus(this)"><span aria-hidden="true"></span></button></div><div class="focus-urgent">${urgent.map(row).join('')}</div><details class="ui-disclosure focus-held" ${on?'':'open'}><summary>일반 알림 ${held.length}개</summary><div>${held.map(row).join('')||emptyState('알림이 없습니다.')}</div></details>`+btn('모두 읽음',"act(async()=>{if(freeFeaturePreview())previewData().events.forEach(x=>x.seen=true);await api('/api/events/read',{});render()})"))}
function toggleFocus(button){const on=button.getAttribute('aria-checked')!=='true';button.setAttribute('aria-checked',String(on));try{sessionStorage.setItem(focusKey(),on?'1':'0')}catch{}const panel=button.closest('.card').querySelector('.focus-held');if(panel)panel.open=!on;const chip=button.closest('.focus-bar').querySelector('.focus-count');if(chip&&chip.animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches)chip.animate([{transform:'scale(.85)'},{transform:'scale(1.12)'},{transform:'scale(1)'}],{duration:260});}

function importKnowledgeModal(){const agent=qualityAgent;modal('교육 백업 가져오기','<p>선택한 브랜드의 검토 대기 교육으로 가져옵니다. 기존 교육은 승인 전까지 유지됩니다. 백업의 FAQ와 승인된 교육만 가져오며 이전 버전 기록과 원본 파일은 제외됩니다.</p><p class="muted">AI 호출 및 크레딧 차감 없음 · 다른 업체 자료를 가져올 권한이 있는지 확인하세요.</p>'+fileUpload('knowledge-backup-file',{accept:'.json,application/json'})+'<label class="ui-check"><input class="ui-choice" type="checkbox" id="knowledge-backup-consent"><span>교육 자료를 검토했고 가져올 권한이 있습니다.</span></label>'+actionFooter([btn('검토 대기로 가져오기',`importKnowledgeBackup('${agent}')`,'primary')]))}
async function importKnowledgeBackup(agent){await act(async()=>{const f=$('#knowledge-backup-file')?.files?.[0];if(!f||f.size>2*1024*1024)throw Error('2 MiB 이하의 JSON 백업 파일을 선택하세요.');if(!checked('knowledge-backup-consent'))throw Error('교육 자료 가져오기 확인이 필요합니다.');const backup=JSON.parse(await f.text());const r=await api('/api/workflow/backup/import',{agent,backup,confirmed:true});$('.modal')?.remove();toast('교육 검토 대기 · FAQ '+r.faq_count+'개');educationAgent=agent;go('education');})}

function pauseLabel(reason){return ({account:'전체 직접 상담',brand:'브랜드 직접 상담',channel:'채널 직접 상담',brand_channel:'브랜드 채널 직접 상담'})[reason]||'직접 상담'}
function consultationControls(modes,brands,channelPage=false){
 const paused=(a,c)=>modes.paused.some(x=>x.agent===a&&x.channel===c);
 const agent=channelPage?'all':inboxAgent;
 const account=paused('*','*');
 const row=(a,c,name)=>{
  const own=paused(a,c),inherited=!own&&(account||a!=='*'&&paused(a,'*')||c!=='*'&&paused('*',c));
  return `<div class="line ui-inline consultation-mode-row">
   <div class="consultation-mode-copy">
    <strong>${e(name)}</strong>
    ${helperText(own?'직접 상담 지정됨':inherited?'상위 직접 상담 적용 중':'AI 상담 허용')}
    ${inherited?'<small>상위 설정 우선</small>':''}
   </div>
   ${btn(own?'직접 상담 해제':'직접 상담 전환',`setConsultationMode('${a}','${c}',${!own})`)}
  </div>`;
 };
 let out=row('*','*','전체 브랜드·채널');
 if(agent!=='all')out+=row(agent,'*',brands.find(x=>x.id===agent)?.settings.brand||me.settings.brand);
 out+=row('*','public','전체 웹 상담');
 if(has('naver')||paused('*','naver'))out+=row('*','naver','네이버 톡톡');
 if(has('kakao')||paused('*','kakao'))out+=row('*','kakao','카카오 AI 챗봇');
 if(agent!=='all')out+=row(agent,'public','선택 브랜드 웹 상담');
 return accordion('전체·채널·브랜드 상담 모드'+(account?' · 전체 직접 상담 중':''),
  '<p class="muted">직접 상담은 새 AI 답변과 상담량 차감을 중지합니다. 이미 생성 중인 답변은 완료될 수 있으며, 개별 담당자 전환 및 업무 권한은 유지됩니다. 외부 직접 답변은 해당 채널 관리자에서 처리하세요.</p>'+out,
  {className:'consultation-mode-panel',open:channelPage});
}
async function setConsultationMode(agent,channel,manual){if(!confirm(manual?'이 범위의 새 AI 상담을 중지하고 직접 상담으로 전환할까요?':'이 범위의 직접 상담 지정을 해제할까요? 다른 범위 및 개별 상담 설정은 유지됩니다.'))return;await act(async()=>{await api('/api/consultation-mode',{agent,channel,manual,confirmed:true});toast('상담 모드를 변경했습니다.');render()})}

let externalReplyBusy=false,externalReplyDraft=null;
function externalReplyControls(t,showComposer=true){
 const info=t.channel_reply||{},jobs=info.jobs||[],inbound=info.inbound||[];
 const statuses={queued:'발송 대기',running:'발송 중',sent:'발송 확인',failed:'발송 취소·실패',unknown:'발송 결과 미확인'};
 const history=jobs.map(x=>'<p class="muted">'+e(statuses[x.status]||x.status)+' · '+e(new Date(x.created*1000).toLocaleString('ko-KR'))+(x.error?' · '+e(x.error):'')+'</p>').join('');
 const autoHistory=inbound.map(x=>'<p class="muted">'+e(({sent:'외부 응답 전송 확인',held:'수동 상담 접수',failed:'외부 응답 실패·미확인',running:'외부 응답 처리 중',cancelled:'처리 취소'})[x.status]||x.status)+' · '+e(new Date(x.created*1000).toLocaleString('ko-KR'))+(x.error?' · '+e(x.error):'')+'</p>').join('');
 const busy=jobs.some(x=>['queued','running'].includes(x.status));
 return (['naver','telegram'].includes(t.kind)&&info.available?(showComposer?replyWithHistory('external-reply',inboxChannel(t)+' 직접 답변',t.messages,{maxLength:1000})+(busy?'<p class="muted">이전 답변 발송 중</p>':btn('채널로 전송','sendExternalReply()','primary')):''):'<p class="muted">'+(t.kind==='instagram'?'Instagram DM 답변은 Instagram에서 직접 진행하세요. CSAI는 수신 기록만 표시합니다.':t.kind==='line'?'LINE 수동 답변은 공식 계정 관리자에서 진행하세요. 이곳에서는 상담 기록을 조회합니다.':t.kind==='kakao'?'AI 상담 기록만 조회할 수 있습니다. 사람 상담 및 그 기록은 카카오 채널 관리자센터에서 확인하세요.':'네이버 직접 발송 허용 및 새 고객 메시지 수신 후 전송할 수 있습니다.')+'</p>')+(t.kind==='kakao'?'<a class="channel-action" href="https://center-pf.kakao.com/" target="_blank" rel="noopener noreferrer">카카오에서 직접 상담하기</a>':'')+history+(autoHistory?'<details class="ui-disclosure"><summary>외부 채널 처리 내역</summary>'+autoHistory+'</details>':'')+btn('발송 상태 새로고침','render()');
}
async function sendExternalReply(){
 if(externalReplyBusy)return;
 const id=threadId,reply=val('external-reply').trim();if(!reply||reply.length>1000)return toast('답변은 1~1000자로 입력하세요.');
 if(!confirm('이 고객의 연결 채널로 직접 답변을 발송할까요? 이 상담은 담당자 모드로 전환됩니다.'))return;
 if(!externalReplyDraft||externalReplyDraft.id!==id||externalReplyDraft.reply!==reply)externalReplyDraft={id,reply,client:crypto.randomUUID()};
 externalReplyBusy=true;
 try{const t=await api('/api/inbox/'+enc(id));if(threadId!==id||!t.manual||!t.channel_reply?.available)throw Error('직접 상담 모드와 채널 연결 상태를 확인하세요.');if((t.channel_reply.jobs||[]).some(x=>['queued','running'].includes(x.status)))throw Error('이전 답변 발송 중입니다.');await api('/api/inbox/'+enc(id)+'/channel-reply',{reply,client:externalReplyDraft.client,confirmed:true});externalReplyDraft=null;toast('발송을 접수했습니다. 발송 상태를 확인하세요.');await render()}catch(x){toast(x.message)}finally{externalReplyBusy=false}
}

function renderInboxList(ts,brands){if(inboxCenter())return renderCenterList(ts);return ts.map(t=>`<button type="button" onclick="openInboxThread('${t.id}')" class="line inbox-entry ${threadId===t.id?'selected':''}${t.sample?' sample-record':''}"><small>${e(brands.find(a=>a.id===t.agent)?.settings.brand||(t.agent?'이전 브랜드':me.settings.brand))} · ${inboxChannelBadge(t)} · ${e(states[t.status]||t.status)}${t.manual?' · 개별 직접 상담':t.paused_by?' · '+e(pauseLabel(t.paused_by)):' · AI 허용'} · ${e(new Date((t.activity||t.created)*1000).toLocaleDateString('ko-KR'))}</small><span class="inbox-excerpt">${t.consultation?.title?'<strong>'+e(consultationTitle(t))+'</strong> · ':''}${e(t.consultation?.summary||sampleTitle(t.last||'새 상담',t.sample))}</span>${t.unread?`<span class="status">새 문의 ${t.unread}건</span> `:''}${!t.sample&&t.kind!=='test'&&(t.assignment?.assignee||t.assignment?.priority==='urgent'||t.assignment?.priority==='high'||t.assignment?.due_date)?`<small>${e(t.assignment.assignee||'미배정')} · ${e(priorityNames[t.assignment.priority]||'보통')}${t.assignment.due_date?' · 기한 '+e(t.assignment.due_date):''}</small> `:''}</button>`).join('')||emptyState('조건에 맞는 상담이 없습니다.');}
async function openInboxThread(id){if(threadId&&id!==threadId){if(inboxReplyDraftActive()&&!confirm('작성 중인 내용을 닫고 다른 상담을 열까요?'))return;await leaveTemporary();}threadId=id;await render()}
async function markInboxRead(id,msg){await act(async()=>{await api('/api/inbox/'+enc(id)+'/read',{message:msg});toast('읽음 처리했습니다.');await pollInbox(true)})}
async function refreshInboxNow(){if((['staff-reply','external-reply'].some(id=>$('#'+id)?.value)||$('#inbox-note')?.value!==$('#inbox-note')?.defaultValue||$('#inbox-tags')?.value!==$('#inbox-tags')?.defaultValue)&&!confirm('작성 중인 답변 또는 메모가 있습니다. 새로고침할까요?'))return;await render()}
function inboxRefreshScope(){
 return JSON.stringify([route,renderId,inboxAgent,inboxKind,inboxSource,inboxQuery,inboxUnread,inboxPriority,threadId]);
}
function pollInbox(force=false){
 const list=$('#inbox-live-list');
 if(!me||!inboxWorkspace()||!list||document.hidden)return Promise.resolve(false);
 const scope=inboxRefreshScope();
 if(inboxPolling?.scope===scope)return inboxPolling.request;
 const isCurrent=()=>inboxWorkspace()&&list.isConnected&&scope===inboxRefreshScope();
 const request=(async()=>{
  try{
   const threads=await loadInboxThreads();
   if(!isCurrent())return false;
   const next=JSON.stringify(threads);
   const changed=next!==inboxSnapshot;
   if(changed){
    list.innerHTML=renderInboxList(threads,inboxBrands);
    inboxSnapshot=next;
   }
   if(inboxCenter())refreshCenterAges(list);
   if(threadId){
    let detail=await inboxDetailFor(threadId);
    if(!isCurrent())return false;
    const lease=inboxTemporary(detail);
    if(lease&&inboxReplyDraftActive()&&Date.now()/1000>lease.expires-30&&Date.now()-temporaryRenewAt>10000){temporaryRenewAt=Date.now();if(detail.sample){lease.expires=Date.now()/1000+(lease.seconds||300);}else{await api('/api/inbox/'+enc(threadId),{renew_temporary:lease.lease});detail=await api('/api/inbox/'+enc(threadId));if(!isCurrent())return false;}}
    rememberTemporary(detail);const timer=$('[data-temporary-expires]');if(timer&&activeTemporary)timer.dataset.temporaryExpires=activeTemporary.expires;
    const chat=$('.inbox-conversation'),signature=JSON.stringify(detail.messages),mode=inboxModeKey(detail);
    if(chat&&signature!==inboxDetailSignature){const bottom=chat.scrollHeight-chat.scrollTop-chat.clientHeight<80;const top=chat.scrollTop;chat.innerHTML=inboxMessageMarkup(detail);chat.scrollTop=bottom?chat.scrollHeight:top;inboxDetailSignature=signature;}
    if(mode!==inboxModeSignature){
     if(!inboxReplyDraftActive()&&!ownerReplyBusy&&!externalReplyBusy&&!sampleInboxSending){await render();return true;}
     const area=$('.inbox-live-mode');if(area)area.innerHTML=inboxModeBar(detail);
     const composer=$('.owner-compose');if(composer)composer.querySelectorAll('textarea,button').forEach(x=>x.disabled=!inboxDirect(detail)||!inboxCanReply(detail));
    }
   }
   if($('#inbox-live-status'))$('#inbox-live-status').textContent='상담 자동 갱신 중 · 3초 간격';
   return true;
  }catch{
   if(isCurrent())$('#inbox-live-status').textContent='목록 갱신 실패 · 새로고침을 이용하세요.';
   return false;
  }finally{
   if(inboxPolling?.request===request)inboxPolling=null;
  }
 })();
 inboxPolling={scope,request};
 return request;
}
function mountInboxPullRefresh(){
 const list=$('#inbox-live-list');
 if(!list)return;
 const panel=list.closest('.inbox-pull');if(!panel)return;const indicator=panel.querySelector('[data-pull-label]');
 const announcement=panel.querySelector('[role=status]');
 const threshold=80;
 let gesture=null,refreshing=false,feedbackTimer=0;
 function setState(state,height,label=''){
  panel.dataset.pullState=state;
  panel.style.setProperty('--pull-height',height+'px');
  panel.style.setProperty('--pull-stretch',Math.min(1.16,.35+height/54));
  indicator.textContent=label;
 }
 list.addEventListener('touchstart',event=>{
  if(refreshing||list.scrollTop>1||event.touches.length!==1){gesture=null;return;}
  clearTimeout(feedbackTimer);
  if(panel.dataset.pullState==='feedback')setState('idle',0);
  const touch=event.touches[0];
  gesture={id:touch.identifier,x:touch.clientX,y:touch.clientY,distance:0};
 },{passive:true});
 list.addEventListener('touchmove',event=>{
  if(!gesture)return;
  const touch=event.touches[0];
  if(event.touches.length!==1||touch.identifier!==gesture.id){
   gesture=null;setState('idle',0);return;
  }
  const down=touch.clientY-gesture.y,side=Math.abs(touch.clientX-gesture.x);
  if(!gesture.distance&&(down<-6||side>Math.max(8,down)||list.scrollTop>1)){gesture=null;return;}
  if(down<=6&&!gesture.distance)return;
  if(!event.cancelable){gesture=null;setState('idle',0);return;}
  event.preventDefault();
  gesture.distance=Math.max(0,down);
  const armed=down>=threshold;
  setState(armed?'armed':'pulling',Math.min(48,gesture.distance*.56),armed?'놓으면 새로고침':'당겨서 새로고침');
 },{passive:false});
 list.addEventListener('touchcancel',()=>{
  gesture=null;
  if(!refreshing)setState('idle',0);
 },{passive:true});
 list.addEventListener('touchend',async event=>{
  if(!gesture||![...event.changedTouches].some(touch=>touch.identifier===gesture.id))return;
  const armed=gesture.distance>=threshold;
  gesture=null;
  if(!armed){setState('idle',0);return;}
  refreshing=true;
  announcement.textContent='';
  setState('refreshing',44,'상담 기록 불러오는 중');
  const ok=await pollInbox(true);
  refreshing=false;
  if(!panel.isConnected)return;
  const message=ok?'상담 기록을 새로고침했습니다.':'상담 기록 갱신에 실패했습니다.';
  announcement.textContent=message;
  setState('feedback',44,message);
  feedbackTimer=setTimeout(()=>{if(panel.isConnected)setState('idle',0);},1200);
 },{passive:true});
}
setInterval(()=>pollInbox(),3000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)pollInbox(true)});
const priorityNames={low:'낮음',normal:'보통',high:'높음',urgent:'긴급'};
function inboxAssignmentHtml(a){return '<details class="ui-disclosure"><summary>담당자·처리 우선순위</summary><p class="muted">담당자 이름은 기존 내부 메모입니다. 실제 직원 계정 접근 권한은 직원 계정 배정에서 관리합니다.</p>'+label('담당자 이름',input('inbox-assignee',a.assignee))+label('우선순위',select('inbox-assignment-priority',Object.entries(priorityNames),a.priority))+label('처리 기한',input('inbox-due-date',a.due_date,'date'))+actionFooter([btn('직원 계정 배정','assignTeamMember()'),btn('배정 저장','saveInboxAssignment()','primary')])+'</details>'}
async function saveInboxAssignment(){const tid=threadId;await act(async()=>{await api('/api/inbox/'+enc(tid)+'/assignment',{assignee:val('inbox-assignee'),priority:val('inbox-assignment-priority'),due_date:val('inbox-due-date')});toast('담당자 및 처리 우선순위를 저장했습니다.');await pollInbox(true)})}
function inboxAnnotationHtml(a){return '<details class="ui-disclosure"><summary>고객 상담 메모·태그</summary>'+label('내부 메모',ta('inbox-note',a.note))+label('태그 (쉼표 구분)',input('inbox-tags',a.tags.join(', ')))+actionFooter([btn('메모 저장','saveInboxAnnotation()','primary')])+'</details>'}
async function saveInboxAnnotation(){await act(async()=>{await api('/api/inbox/'+enc(threadId)+'/annotation',{note:val('inbox-note'),tags:val('inbox-tags').split(',').map(x=>x.trim()).filter(Boolean)});$('#inbox-note').defaultValue=val('inbox-note');$('#inbox-tags').defaultValue=val('inbox-tags');toast('내부 메모를 저장했습니다.')})}
async function manageInboxSnippets(){await act(async()=>{inboxSnippets=await api('/api/inbox-snippets');modal('자주 쓰는 답변',inboxSnippets.map(x=>'<div class="line"><strong>'+e(x.title)+'</strong><p>'+e(x.body)+'</p>'+btn('삭제',`deleteInboxSnippet('${x.id}',this)`)+'</div>').join('')+label('제목',input('snippet-title',''))+label('답변',ta('snippet-body'))+btn('저장','saveInboxSnippet()','primary'))})}
async function saveInboxSnippet(){await act(async()=>{await api('/api/inbox-snippets',{title:val('snippet-title'),body:val('snippet-body')});await manageInboxSnippets()})}
async function deleteInboxSnippet(id,button){if(confirm('저장 답변을 삭제할까요?'))await deleteVisibleRow('/api/inbox-snippets/'+enc(id),button,manageInboxSnippets);}
function chooseInboxSnippet(){modal('저장 답변 선택',inboxSnippets.map(x=>'<div class="line"><strong>'+e(x.title)+'</strong><p>'+e(x.body)+'</p>'+btn('답변에 넣기',`insertInboxSnippet('${x.id}')`)+'</div>').join(''))}
function insertInboxSnippet(id){const x=inboxSnippets.find(s=>s.id===id),target=$('#staff-reply')||$('#external-reply');if(!x||!target){toast('답변 가능한 상담을 선택하세요.');return;}target.value+=(target.value?'\n':'')+x.body;$('.modal')?.remove();target.focus();target.dispatchEvent(new Event('input',{bubbles:true}))}


async function showDeliveryIssues(){await act(async()=>{const rows=await api('/api/channel-delivery-issues'),statuses={queued:'대기',running:'처리 중',failed:'실패·미확인',unknown:'발송 결과 미확인',cancelled:'취소'};modal('외부 채널 발송 관리','<p class="muted">최근 조회 가능 범위 내 최대 100건. 결과가 불명확하면 원래 채널에서 먼저 확인하세요. 자동 재전송하지 않습니다.</p>'+ (rows.map(x=>'<div class="line"><strong>'+e(channelNames[x.channel]||x.channel)+' · '+e(x.origin==='staff'?'직접 답변':'자동 처리')+'</strong><p>'+e(statuses[x.status]||x.status)+' · '+e(new Date(x.updated*1000).toLocaleString('ko-KR'))+'</p><p>'+e(x.error||'')+'</p>'+(x.thread?btn('연결 상담 열기',`openDeliveryThread('${x.thread}')`):'<small>상담 연결 전 발생</small>')+'</div>').join('')||emptyState('표시할 발송 문제가 없습니다.')))})}
function openDeliveryThread(id){$('.modal')?.remove();threadId=id;inboxAgent='all';inboxKind='customer';inboxSource='all';inboxUnread=false;inboxQuery='';if(inboxWorkspace())render();else go('inbox')}

let replyAssistantBusy=false,replyAssistantPending=null,replyAssistantResults=[];
const replyAssistantDescription='개인 메시지·메일·SNS의 답장 초안을 만듭니다. 답장은 자동으로 발송되지 않습니다.';
function replyAssistantForm(tid=''){
 const medium=select('reply-medium',[['message','메신저·SNS·문자'],['email','이메일']],'message').replace('<select','<select onchange="syncReplyMedium()"');
 const source=tid?'':`<div class="reply-medium">${label('답장 대상',medium)}</div>
  ${label('받은 메시지','<textarea id="reply-source" maxlength="4000" placeholder="답장할 메시지를 붙여넣으세요."></textarea>',{labelId:'reply-source-label'})}`;
 const submit=btn('답장 3개 생성',tid?`generateReplyAssistant('${tid}')`:'generateReplyAssistant()','primary');
 return `<div class="reply-form">
  ${source}
  ${label('내가 전달할 내용 (선택)','<textarea id="reply-intent" maxlength="1000" placeholder="예: 일정은 아직 미정, 정중하게 거절"></textarea>')}
  <fieldset class="ui-fieldset reply-style-fieldset">
   <legend>답장 스타일</legend>
   <div class="reply-styles">${['간결하게','친근하게','정중하게'].map((style,i)=>label('스타일 '+(i+1),input('reply-style-'+i,style))).join('')}</div>
  </fieldset>
  <div class="reply-submit ui-action-footer is-divided">
   <p class="ui-hint">메시지와 입력 내용을 AI로 처리합니다. 초안 3개를 만들 때 상담 사용량 1회가 차감됩니다.</p>
   <div class="ui-action-row">
    ${checkbox('reply-consent','메시지 처리 권한과 상담량 차감을 확인했습니다.')}
    ${submit}
   </div>
  </div>
 </div>`;
}
function replyAssistantResultsPanel(){
 return '<div id="reply-assistant-results" class="reply-results" aria-live="polite">'+emptyState('답장을 생성하면 여기에 초안이 표시됩니다.')+'</div>';
}
function syncReplyMedium(){const email=val('reply-medium')==='email';$('#reply-source-label').textContent=email?'받은 이메일 (제목과 본문)':'받은 메시지';$('#reply-source').placeholder=email?'이메일 제목과 본문을 붙여넣으세요.':'답장할 메시지를 붙여넣으세요.'}
function replyAssistantPage(){
 return pageTop('답장 비서',replyAssistantDescription)+`<div class="reply-workspace">
  ${card('답장 만들기',replyAssistantForm())}
  ${card('생성 결과',`<div class="ui-stack">${replyAssistantResultsPanel()}
   <div class="ui-section"><p class="muted">통합 상담함에서 문의를 열면 교육 내용을 반영한 답장 초안을 사용할 수 있습니다. 지원 채널은 상담 입력창에 삽입할 수 있습니다.</p>${btn('통합 상담함 열기',"go('inbox')",'tertiary')}</div>
   <div class="ui-section"><p class="muted">Gmail 등 이메일 수신·발송, 모바일 알림 및 외부 DM 연동은 준비 중입니다.</p></div>
  </div>`)}
 </div>`;
}
function consultationBriefHtml(p){if(!p)return '';return '<div class="line"><strong>'+e(p.title||'상담 요약')+'</strong><p>'+e(p.summary||'')+'</p><small>'+ (p.source==='ai'?'AI 요약 · 원문 확인 필요':'자동 분류 · 고객 최근 발화')+'</small>'+(p.booking?'<p>예약: '+e(states[p.booking.status]||p.booking.status)+'</p>':'')+(p.booking?.fields||p.draft_fields||[]).map(f=>'<p>'+e(f.label)+': '+e(f.value)+'</p>').join('')+(p.draft_fields?.length?'<small>고객 확인 전 입력 정보</small>':'')+'</div>';}
async function showInboxBrief(){const tid=threadId;await act(async()=>{const r=await api('/api/inbox/'+enc(tid)+'/brief');if(threadId!==tid||!inboxWorkspace())return;modal('상담 핵심 보기','<p class="muted">최근 상담 요약과 발화자별 원문을 보여줍니다. 별도 AI 호출이나 사용량 차감이 없습니다.</p>'+consultationBriefHtml(r.consultation)+'<p>'+e(states[r.status]||r.status)+(r.latest_is_customer?' · 최근 고객 문의가 마지막 메시지입니다.':'')+(r.manual||r.paused_by?' · AI 응답 중지 상태':'')+'</p>'+r.recent.map(m=>'<div class="line"><strong>'+e(({user:'고객',assistant:'AI 상담사',staff:'담당자'})[m.role])+'</strong><p>'+e(m.body)+(m.truncated?' …':'')+'</p><small>'+e(new Date(m.created*1000).toLocaleString('ko-KR'))+'</small></div>').join('')+(r.note?'<div class="line"><strong>내부 메모</strong><p>'+e(r.note)+'</p></div>':'')+(r.tags.length?'<p>태그: '+e(r.tags.join(', '))+'</p>':'')+btn('원문 확인', "document.querySelector('.modal')?.remove()"))})}
function openInboxDraftAssistant(){modal('AI 답장 추천',`<p class="ui-hint">${e(replyAssistantDescription)}</p>`+replyAssistantForm(threadId)+replyAssistantResultsPanel())}
async function generateReplyAssistant(tid=''){
 if(replyAssistantBusy)return;
 if(!$('#reply-consent')?.checked)return toast('메시지 처리 및 사용량 차감을 확인하세요.');
 const message=tid?'':val('reply-source').trim(),intent=val('reply-intent'),styles=[0,1,2].map(i=>val('reply-style-'+i).trim());
 if(!tid&&!message)return toast('받은 메시지를 입력하세요.');
 if(styles.some(x=>!x)||new Set(styles).size!==3)return toast('서로 다른 스타일 세 가지를 입력하세요.');
 const params={thread:tid,message,intent,styles,confirmed:true,...(!tid?{medium:val('reply-medium')}: {})};
 const key=JSON.stringify(params),target=$('#reply-assistant-results'),submit=$('#reply-consent')?.closest('.reply-form')?.querySelector('.reply-submit button');
 if(!replyAssistantPending||replyAssistantPending.key!==key)replyAssistantPending={key,client:crypto.randomUUID()};
 replyAssistantBusy=true;if(target)target.textContent='답장 생성 중…';
 if(submit){submit.disabled=true;submit.setAttribute('aria-busy','true');}
 try{
  const r=await api('/api/reply-assistant',{...params,client:replyAssistantPending.client});
  replyAssistantPending=null;replyAssistantResults=r.drafts;me.remaining=r.remaining;
  if(!target?.isConnected)return;
  target.innerHTML=(r.demo?'<p class="muted">로컬 데모 · 실제 AI 답장 아님</p>':'')+r.drafts.map((x,i)=>'<div class="line"><strong>'+e(x.style)+'</strong><p id="assistant-draft-'+i+'">'+e(x.text)+'</p>'+actionGroup({keepSize:true},copyButton('답장 복사','assistant-draft-'+i),(tid&&($('#staff-reply')||$('#external-reply'))?btn('상담 답변에 넣기',`insertAssistantDraft(${i},'${tid}')`):''))+'</div>').join('')+'<p class="muted">남은 상담 사용량 '+e(String(r.remaining))+'회</p>';
 }catch(err){if(String(err.message).includes('이전 요청 시간이 초과'))replyAssistantPending=null;if(target?.isConnected)target.textContent=err.message;toast(err.message)}finally{replyAssistantBusy=false;if(submit){submit.disabled=false;submit.removeAttribute('aria-busy');}}
}
function insertAssistantDraft(i,tid){const x=replyAssistantResults[i];if(threadId!==tid||!x)return;const field=$('#staff-reply')||$('#external-reply');if(!field)return toast('이 채널은 직접 발송을 지원하지 않습니다. 복사를 이용하세요.');if(field.value&&!confirm('작성 중인 답변을 교체할까요?'))return;field.value=x.text;$('.modal')?.remove();field.focus();field.dispatchEvent(new Event('input',{bubbles:true}))}

async function closeAndResumeAI(){if(!confirm('상담을 완료하고 이 고객의 개별 수동 설정을 해제할까요? 전체·브랜드·채널 수동 설정은 유지됩니다.'))return;await updateThread({status:'resolved',resume_on_close:true})}
async function showRelatedThreads(){const id=threadId;await act(async()=>{const r=await api('/api/inbox/'+enc(id)+'/related');modal('동일 고객 이전 상담',r.verified?(r.threads.map(t=>'<div class="line"><strong>'+e(new Date(t.activity*1000).toLocaleString('ko-KR'))+'</strong> · '+e(states[t.status]||t.status)+btn('상담 열기',`openDeliveryThread('${t.id}')`)+'</div>').join('')||'<p>연결된 이전 상담이 없습니다.</p>'):'<p>이 상담은 검증된 외부 고객 식별 정보가 없습니다. 새로 수신한 메시지부터 같은 채널·연결 내 고객 이력을 연결합니다.</p>')})}
async function showChannelMetrics(days=30){await act(async()=>{const r=await api('/api/inbox-channel-metrics?days='+days);modal('채널별 상담 통계',[7,30,90].map(n=>btn(n+'일',`showChannelMetrics(${n})`)).join('')+'<p class="muted">'+e(r.note)+'</p>'+ (r.channels.map(x=>'<div class="line"><strong>'+e(channelNames[x.channel]||x.channel)+'</strong><p>상담 '+x.threads+' · 고객 메시지 '+x.inbound+' · AI 기록 '+x.ai_messages+' · 담당자 답변 '+x.staff_messages+'</p></div>').join('')||'<p>상담 기록이 없습니다.</p>')+'<h3>외부 처리 상태</h3>'+r.auto_delivery.concat(r.staff_delivery.map(x=>({...x,staff:true}))).map(x=>'<p>'+e(channelNames[x.channel]||x.channel)+' · '+(x.staff?'직접':'자동')+' · '+e(x.status)+' '+x.n+'건</p>').join(''))})}

let kakaoConsultAgent='';
async function openKakaoConsultRequest(agent=''){await act(async()=>{
 const brands=has('extra_agent')?(await api('/api/agents/list')).agents.filter(x=>x.available&&!x.archived):[];
 const r=await api('/api/kakao-consultation/request?agent='+enc(agent)),v=r.request||{};
 kakaoConsultAgent=agent;
 modal('카카오 상담톡 연결 신청',brandSelect('consult-kakao-brand',brands,agent,'openKakaoConsultRequest(this.value)')+
 '<p class="muted">현재 연결 신청 정보만 저장합니다. 실제 API 연결, 비용 결제, 메시지 발송은 아직 지원하지 않습니다. 비밀번호와 API 키는 입력하지 마세요.</p>'+
 label('계약 방식',select('consult-kakao-mode',[['own_contract','기존 딜러 계약 사용 · 공급료 직접 납부'],['managed_prepaid','CS AI 공급 계약 사용 · 선불 방식 예정']],v.mode||'own_contract').replace('<select','<select onchange="syncKakaoConsultMode()"'))+
 label('카카오 비즈니스 채널 ID 또는 이름',input('consult-kakao-channel',v.channel_ref||''))+
 '<div id="consult-kakao-own">'+label('계약한 공식 딜러사',input('consult-kakao-dealer',v.dealer||''))+'</div>'+
 '<div id="consult-kakao-managed">'+label('희망 월 사용 예산 (원)','<input id="consult-kakao-budget" type="number" min="1000" max="10000000" value="'+e(String(v.budget_krw||10000))+'">')+'<p class="muted">예산 희망치이며 실제 충전·과금 한도가 아닙니다. 공급 단가와 차감 방식이 확정되면 별도 고지합니다.</p></div>'+
 '<label><input type="checkbox" id="consult-kakao-confirm"> 연결 신청이며 계약 및 결제가 완료되지 않음을 확인했습니다.</label>'+
 actionGroup({keepSize:true},btn('신청 정보 저장','saveKakaoConsultRequest()','primary'),(r.request?btn('신청 취소','cancelKakaoConsultRequest()'):''))+
 '<p class="muted">상태: '+(r.request?'계약 및 연동 검토 대기':'미신청')+'</p>');
 syncKakaoConsultMode();
})}
function syncKakaoConsultMode(){const own=val('consult-kakao-mode')==='own_contract';$('#consult-kakao-own').hidden=!own;$('#consult-kakao-managed').hidden=own;}
async function saveKakaoConsultRequest(){await act(async()=>{
 const mode=val('consult-kakao-mode'),own=mode==='own_contract';
 if(!$('#consult-kakao-confirm')?.checked)throw Error('신청 내용을 확인하세요.');
 const agent=kakaoConsultAgent;
 await api('/api/kakao-consultation/request',{agent,mode,dealer:own?val('consult-kakao-dealer').trim():'',channel_ref:val('consult-kakao-channel').trim(),budget_krw:own?0:Number(val('consult-kakao-budget')),confirmed:true});
 toast('연동 신청 정보를 저장했습니다.');await openKakaoConsultRequest(agent);
})}
async function cancelKakaoConsultRequest(){if(!confirm('상담톡 연동 신청을 취소할까요?'))return;await act(async()=>{const agent=kakaoConsultAgent;await api('/api/kakao-consultation/request?agent='+enc(agent),undefined,'DELETE');await openKakaoConsultRequest(agent)})}


let profileEditorAgent='',profileEditorInitial='',profileEditorHasPhoto=false;
let profileEditorRemove=false,profileEditorBusy=false,profileEditorOpening=false;
function profileEditorPayload(){
 return {
  agent:profileEditorAgent,show_at_start:checked('profile-start'),notice_mode:val('profile-notice-mode'),
  manual_notice:val('profile-manual-notice'),title:val('profile-title'),message:val('profile-message'),
  contacts:[...$('#profile-editor-contacts').children].map(el=>({
   kind:el.querySelector('.profile-contact-kind').value,name:el.querySelector('.profile-contact-name').value.trim(),
   value:el.querySelector('.profile-contact-value').value.trim(),
  })).filter(c=>c.name||c.value),
  links:[...$('#profile-editor-links').children].map(el=>({
   name:el.querySelector('.profile-link-name').value.trim(),url:el.querySelector('.profile-link-url').value.trim(),
  })).filter(l=>l.name||l.url),
 };
}
function profileEditorDirty(){
 return !!$('#profile-editor-links')&&(JSON.stringify(profileEditorPayload())!==profileEditorInitial||
  !!$('#profile-photo-file').files.length||(profileEditorRemove&&profileEditorHasPhoto));
}
function preserveProfileBeforeUnload(event){
 if(!profileEditorBusy&&!profileEditorDirty())return;
 event.preventDefault();
 event.returnValue='';
}
function endProfileEditor(){window.removeEventListener('beforeunload',preserveProfileBeforeUnload);}
function profileLinkRow(name='',url=''){const div=document.createElement('div');div.className='profile-edit-link';div.innerHTML='<input type="text" maxlength="80" class="profile-link-name" placeholder="링크 이름" aria-label="링크 이름"><input type="url" maxlength="1000" class="profile-link-url" placeholder="https://..." aria-label="링크 주소"><button type="button" onclick="this.parentElement.remove()" aria-label="링크 삭제">삭제</button>';div.querySelector('.profile-link-name').value=name;div.querySelector('.profile-link-url').value=url;return div}
function profileContactRow(c={kind:'phone',name:'',value:''}){const div=document.createElement('div');div.className='profile-edit-contact';div.innerHTML='<select class="profile-contact-kind" aria-label="연락처 종류"><option value="phone">전화번호</option><option value="email">이메일</option><option value="other">기타 연락처</option></select><input type="text" class="profile-contact-name" maxlength="60" placeholder="이름 (예: 고객센터)" aria-label="연락처 이름"><input type="text" class="profile-contact-value" maxlength="200" placeholder="연락처" aria-label="연락처 내용"><button type="button" onclick="this.parentElement.remove()" aria-label="연락처 삭제">삭제</button>';div.querySelector('.profile-contact-kind').value=c.kind;div.querySelector('.profile-contact-name').value=c.name;div.querySelector('.profile-contact-value').value=c.value;return div}
function addProfileContact(){const list=$('#profile-editor-contacts');if(!list)return;if(list.children.length>=10){toast('연락처는 최대 10개입니다.');return}list.append(profileContactRow())}
function addProfileLink(){const list=$('#profile-editor-links');if(!list)return;if(list.children.length>=10){toast('링크는 최대 10개입니다.');return}list.append(profileLinkRow())}
function removeProfilePhoto(){profileEditorRemove=true;const f=$('#profile-photo-file');if(f){f.value='';fileUploadSelected(f);}const img=$('#profile-current-photo');if(img)img.innerHTML='<p class="muted">저장하면 사진이 삭제됩니다.</p>'}
async function openProfileEditor(agent=''){
 if(profileEditorOpening||$('#profile-editor-links'))return;
 profileEditorOpening=true;
 try{await act(async()=>{
 const p=await api('/api/chat-profile?agent='+enc(agent));
 const overlay=modal('채팅창 프로필 설정','<p class="muted">고객에게 공개되는 업체 소개입니다. 전화번호·이메일은 고객이 누르면 기기의 전화·메일 앱을 엽니다. 웹 내부 음성·영상 통화는 아직 제공하지 않습니다.</p><label><input class="check" type="checkbox" id="profile-start" '+(p.show_at_start?'checked':'')+'> 채팅 시작 시 프로필 자동 표시</label><p class="muted">끄면 자동 표시되지 않으며, 등록된 프로필은 채팅 상단 프로필 버튼으로 확인할 수 있습니다.</p>'+label('공지사항 표시 방식',select('profile-notice-mode',[['manual','직접 작성한 공지'],['profile','프로필을 공지로 표시'],['both','직접 작성 공지와 프로필 모두'],['off','공지 영역 숨기기']],p.notice_mode||'manual'))+label('직접 작성 공지',ta('profile-manual-notice',p.manual_notice||''))+'<p class="muted">공지 영역의 표시 방식과 채팅 시작 시 프로필 표시는 각각 설정됩니다.</p>'+label('프로필 제목 (선택)',input('profile-title',p.title))+label('소개 및 추가 안내 문구',ta('profile-message',p.message))+'<div class="profile-edit-photo"><div id="profile-current-photo">'+(p.photo?'<img class="chat-profile-photo" alt="현재 프로필 사진" src="'+e(p.photo)+'">':'<p class="muted">등록된 사진 없음</p>')+'</div>'+fileUpload('profile-photo-file',{accept:'image/png,image/jpeg,image/webp',buttonText:'이미지 선택',description:'권장 1200 × 900px (4:3) · PNG/JPG/WebP · 5MB 이하 · 자동 최적화',onChange:'previewProfilePhoto(this)'})+btn('사진 제거','removeProfilePhoto()','secondary ui-sm')+'</div><h3>전화번호·이메일·기타 연락처</h3><div id="profile-editor-contacts"></div>'+btn('연락처 추가','addProfileContact()')+'<h3>홈페이지·SNS·기타 링크</h3><div id="profile-editor-links"></div>'+btn('링크 추가','addProfileLink()')+'<p class="muted">최대 10개, HTTPS 링크만 가능합니다. 비공개 정보는 등록하지 마세요.</p>',{
  className:'profile-editor-modal',
  dismissOnBackdrop:false,
  canClose:()=>!profileEditorBusy&&(!profileEditorDirty()||confirm('저장하지 않은 변경사항을 버리고 닫을까요?')),
  onClose:endProfileEditor,
 });
 if(!overlay)return;
 const panel=overlay.querySelector('.ui-modal-panel'),heading=panel.querySelector('h2'),footer=panel.querySelector('.ui-modal-footer');
 const content=document.createElement('div');content.className='profile-editor-body';while(heading.nextSibling&&heading.nextSibling!==footer)content.append(heading.nextSibling);panel.insertBefore(content,footer);
 footer.insertAdjacentHTML('afterbegin','<p id="profile-save-error" role="alert" hidden></p>'+btn('프로필 저장','saveChatProfile()','primary'));
 profileEditorAgent=agent;profileEditorHasPhoto=!!p.photo;profileEditorRemove=false;
 for(const l of p.links||[])$('#profile-editor-links').append(profileLinkRow(l.name,l.url));
 for(const c of p.contacts||[])$('#profile-editor-contacts').append(profileContactRow(c));
 profileEditorInitial=JSON.stringify(profileEditorPayload());
 window.addEventListener('beforeunload',preserveProfileBeforeUnload);
 })}finally{profileEditorOpening=false;}
}
function previewProfilePhoto(field){const f=field.files[0];if(!f)return;if(f.size>5000000){field.value='';fileUploadSelected(field);toast('사진은 5MB 이하로 선택하세요.');return}profileEditorRemove=false;const r=new FileReader(),target=$('#profile-current-photo');r.onload=()=>{if(target?.isConnected&&field.files[0]===f){target.innerHTML='';const img=document.createElement('img');img.className='chat-profile-photo';img.alt='프로필 사진 미리보기';img.src=r.result;target.append(img)}};r.readAsDataURL(f)}
async function saveChatProfile(){
 if(profileEditorBusy)return;
 const modalNode=$('#profile-editor-links')?.closest('.modal');
 if(!modalNode)return;
 const errorNode=modalNode.querySelector('#profile-save-error');errorNode.hidden=true;errorNode.textContent='';
 try{
  const body=profileEditorPayload(),photo=$('#profile-photo-file').files[0];
  if(body.contacts.some(c=>!c.name||!c.value))throw Error('연락처 이름과 내용을 모두 입력하세요.');
  if(body.links.some(l=>!l.name||!l.url))throw Error('링크 이름과 주소를 모두 입력하세요.');
  const panel=modalNode.querySelector('.ui-modal-panel');
  const fields=[...modalNode.querySelectorAll('input,select,textarea,button')].filter(field=>!field.disabled);
  profileEditorBusy=true;panel.setAttribute('aria-busy','true');
  fields.forEach(field=>field.disabled=true);
  try{
   if(photo){
    if(photo.size>5000000)throw Error('사진은 5MB 이하입니다.');
    body.photo=await new Promise((resolve,reject)=>{
     const reader=new FileReader();
     reader.onload=()=>resolve(String(reader.result).split(',')[1]);
     reader.onerror=()=>reject(Error('사진을 읽을 수 없습니다.'));
     reader.readAsDataURL(photo);
    });
   }else if(profileEditorRemove)body.photo='';
   await api('/api/chat-profile',body);
   const saved=await api('/api/chat-profile?agent='+enc(body.agent));
   const matches=body.title.trim()===saved.title&&body.message.trim()===saved.message&&body.manual_notice.trim()===saved.manual_notice&&body.show_at_start===saved.show_at_start&&body.notice_mode===saved.notice_mode&&JSON.stringify(body.contacts)===JSON.stringify(saved.contacts)&&JSON.stringify(body.links)===JSON.stringify(saved.links)&&(!photo||!!saved.photo)&&(!profileEditorRemove||!!photo||!saved.photo);
   if(!matches)throw Error('저장 결과를 확인하지 못했습니다. 입력 내용은 유지됩니다. 다시 저장해 주세요.');
   profileEditorInitial=JSON.stringify(profileEditorPayload());
   modalNode.remove();endProfileEditor();
   toast('프로필을 저장했습니다.');
   await refresh();await render();
  }finally{
   profileEditorBusy=false;panel.removeAttribute('aria-busy');
   fields.forEach(field=>field.disabled=false);
  }
 }catch(err){if(modalNode.isConnected){errorNode.textContent=err.message||'프로필 저장 실패';errorNode.hidden=false;}else toast(err.message||'프로필 화면 갱신 실패');}
}

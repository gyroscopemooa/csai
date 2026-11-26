'use strict';
// Reference: user supplied DesignBookmark Letter Limit / Plan Switch / Storage Meter.
// Native controls remain authoritative, no autoplay, fake payment state or input rewriting.
(()=>{
 const reduce=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 const mounted=new WeakMap();
 function sync(field){
  if(!field.isConnected)return;
  const cap=field.maxLength;if(cap<=0)return;
  let counter=mounted.get(field);
  if(!counter){
   counter=document.createElement('span');counter.className='real-letter-meter';
   const id='limit-'+field.id;counter.id=id;
   const previous=field.getAttribute('aria-describedby')||'';
   field.setAttribute('aria-describedby',(previous+' '+id).trim());
   field.insertAdjacentElement('afterend',counter);mounted.set(field,counter);
  }
  const n=field.value.length,remaining=Math.max(0,cap-n),old=counter.dataset.remaining;
  counter.dataset.remaining=String(remaining);counter.dataset.level=remaining===0?'full':remaining<=Math.ceil(cap*.1)?'near':'normal';
  counter.textContent=n.toLocaleString('ko-KR')+' / '+cap.toLocaleString('ko-KR')+'자';
  if(old!==undefined&&old!==String(remaining)&&!reduce()&&counter.animate)counter.animate([{opacity:.7,transform:'translateY(2px)'},{opacity:1,transform:'none'}],{duration:170});
 }
 function scan(root=document){
  root.querySelectorAll('textarea[maxlength][id]').forEach(sync);
 }
 let queued=false;
 function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;scan()})}
 document.addEventListener('input',event=>{if(event.target.matches('textarea[maxlength][id]'))sync(event.target)});
 document.addEventListener('compositionend',event=>{if(event.target.matches('textarea[maxlength][id]'))sync(event.target)});
 document.addEventListener('click',schedule);document.addEventListener('submit',schedule);
 const root=document.getElementById('app');
 // Ignore counter's own mutations; observe only element insertions/removals.
 new MutationObserver(records=>{if(records.some(r=>[...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&!n.classList.contains('real-letter-meter'))))schedule()}).observe(root,{childList:true,subtree:true});
 scan();
})();

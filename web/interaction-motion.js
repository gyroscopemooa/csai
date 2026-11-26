'use strict';
// A small decorative response to an explicit confirmation click. The original
// button action remains responsible for validating and saving the change.
document.addEventListener('click',event=>{
  const button=event.target.closest('button');
  if(!button||button.disabled||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const label=(button.textContent||'').trim();
  if(!/(승인|수락|결제|동의|확인하고|확정)/.test(label))return;
  const box=button.getBoundingClientRect();
  if(!box.width||!box.height)return;
  const bite=document.createElement('span');
  bite.className='cookie-bite';
  bite.style.cssText=`left:${box.right-20}px;top:${box.top+box.height/2-8}px`;
  document.body.append(bite);
  for(let i=0;i<5;i++){
    const crumb=document.createElement('i');
    crumb.style.setProperty('--x',`${Math.round((Math.random()-.5)*42)}px`);
    crumb.style.setProperty('--y',`${Math.round(-12-Math.random()*36)}px`);
    crumb.style.animationDelay=`${i*25}ms`;
    bite.append(crumb);
  }
  setTimeout(()=>bite.remove(),650);
},true);

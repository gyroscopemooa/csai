'use strict';
// Adapted from user-supplied DesignBookmark Date Range and Star Rating.
// Original spring constants, four integration substeps, fade curves and staggering.
const DBMotion=(()=>{
 const clamp=(x,a,b)=>Math.max(a,Math.min(b,x)),reduce=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
 const S=(x,k,c)=>({x,v:0,t:x,k,c});
 function step(s,dt){if(reduce()){s.x=s.t;s.v=0;return;}s.v+=(-s.k*(s.x-s.t)-s.c*s.v)*dt;s.x+=s.v*dt;}
 const moving=s=>Math.abs(s.x-s.t)>.0005||Math.abs(s.v)>.005;
 function engine(root,frame,paint,active){
  let raf=0,last=0;
  function tick(now){raf=0;if(!root.isConnected)return;const dt=Math.min((now-last)/1000,1/30);last=now;for(let i=0;i<4;i++)frame(dt/4);paint();if(active())raf=requestAnimationFrame(tick);}
  return ()=>{if(!raf&&root.isConnected){last=performance.now();raf=requestAnimationFrame(tick);}};
 }
 const starPath='M12 3.2l2.6 5.5 6 .8-4.4 4.1 1.1 5.9L12 16.6l-5.3 2.9 1.1-5.9-4.4-4.1 6-.8z';
 const labels=['별점을 선택하세요','매우 불만족','불만족','보통','만족','매우 만족'];
 const ratings=new WeakMap();
 function mountRating(group){
  if(ratings.has(group))return ratings.get(group);
  const row=group.querySelector('.db-stars'),col=group.querySelector('.db-rating-col');
  const stars=[...row.querySelectorAll('label')].map(el=>({el,input:el.querySelector('input'),svg:el.querySelector('svg'),path:el.querySelector('path'),f:S(0,300,24),p:S(1,520,13),lit:false,due:0,pending:false}));
  const word=S(0,260,22);let clock=0,rating=0;
  const wake=engine(group,dt=>{clock+=dt;step(word,dt);for(const s of stars){if(s.pending&&clock>=s.due){s.pending=false;s.f.t=s.lit?1:0;if(s.lit&&!reduce()){s.p.x=.7;s.p.v=7;}}step(s.f,dt);step(s.p,dt);}},()=>{
   for(const s of stars){const f=clamp(s.f.x,0,1);s.path.style.fill='color-mix(in srgb, var(--db-star-yellow) '+(f*100).toFixed(1)+'%, var(--db-star-empty))';s.svg.style.transform='scale('+s.p.x.toFixed(4)+')';}
   col.style.transform='translateY('+(-20*word.x).toFixed(2)+'px)';
  },()=>moving(word)||stars.some(s=>s.pending||moving(s.f)||moving(s.p)));
  function light(n){word.t=n;stars.forEach((s,i)=>{const on=i<n;if(on===s.lit)return;s.lit=on;s.due=clock+(on&&!reduce()?i*.05:0);s.pending=true;});wake();}
  function select(n){rating=n;stars.forEach((s,i)=>s.input.checked=i===n-1);group.querySelector('.db-rating-status').textContent=n?n+'점 · '+labels[n]:labels[0];light(n);}
  stars.forEach((s,i)=>{s.el.addEventListener('pointerenter',ev=>{if(ev.pointerType==='mouse')light(i+1);});s.input.addEventListener('change',()=>select(i+1));});
  row.addEventListener('pointerleave',()=>light(rating));
  const api={select};ratings.set(group,api);return api;
 }
 const mountRatings=root=>root.querySelectorAll('.db-rating').forEach(mountRating);
 function dateNum(s){const [y,m,d]=s.split('-').map(Number);return Math.round(Date.UTC(y,m-1,d)/864e5);}
 function dateStr(n){return new Date(n*864e5).toISOString().slice(0,10);}
 function monthInfo(y,m){const d=new Date(Date.UTC(y,m,1)),year=d.getUTCFullYear(),month=d.getUTCMonth(),first=dateNum(year+'-'+(month+1)+'-1'),len=new Date(Date.UTC(year,month+1,0)).getUTCDate(),offset=d.getUTCDay();return {year,month,first,len,offset,rows:Math.ceil((offset+len)/7)};}
 const short=n=>{const d=new Date(n*864e5);return (d.getUTCMonth()+1)+'월 '+d.getUTCDate()+'일';};
 function calendar(root,options,onChange){
  const view=root.querySelector('.db-calendar-view'),title=root.querySelector('.db-calendar-title'),sum=root.querySelector('.db-calendar-sum'),chip=root.querySelector('.db-calendar-chip');
  const CH=40,R=18,FADE=.19,PREVIEW=.5;let clock=0,drag=null,hover=null;
  let M=monthInfo(options.year,options.month),a=options.start?dateNum(options.start):null,b=options.end?dateNum(options.end):null,anchor=!!options.anchor;
  if(!options.range){a=dateNum(options.day);b=a;anchor=false;}
  const live=[],bands=[],dots=[],H=S(M.rows*CH,260,24),CHIP={from:0,to:0,t0:-1000};
  const F=(v=0)=>({from:v,to:v,t0:-1000});
  const val=f=>{const u=reduce()?1:clamp((clock-f.t0)/FADE,0,1);return f.from+(f.to-f.from)*(f.to>=f.from?1-(1-u)**3:u**3);};
  const fade=(f,to)=>{if(f.to!==to){f.from=val(f);f.to=to;f.t0=clock;}};
  const snap=(f,v)=>{f.from=f.to=v;f.t0=-1000;};
  const unfinished=f=>!reduce()&&clock-f.t0<FADE;
  function roller(el){
   const a=document.createElement('span'),b=document.createElement('span');el.replaceChildren(a,b);let cur=a,old=b,dir=1;const p=S(0,420,32);
   return {put(t){cur.textContent=t;old.textContent='';p.x=p.t=p.v=0;},set(t,d=1){if(cur.textContent===t)return;if(p.x>.02&&cur.textContent){cur.textContent=t;return;}dir=d;old.textContent=t;[cur,old]=[old,cur];p.x=1;p.t=0;p.v=0;},step(dt){step(p,dt);},active:()=>moving(p),paint(){const q=clamp(p.x,0,1);cur.style.transform='translateY('+q*100*dir+'%)';cur.style.opacity=1-q;cur.style.filter='blur('+q*2+'px)';old.style.transform='translateY('+(q-1)*100*dir+'%)';old.style.opacity=q;old.style.filter='blur('+(1-q)*2+'px)';old.style.visibility=q<.002?'hidden':'visible';}};
  }
  const tr=roller(title),sr=roller(sum),cr=roller(chip);
  const band=()=>bands.find(x=>x.live);
  function killBand(){const x=band();if(x){x.live=false;fade(x.f,0);}}
  function setBand(lo,hi,preview=false){if(lo===hi){killBand();return;}let x=band();if(!x){x={a:lo,b:hi,f:F(),live:true};bands.push(x);}x.a=lo;x.b=hi;if(preview)snap(x.f,PREVIEW);else fade(x.f,1);}
  function setDot(role,d){const old=dots.find(x=>x.role===role);if(old&&old.d===d){fade(old.f,1);return;}if(old){old.role=null;fade(old.f,0);}if(d===null)return;let x=dots.find(x=>x.role===null&&x.d===d);if(!x){x={d,f:F(),role};dots.push(x);}x.role=role;fade(x.f,1);}
  function marks(){if(a===null){killBand();setDot('a',null);setDot('b',null);}else{setDot('a',a);setDot('b',b!==a?b:null);if(b!==null&&b!==a)setBand(a,b);else killBand();}}
  function text(initial=false,dir=1){const set=(r,v)=>initial?r.put(v):r.set(v,dir);set(tr,M.year+'년 '+(M.month+1)+'월');set(sr,a===null?'시작일 선택':anchor?short(a)+' · 종료일 선택':b!==null&&a!==b?short(a)+' – '+short(b):short(a));if(options.range&&b!==null&&!anchor){const t=(b-a+1)+'일';if(val(CHIP)<.02)cr.put(t);else cr.set(t);fade(CHIP,1);}else fade(CHIP,0);}
  function build(m){const el=document.createElement('div');el.className='db-calendar-month';const bl=document.createElement('div');bl.className='db-calendar-layer';el.append(bl);const cells=[];
   for(let k=0;k<m.len;k++){const d=m.first+k,cell=document.createElement('button'),count=Number(options.counts[dateStr(d)]||0);cell.type='button';cell.className='db-calendar-day';cell.dataset.date=dateStr(d);cell.setAttribute('aria-label',dateStr(d)+' · 일정 '+count+'건');cell.textContent=k+1;if(count){const c=document.createElement('small');c.textContent=count+'건';cell.append(c);}el.append(cell);cells.push({el:cell,d,col:(m.offset+k)%7,row:Math.floor((m.offset+k)/7),count});}
   const dl=document.createElement('div');dl.className='db-calendar-layer';el.append(dl);view.append(el);return {m,el,bl,dl,cells,X:S(0,420,41),A:S(1,420,41),bandEls:[],dotEls:[],leaving:false};
  }
  let active=build(M);live.push(active);
  function place(o,w){o.cells.forEach(c=>{c.el.style.width=w+'px';c.el.style.transform='translate('+c.col*w+'px,'+c.row*CH+'px)';c.el.setAttribute('aria-pressed',String(a!==null&&c.d>=a&&c.d<=(b??a)));c.el.classList.toggle('in-range',a!==null&&b!==null&&c.d>=a&&c.d<=b);});}
  function paint(){const w=view.clientWidth/7,rowLen=w*7;view.style.height=H.x.toFixed(2)+'px';tr.paint();sr.paint();cr.paint();const cp=val(CHIP);chip.style.opacity=cp;chip.style.transform='scale('+(.9+.1*cp)+')';if(!w)return;
   for(const o of live){place(o,w);o.el.style.transform='translateX('+o.X.x.toFixed(2)+'px)';o.el.style.opacity=clamp(o.A.x,0,1);const track=d=>(o.m.offset+d-o.m.first)*w+w/2;
    bands.forEach((x,i)=>{const els=o.bandEls[i]||(o.bandEls[i]=Array.from({length:o.m.rows},()=>{const el=document.createElement('span');el.className='db-calendar-band';o.bl.append(el);return el;}));const al=val(x.f),lo0=track(x.a)-R,hi0=track(x.b)+R,lo=Math.max(lo0,o.m.offset*w),hi=Math.min(hi0,(o.m.offset+o.m.len)*w);els.forEach((el,r)=>{const l=Math.max(lo,r*rowLen+2),rr=Math.min(hi,(r+1)*rowLen-2);el.style.opacity=rr-l<1?0:al;el.style.width=Math.max(0,rr-l)+'px';el.style.transform='translate('+(l-r*rowLen)+'px,'+(r*CH+2)+'px) scaleY('+(.9+.1*clamp(al/PREVIEW,0,1))+')';el.style.borderRadius=(l===lo0?R:8)+'px '+(rr===hi0?R:8)+'px '+(rr===hi0?R:8)+'px '+(l===lo0?R:8)+'px';});});
    for(let i=bands.length;i<o.bandEls.length;i++)o.bandEls[i].forEach(el=>el.style.opacity=0);
    dots.forEach((x,i)=>{const el=o.dotEls[i]||(o.dotEls[i]=document.createElement('span'));if(!el.isConnected){el.className='db-calendar-dot';o.dl.append(el);}const p=val(x.f),k=x.d-o.m.first;if(p<.002||k<0||k>=o.m.len){el.style.visibility='hidden';return;}const pos=track(x.d),r=Math.floor(pos/rowLen);const count=Number(options.counts[dateStr(x.d)]||0);const label=String(k+1)+(count?' · '+count+'건':'');if(el.dataset.label!==label){el.dataset.label=label;el.replaceChildren(document.createTextNode(String(k+1)));if(count){const small=document.createElement('small');small.textContent=count+'건';el.append(small);}}el.style.visibility='visible';el.style.transform='translate('+(pos-r*rowLen)+'px,'+(r*CH+CH/2)+'px)';el.style.clipPath='circle('+(R*p)+'px at 50% 50%)';});
    for(let i=dots.length;i<o.dotEls.length;i++)o.dotEls[i].style.visibility='hidden';
   }
  }
  const wake=engine(root,dt=>{clock+=dt;step(H,dt);tr.step(dt);sr.step(dt);cr.step(dt);for(const o of live){step(o.X,dt);step(o.A,dt);}for(let i=live.length-1;i>=0;i--)if(live[i].leaving&&!moving(live[i].A)&&!moving(live[i].X)){live[i].el.remove();live.splice(i,1);}for(let i=bands.length-1;i>=0;i--)if(!bands[i].live&&!unfinished(bands[i].f))bands.splice(i,1);for(let i=dots.length-1;i>=0;i--)if(!dots[i].role&&!unfinished(dots[i].f))dots.splice(i,1);},paint,()=>moving(H)||tr.active()||sr.active()||cr.active()||unfinished(CHIP)||live.some(o=>moving(o.X)||moving(o.A))||bands.some(x=>unfinished(x.f))||dots.some(x=>unfinished(x.f)));
  function emit(){onChange({year:M.year,month:M.month,start:a===null?null:dateStr(a),end:b===null?null:dateStr(b),anchor,day:a===null?dateStr(M.first):dateStr(b??a)});}
  function update(){marks();text();paint();wake();emit();}
  function pick(d){if(!options.range){a=b=d;anchor=false;}else if(a===d){a=b=null;anchor=false;}else if(anchor){const lo=Math.min(a,d);b=Math.max(a,d);a=lo;anchor=false;}else{a=d;b=null;anchor=true;}hover=null;update();}
  function preview(d){if(!options.range||!anchor||a===null)return;hover=d;if(d===null||d===a){killBand();}else setBand(Math.min(a,d),Math.max(a,d),true);paint();wake();}
  function goMonth(y,m){const next=monthInfo(y,m),dir=next.first>M.first?1:-1;if(next.first===M.first)return;const old=active,W=view.clientWidth;old.X.t=-dir*W;old.A.t=0;old.leaving=true;old.el.inert=true;M=next;if(!options.range){a=b=M.first;marks();}active=build(M);live.push(active);active.X.x=old.X.x+dir*W;active.A.x=.4;H.t=M.rows*CH;text(false,dir);paint();wake();emit();}
  function dayAt(ev){const r=view.getBoundingClientRect(),w=view.clientWidth/7,col=Math.floor((ev.clientX-r.left-active.X.x)/w),row=Math.floor((ev.clientY-r.top)/CH);if(col<0||col>6||row<0)return null;return active.cells.find(c=>c.row===row&&c.col===col)?.d??null;}
  view.addEventListener('pointerdown',ev=>{if(ev.button!==0||!ev.isPrimary)return;const d=dayAt(ev);if(d===null)return;drag={id:ev.pointerId,first:d,last:d,x:ev.clientX,y:ev.clientY,moved:false};view.setPointerCapture(ev.pointerId);});
  view.addEventListener('pointermove',ev=>{const d=dayAt(ev);if(drag&&drag.id===ev.pointerId){if(Math.hypot(ev.clientX-drag.x,ev.clientY-drag.y)>5)drag.moved=true;if(drag.moved&&options.range){if(!anchor&&a!==drag.first){a=drag.first;b=null;anchor=true;update();}drag.last=d;if(d!==null)preview(d);}}else if(ev.pointerType==='mouse')preview(d);});
  view.addEventListener('pointerup',ev=>{if(!drag||drag.id!==ev.pointerId)return;const d=dayAt(ev),p=drag;drag=null;if(p.moved&&options.range&&d!==null&&d!==p.first){a=Math.min(p.first,d);b=Math.max(p.first,d);anchor=false;update();}else if(!p.moved)pick(p.first);else preview(null);});
  view.addEventListener('pointercancel',()=>{drag=null;preview(null);});view.addEventListener('pointerleave',()=>{if(!drag)preview(null);});
  view.addEventListener('click',ev=>{if(ev.detail===0){const cell=ev.target.closest('[data-date]');if(cell)pick(dateNum(cell.dataset.date));}});
  root.querySelector('[data-prev]').onclick=()=>goMonth(M.year,M.month-1);root.querySelector('[data-next]').onclick=()=>goMonth(M.year,M.month+1);
  marks();text(true);paint();wake();
  const observer=new ResizeObserver(()=>{if(root.isConnected){paint();wake();}else observer.disconnect();});observer.observe(view);
  return {setRange(start,end){a=dateNum(start);b=dateNum(end);anchor=false;const d=new Date(a*864e5);goMonth(d.getUTCFullYear(),d.getUTCMonth());update();},destroy(){observer.disconnect();}};
 }
 return {mountRatings,mountRating,calendar,starPath,labels,S,step,monthInfo,dateNum,dateStr};
})();

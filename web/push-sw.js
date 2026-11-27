'use strict';
const routes=new Set(['inbox','calendar','alerts']);
self.addEventListener('push',event=>{
  event.waitUntil((async()=>{
    let p={};try{p=event.data?.json()||{}}catch{}
    const route=routes.has(p.route)?p.route:'alerts';
    const title=typeof p.title==='string'?p.title.slice(0,100):'CS AI 알림';
    const id=typeof p.event==='string'&&/^[A-Za-z0-9_-]{1,80}$/.test(p.event)?p.event:'general';
    const silent=p.silent===true;
    await self.registration.showNotification(title,{body:'관리자 화면에서 확인하세요.',tag:'csai-'+id,silent,data:{path:'/#'+route},...(silent?{}:{vibrate:p.kind==='handoff_urgent'?[200,100,200]:[120]})});
    const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    for(const c of windows){if(c.visibilityState==='visible'&&!silent)c.postMessage({type:'csai-push',kind:p.kind,event:id});}
  })());
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil((async()=>{
    const route=String(event.notification.data?.path||'').slice(2);
    const url=new URL('/#'+(routes.has(route)?route:'alerts'),self.location.origin).href;
    const clients=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    for(const c of clients){const u=new URL(c.url);if(u.origin===self.location.origin&&u.pathname==='/'){await c.navigate(url);return c.focus();}}
    return self.clients.openWindow(url);
  })());
});

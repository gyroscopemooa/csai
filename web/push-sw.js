'use strict';
self.addEventListener('push',event=>{
  event.waitUntil(self.registration.showNotification('CS AI 알림',{body:'새로운 업무 알림이 있습니다. 관리자 화면에서 확인하세요.',tag:'csai-work',data:{path:'/#alerts'}}));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil((async()=>{
    const url=new URL('/#alerts',self.location.origin).href;
    const clients=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    for(const c of clients){if(new URL(c.url).origin===self.location.origin){await c.navigate(url);return c.focus();}}
    return self.clients.openWindow(url);
  })());
});

/* Embed on a customer-owned HTTPS page; no credentials or access keys in browser code. */
(function(){
  'use strict';
  const script=document.currentScript;
  if(!script)return;
  const slug=script.dataset.slug||'';
  if(!/^[A-Za-z0-9_-]{3,100}$/.test(slug))return;
  const base=new URL(script.src,location.href).origin;
  if(!/^https:\/\//.test(base)&&!/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(base))return;
  function start(){
    const host=document.createElement('div');host.style.cssText='position:fixed;right:18px;bottom:18px;z-index:2147483000;font-family:system-ui,sans-serif;';
    const root=host.attachShadow({mode:'closed'});
    const style=document.createElement('style');style.textContent='button{border:0;border-radius:28px;padding:14px 20px;background:#3182f6;color:white;font:600 14px system-ui;cursor:pointer;box-shadow:0 3px 15px #0002}button:focus-visible{outline:3px solid #98bfff;outline-offset:2px}iframe{position:fixed;right:18px;bottom:80px;width:min(380px,calc(100vw - 36px));height:min(650px,calc(100dvh - 105px));border:1px solid #ddd;background:white;border-radius:18px;box-shadow:0 10px 45px #0003}iframe[hidden]{display:none}@media(max-width:480px){iframe{right:8px;bottom:76px;width:calc(100vw - 16px);height:calc(100dvh - 90px)}}';
    const button=document.createElement('button');button.type='button';button.textContent='상담하기';button.setAttribute('aria-expanded','false');
    const frame=document.createElement('iframe');frame.hidden=true;frame.title='고객 상담';frame.referrerPolicy='no-referrer';frame.loading='lazy';frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox');
    let loaded=false;
    button.addEventListener('click',()=>{const show=frame.hidden;if(show&&!loaded){frame.src=base+'/widget/'+encodeURIComponent(slug);loaded=true}frame.hidden=!show;button.textContent=show?'상담 닫기':'상담하기';button.setAttribute('aria-expanded',String(show));});
    root.append(style,frame,button);document.body.append(host);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();

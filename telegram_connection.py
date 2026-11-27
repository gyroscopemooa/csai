"""Explicit Telegram setup, no paid broadcast or automatic webhook takeover."""
import os,secrets
from fastapi import Depends
from app import app,ident,require,bounded,limit
from store import *
import channel_live as cl
import ops
from integrations import telegram_transport as tg

@app.get('/api/telegram')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);ops.work_scope(c,w,agent);r=cl.scoped_link(c,ws,'telegram',agent)
        return {'available':cl.telegram_enabled(),'saved':bool(r),'active':bool(r and cl.permitted_link(c,w,r)),'bot':r['partner'] if r else ''}

@app.post('/api/telegram/connect')
def connect(body:dict,agent:str='',ws=Depends(ident)):
    require(cl.telegram_enabled() and os.getenv('INTEGRATION_ENCRYPTION_KEY'),'서버 텔레그램 연결 준비 중',503)
    require(body.get('confirmed') is True,'웹훅 등록 동의 필요',422)
    token=bounded(body.get('token',''),200);limit('telegram-connect:'+ws,5,60)
    try:bot=tg.verify_bot(token);remote=tg.webhook_status(token)
    except tg.TelegramError:require(False,'텔레그램 봇 인증 실패',422)
    with db(True) as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'유료 상담 권한 필요',403)
        old=cl.scoped_link(c,ws,'telegram',agent)
        require(not old or old['partner']==bot,'기존 연결을 해제하세요.',409)
        main=one(c,"SELECT ws FROM channel_link WHERE channel='telegram' AND partner=? AND ws<>?",(bot,ws))
        other=one(c,"SELECT ws FROM channel_brand_link WHERE channel='telegram' AND partner=? AND (ws<>? OR agent<>?)",(bot,ws,agent))
        require(not main and not other and not (agent and cl.scoped_link(c,ws,'telegram','') and cl.scoped_link(c,ws,'telegram','')['partner']==bot),'다른 브랜드에 등록된 봇입니다.',409)
        secret=cl.unlock(old['secret']) if old else secrets.token_urlsafe(32)
        url=APP_URL+'/hooks/telegram/'+secret
        require(not remote or remote==url,'다른 웹훅이 사용 중입니다. 기존 서비스에서 먼저 해제하세요.',409)
        require(not old or not old['active'],'이미 연결되었습니다.',409)
        args=(cl.digest(secret),cl.lock_text(secret),cl.lock_text(token),bot,0)
        if agent:c.execute('INSERT INTO channel_brand_link VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(ws,agent,channel) DO UPDATE SET credential=excluded.credential,active=0',(ws,agent,'telegram',*args))
        else:c.execute('INSERT INTO channel_link VALUES(?,?,?,?,?,?,?) ON CONFLICT(ws,channel) DO UPDATE SET credential=excluded.credential,active=0',(ws,'telegram',*args))
    try:
        tg.register_webhook(token,url,cl.digest('telegram-header:'+secret),APP_URL)
        require(tg.webhook_status(token)==url,'웹훅 확인 실패',502)
    except tg.TelegramError:require(False,'웹훅 등록 미확인 · 다시 연결하세요.',502)
    with db(True) as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);r=cl.scoped_link(c,ws,'telegram',agent)
        require(r and r['secret_hash']==cl.digest(secret) and cl.unlock(r['credential'])==token,'연결 설정이 변경되었습니다.',409)
        if agent:c.execute("UPDATE channel_brand_link SET active=1 WHERE ws=? AND agent=? AND channel='telegram'",(ws,agent))
        else:c.execute("UPDATE channel_link SET active=1 WHERE ws=? AND channel='telegram'",(ws,))
    return {'ok':True,'bot':bot}

@app.post('/api/telegram/pause')
def pause(agent:str='',ws=Depends(ident)):
    with db(True) as c:
        ops.work_scope(c,getw(c,ws),agent);r=cl.scoped_link(c,ws,'telegram',agent)
        if not r:return {'ok':True}
        require(not one(c,"SELECT id FROM channel_job WHERE ws=? AND channel='telegram' AND status='running'",(ws,)) and not one(c,"SELECT id FROM channel_staff_outbox WHERE ws=? AND channel='telegram' AND status='running'",(ws,)),'발송 종료 후 중지하세요.',409)
        if agent:c.execute("UPDATE channel_brand_link SET active=0 WHERE ws=? AND agent=? AND channel='telegram'",(ws,agent))
        else:c.execute("UPDATE channel_link SET active=0 WHERE ws=? AND channel='telegram'",(ws,))
        c.execute("UPDATE channel_job SET status='cancelled',body='',updated=? WHERE ws=? AND channel='telegram' AND status='queued' AND COALESCE((SELECT s.agent FROM channel_job_scope s WHERE s.ws=channel_job.ws AND s.job=channel_job.id),'')=?",(now(),ws,agent))
        c.execute("UPDATE channel_staff_outbox SET status='failed',error='연결 중지',body='',updated=? WHERE ws=? AND channel='telegram' AND link_hash=? AND status='queued'",(now(),ws,r['secret_hash']))
    return {'ok':True}

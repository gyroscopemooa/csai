"""Shared app webhook, verified Instagram Login account, inbound text only.
No auto-subscription, app-review bypass, token retention, outbound sends or billing.
"""
import os,re,hmac,json,secrets
from fastapi import Depends,Request,Response
from app import app,ident,require,bounded,limit
from store import *
import channel_live as cl,ops
from integrations import instagram_transport as ig
from integrations.provider_formats import meta_in,meta_verify

def enabled():
    return cl.enabled() and os.getenv('ENABLE_INSTAGRAM_INBOX')=='1' and bool(os.getenv('META_APP_SECRET') and os.getenv('META_VERIFY_TOKEN') and os.getenv('INTEGRATION_ENCRYPTION_KEY')) and bool(re.fullmatch(r'v[0-9]{1,2}\.0',os.getenv('INSTAGRAM_GRAPH_VERSION','')))

def view(c,ws,a):
    link=cl.scoped_link(c,ws,'instagram',a)
    return {'available':enabled(),'connected':bool(link),'active':bool(link and link['active']),'account':link['partner'] if link else '', 'webhook':APP_URL+'/hooks/providers/instagram','mode':'receive_only'}

@app.get('/api/instagram')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:ops.work_scope(c,getw(c,ws),agent);return view(c,ws,agent)

@app.post('/api/instagram/connect')
def connect(body:dict,agent:str='',ws=Depends(ident)):
    require(enabled(),'Meta 앱 및 서버 설정 필요',503)
    require(body.get('confirmed') is True and body.get('subscribed') is True,'전문 계정과 앱의 메시지 권한·웹훅 구독을 확인하세요.',422)
    token=bounded(body.get('token',''),4096);limit('ig-connect:'+ws,5,60)
    with db() as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'상담 이용 권한 필요',403)
        require(not cl.scoped_link(c,ws,'instagram',agent),'기존 계정 연결을 먼저 해제하세요.',409)
    try:profile=ig.profile(token)
    except ig.InstagramError as e:require(False,str(e),422)
    account=profile['id']
    with db(True) as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'상담 이용 권한 필요',403)
        require(not cl.scoped_link(c,ws,'instagram',agent),'기존 계정 연결을 먼저 해제하세요.',409)
        require(not one(c,"SELECT ws FROM channel_link WHERE channel='instagram' AND partner=?",(account,)) and not one(c,"SELECT ws FROM channel_brand_link WHERE channel='instagram' AND partner=?",(account,)),'이미 연결된 Instagram 계정입니다.',409)
        # The access token is used only to prove account identity and never persisted.
        key=secrets.token_urlsafe(32);args=(cl.digest(key),cl.lock_text(key),'',account,1)
        if agent:c.execute('INSERT INTO channel_brand_link VALUES(?,?,?,?,?,?,?,?)',(ws,agent,'instagram',*args))
        else:c.execute('INSERT INTO channel_link VALUES(?,?,?,?,?,?,?)',(ws,'instagram',*args))
        return {**view(c,ws,agent),'username':profile['username']}

@app.post('/api/instagram/disconnect')
def disconnect(body:dict,agent:str='',ws=Depends(ident)):
    require(body.get('confirmed') is True,'연결 해제 확인 필요',422)
    with db(True) as c:
        ops.work_scope(c,getw(c,ws),agent)
        require(not one(c,"SELECT id FROM channel_job WHERE ws=? AND channel='instagram' AND status='running'",(ws,)),'상담 처리 완료 후 해제하세요.',409)
        if agent:c.execute("DELETE FROM channel_brand_link WHERE ws=? AND agent=? AND channel='instagram'",(ws,agent))
        else:c.execute("DELETE FROM channel_link WHERE ws=? AND channel='instagram'",(ws,))
        c.execute("UPDATE channel_job SET status='cancelled',body='',updated=? WHERE ws=? AND channel='instagram' AND status='queued' AND COALESCE((SELECT s.agent FROM channel_job_scope s WHERE s.ws=channel_job.ws AND s.job=channel_job.id),'')=?",(now(),ws,agent))
    return {'ok':True}

@app.get('/hooks/providers/instagram')
def challenge(req:Request):
    require(enabled(),'Instagram 연동 비활성화',404)
    p=req.query_params;expected=os.environ['META_VERIFY_TOKEN'];supplied=p.get('hub.verify_token','');ch=p.get('hub.challenge','')
    require(p.get('hub.mode')=='subscribe' and hmac.compare_digest(expected.encode(),supplied.encode()) and bool(re.fullmatch(r'[0-9]{1,80}',ch)),'웹훅 검증 실패',403)
    return Response(ch,media_type='text/plain')

@app.post('/hooks/providers/instagram')
async def webhook(req:Request):
    require(enabled(),'Instagram 연동 비활성화',404)
    raw=bytearray()
    async for part in req.stream():
        require(len(raw)+len(part)<=256000,'웹훅 용량 초과',413);raw.extend(part)
    raw=bytes(raw)
    require(meta_verify(os.environ['META_APP_SECRET'],raw,req.headers.get('X-Hub-Signature-256','')),'Meta 웹훅 서명 오류',403)
    try:payload=json.loads(raw)
    except (ValueError,TypeError):require(False,'웹훅 형식 오류',422)
    if not isinstance(payload,dict) or payload.get('object')!='instagram':return Response(status_code=200)
    entries=payload.get('entry');require(isinstance(entries,list) and len(entries)<=100,'웹훅 항목 한도 초과',422)
    accounts={str(x.get('id')) for x in entries if isinstance(x,dict) and re.fullmatch(r'[0-9]{1,32}',str(x.get('id')))}
    with db(True) as c:
        for account in accounts:
            r=one(c,"SELECT * FROM channel_brand_link WHERE channel='instagram' AND partner=? AND active=1",(account,))
            if not r:
                base=one(c,"SELECT * FROM channel_link WHERE channel='instagram' AND partner=? AND active=1",(account,))
                r={**base,'agent':''} if base else None
            if not r or not cl.permitted_link(c,getw(c,r['ws']),r):continue
            ws,a=r['ws'],r['agent'];limit('ig-hook:'+ws,120,60)
            events=meta_in(payload,'instagram',account)
            require(len(events)<=100,'웹훅 이벤트 한도 초과',422)
            for m in events:
                # Account/event IDs remain stable across reconnects in the same workspace.
                event=cl.digest(account+':'+m.event_id)
                if one(c,'SELECT id FROM channel_job WHERE ws=? AND channel=? AND event_key=?',(ws,'instagram',event)):continue
                i=uid();c.execute('INSERT INTO channel_job VALUES(?,?,?,?,?,?,?,?,?)',(i,ws,'instagram',event,cl.lock_text(dump({'user':m.user,'text':m.text,'target':'','link_hash':r['secret_hash'],'partner':account})),'queued','',now(),now()))
                c.execute('INSERT INTO channel_job_scope VALUES(?,?,?)',(ws,i,a))
    return Response(status_code=200)

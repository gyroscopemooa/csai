"""Bring-your-own LINE official account. Verify signed callback before activation."""
import os,secrets,json,re
from fastapi import Depends,Request,Response
from app import app,ident,require,bounded,limit
from store import *
import channel_live as cl,ops
from integrations import line_transport as lt
from integrations.provider_formats import line_verify,line_in

def enabled():return cl.enabled() and os.getenv('ENABLE_LINE_CHANNEL')=='1' and bool(os.getenv('INTEGRATION_ENCRYPTION_KEY'))
def reply_enabled():return enabled() and os.getenv('ENABLE_LINE_REPLY')=='1'
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS line_verification(ws TEXT NOT NULL,agent TEXT NOT NULL,link_hash TEXT NOT NULL,verified INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        """)
init()
def raw_link(c,key):
    r=one(c,"SELECT * FROM channel_brand_link WHERE channel='line' AND secret_hash=?",(key,))
    if r:return r
    r=one(c,"SELECT * FROM channel_link WHERE channel='line' AND secret_hash=?",(key,))
    return {**r,'agent':''} if r else None
def view(c,ws,a):
    r=cl.scoped_link(c,ws,'line',a)
    proof=one(c,'SELECT verified FROM line_verification WHERE ws=? AND agent=? AND link_hash=?',(ws,a,r['secret_hash'])) if r else None
    return {'available':enabled(),'saved':bool(r),'active':bool(r and r['active']),'verified':bool(proof),'reply_available':reply_enabled(),'bot':r['partner'] if r else '', 'webhook':APP_URL+'/hooks/providers/line/'+cl.unlock(r['secret']) if r else ''}

@app.get('/api/line')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:ops.work_scope(c,getw(c,ws),agent);return view(c,ws,agent)

@app.post('/api/line/connect')
def connect(body:dict,agent:str='',ws=Depends(ident)):
    require(enabled(),'LINE 서버 연동 비활성화',503)
    require(body.get('confirmed') is True,'LINE 공식 계정 연결 동의 필요',422)
    token=bounded(body.get('token',''),4096);secret=bounded(body.get('channel_secret',''),128)
    require(re.fullmatch(r'[A-Za-z0-9]{16,128}',secret),'채널 시크릿 형식 확인 필요',422)
    limit('line-connect:'+ws,5,60)
    with db() as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'유료 상담 또는 체험 권한 필요',403)
        require(not cl.scoped_link(c,ws,'line',agent),'기존 연결을 먼저 해제하세요.',409)
    try:bot=lt.bot_info(token)['id']
    except lt.LineError as e:require(False,str(e),422)
    with db(True) as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'유료 상담 또는 체험 권한 필요',403)
        require(not cl.scoped_link(c,ws,'line',agent),'기존 연결을 먼저 해제하세요.',409)
        require(not one(c,"SELECT ws FROM channel_link WHERE channel='line' AND partner=?",(bot,)) and not one(c,"SELECT ws FROM channel_brand_link WHERE channel='line' AND partner=?",(bot,)),'이미 등록된 공식 계정입니다.',409)
        key=secrets.token_urlsafe(32);args=(cl.digest(key),cl.lock_text(key),cl.lock_text(dump({'token':token,'secret':secret})),bot,0)
        if agent:c.execute('INSERT INTO channel_brand_link VALUES(?,?,?,?,?,?,?,?)',(ws,agent,'line',*args))
        else:c.execute('INSERT INTO channel_link VALUES(?,?,?,?,?,?,?)',(ws,'line',*args))
        return view(c,ws,agent)

@app.post('/api/line/activate')
def activate(body:dict,agent:str='',ws=Depends(ident)):
    require(enabled() and body.get('confirmed') is True,'활성화 동의 및 서버 설정 필요',403)
    with db(True) as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'상담 이용 권한 필요',403)
        r=cl.scoped_link(c,ws,'line',agent);require(r and one(c,'SELECT verified FROM line_verification WHERE ws=? AND agent=? AND link_hash=?',(ws,agent,r['secret_hash'])),'LINE Developers에서 웹훅 Verify 먼저 실행하세요.',409)
        if agent:c.execute("UPDATE channel_brand_link SET active=1 WHERE ws=? AND agent=? AND channel='line'",(ws,agent))
        else:c.execute("UPDATE channel_link SET active=1 WHERE ws=? AND channel='line'",(ws,))
        return view(c,ws,agent)

@app.post('/api/line/disconnect')
def disconnect(body:dict,agent:str='',ws=Depends(ident)):
    require(body.get('confirmed') is True,'연결 해제 확인 필요',422)
    with db(True) as c:
        ops.work_scope(c,getw(c,ws),agent)
        r=cl.scoped_link(c,ws,'line',agent)
        if not r:return {'ok':True}
        require(not one(c,"SELECT id FROM channel_job WHERE ws=? AND channel='line' AND status='running'",(ws,)),'상담 처리 완료 후 해제하세요.',409)
        if agent:c.execute("DELETE FROM channel_brand_link WHERE ws=? AND agent=? AND channel='line'",(ws,agent))
        else:c.execute("DELETE FROM channel_link WHERE ws=? AND channel='line'",(ws,))
        c.execute('DELETE FROM line_verification WHERE ws=? AND agent=?',(ws,agent))
        c.execute("UPDATE channel_job SET status='cancelled',body='',updated=? WHERE ws=? AND channel='line' AND status='queued' AND COALESCE((SELECT s.agent FROM channel_job_scope s WHERE s.ws=channel_job.ws AND s.job=channel_job.id),'')=?",(now(),ws,agent))
    return {'ok':True}

@app.post('/hooks/providers/line/{key}')
async def webhook(key:str,req:Request):
    require(enabled(),'LINE 연동 비활성화',404);require(re.fullmatch(r'[A-Za-z0-9_-]{43}',key),'웹훅 인증 실패',404)
    chunks=[];size=0
    async for chunk in req.stream():
        size+=len(chunk);require(size<=256000,'웹훅 용량 초과',413);chunks.append(chunk)
    raw=b''.join(chunks)
    with db(True) as c:
        r=raw_link(c,cl.digest(key));require(r,'웹훅 인증 실패',404)
        ws,a=r['ws'],r['agent'];cred=loads(cl.unlock(r['credential']))
        require(line_verify(cred['secret'],raw,req.headers.get('X-Line-Signature','')),'웹훅 서명 오류',403)
        try:payload=json.loads(raw)
        except (ValueError,TypeError):require(False,'웹훅 형식 오류',422)
        require(isinstance(payload,dict) and payload.get('destination')==r['partner'] and isinstance(payload.get('events'),list),'공식 계정 불일치',403)
        limit('line-hook:'+ws,120,60)
        c.execute('INSERT INTO line_verification VALUES(?,?,?,?) ON CONFLICT(ws,agent) DO UPDATE SET link_hash=excluded.link_hash,verified=excluded.verified',(ws,a,r['secret_hash'],now()))
        if not r['active'] or not cl.permitted_link(c,getw(c,ws),r):return Response(status_code=200)
        events=line_in(payload,r['partner']);require(len(events)<=100,'웹훅 이벤트 한도 초과',422)
        for m in events:
            event=cl.digest(r['secret_hash']+':'+m.event_id)
            if one(c,'SELECT id FROM channel_job WHERE ws=? AND channel=? AND event_key=?',(ws,'line',event)):continue
            i=uid()
            c.execute('INSERT INTO channel_job VALUES(?,?,?,?,?,?,?,?,?)',(i,ws,'line',event,cl.lock_text(dump({'user':m.user,'text':m.text,'target':m.reply_token,'link_hash':r['secret_hash'],'partner':r['partner']})),'queued','',now(),now()))
            c.execute('INSERT INTO channel_job_scope VALUES(?,?,?)',(ws,i,a))
    return Response(status_code=200)

"""Opt-in WebRTC signaling for human web consultations; no telephony or recording."""
import os,re,hashlib
from fastapi import Depends
from app import app,ident,require,bounded,visitor,limit
from store import *
import ops,staff_access

RING_TTL=120
CALL_TTL=1800
def enabled_server():return os.getenv('ENABLE_WEB_CALLS')=='1'
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS web_call_setting(ws TEXT NOT NULL,agent TEXT NOT NULL,enabled INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS web_call(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,kind TEXT NOT NULL,state TEXT NOT NULL,offer TEXT NOT NULL,answer TEXT NOT NULL,claim TEXT NOT NULL,actor TEXT NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,updated INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS web_call_scope ON web_call(ws,thread,state,expires);
        """)
init()

def configured(c,ws,agent):
    r=one(c,'SELECT enabled FROM web_call_setting WHERE ws=? AND agent=?',(ws,agent))
    return bool(r and r['enabled'])

def enabled(c,ws,agent):return enabled_server() and configured(c,ws,agent)
def public_enabled(c,w,agent):
    return public_access(w) and enabled(c,w['id'],agent['id'] if agent else '') and bool(agent['enabled'] if agent else w['enabled'])

def customer_scope(c,body):
    token=bounded(body.get('token',''),100);limit('webcall-customer:'+token,60,60)
    v=visitor(c,token,kind='public');w=getw(c,v['ws']);agent=ops.public_work_scope(c,w,v)
    t=one(c,"SELECT id FROM thread WHERE ws=? AND visitor=? AND kind='public'",(v['ws'],token))
    require(t and ops.thread_brand(c,w,t['id'],True)==agent,'상담 없음',404)
    return w,agent,t['id']

def owner_scope(c,ws,tid):
    w=getw(c,ws);agent=ops.thread_brand(c,w,tid,True)
    require(one(c,"SELECT id FROM thread WHERE ws=? AND id=? AND kind='public'",(ws,tid)),'웹 상담만 지원합니다.',404)
    return w,agent,tid,'owner'

def employee_scope(c,ws,mid,tid):
    m,w=staff_access.membership(c,ws,mid);t=staff_access.visible_thread(c,m,w,tid,True)
    require(t['kind']=='public','웹 상담만 지원합니다.',404)
    return w,m['agent'],tid,mid

def current(c,ws,tid):
    return one(c,"SELECT * FROM web_call WHERE ws=? AND thread=? AND state IN ('ringing','claimed','answered') AND expires>? ORDER BY created DESC LIMIT 1",(ws,tid,now()))

def lookup(c,ws,tid,i):
    r=one(c,'SELECT * FROM web_call WHERE ws=? AND thread=? AND id=?',(ws,tid,i))
    require(r,'통화 요청 없음',404);return r

def effective(r):
    if r['state'] in ('ringing','claimed','answered') and r['expires']<=now():return 'expired'
    return r['state']

def summary(r):
    return {'id':r['id'],'kind':r['kind'],'state':effective(r),'expires':r['expires']}

def validate_sdp(body,key):
    s=body.get(key)
    require(isinstance(s,str) and 1<=len(s)<=60000 and s.startswith('v=0') and 'm=audio ' in s and '\x00' not in s,'통화 신호 형식 오류',422)
    return s

def claim_hash(value):
    require(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{20,100}',value),'통화 연결 키 오류',422)
    return hashlib.sha256(value.encode()).hexdigest()

@app.get('/api/web-calls/settings')
def call_settings(agent:str='',ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);ops.work_scope(c,w,agent)
        return {'available':enabled_server(),'enabled':configured(c,ws,agent)}

@app.post('/api/web-calls/settings')
def save_settings(body:dict,agent:str='',ws=Depends(ident)):
    flag=body.get('enabled');require(type(flag) is bool,'통화 설정 오류',422)
    with db(True) as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'유료 상담 권한 필요',403)
        require(not flag or enabled_server(),'서버 통화 기능 준비 중',503)
        c.execute('INSERT INTO web_call_setting VALUES(?,?,?) ON CONFLICT(ws,agent) DO UPDATE SET enabled=excluded.enabled',(ws,agent,int(flag)))
        if not flag:c.execute("UPDATE web_call SET state='ended',offer='',answer='',claim='',updated=? WHERE ws=? AND agent=? AND state IN ('ringing','claimed','answered')",(now(),ws,agent))
    return {'ok':True}

@app.post('/api/customer/web-calls')
def customer_call(body:dict):
    action=body.get('action')
    require(action in ('start','status','end'),'통화 요청 오류',422)
    with db(True) as c:
        w,agent,tid=customer_scope(c,body);ws=w['id']
        if action=='start':
            require(enabled(c,ws,agent),'통화가 비활성화되었습니다.',403)
            kind=body.get('kind');require(kind in ('audio','video') and body.get('confirmed') is True,'통화 동의 필요',422)
            offer=validate_sdp(body,'offer')
            require((kind=='video')==('m=video ' in offer),'통화 유형 불일치',422)
            require(not current(c,ws,tid),'이미 통화 요청이 있습니다.',409)
            require(not one(c,"SELECT client FROM request WHERE ws=? AND thread=? AND state='running'",(ws,tid)),'AI 응답 완료 후 요청하세요.',409)
            # Expired signaling data is discarded on next call attempt.
            c.execute("UPDATE web_call SET state='expired',offer='',answer='',claim='',updated=? WHERE ws=? AND thread=? AND state IN ('ringing','claimed','answered') AND expires<=?",(now(),ws,tid,now()))
            i=uid();t=now()
            c.execute('INSERT INTO web_call VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,agent,tid,kind,'ringing',offer,'','','',t,t+RING_TTL,t))
            c.execute("UPDATE thread SET manual=1,status='pending' WHERE ws=? AND id=?",(ws,tid))
            ops.event(c,ws,'handoff','고객 '+('영상' if kind=='video' else '음성')+' 통화 요청',tid)
            return {'id':i,'kind':kind,'state':'ringing','expires':t+RING_TTL}
        r=lookup(c,ws,tid,bounded(body.get('id',''),100))
        if action=='end' or not enabled(c,ws,agent):
            c.execute("UPDATE web_call SET state='ended',offer='',answer='',claim='',updated=? WHERE ws=? AND id=?",(now(),ws,r['id']))
            return {'id':r['id'],'kind':r['kind'],'state':'ended','expires':r['expires']}
        state=effective(r)
        if state=='expired':
            c.execute("UPDATE web_call SET state='expired',offer='',answer='',claim='',updated=? WHERE ws=? AND id=?",(now(),ws,r['id']))
        return summary(r)|({'answer':r['answer']} if state=='answered' else {})

def operate(c,w,agent,tid,actor,body):
    ws=w['id'];action=body.get('action')
    require(action in ('list','claim','answer','status','end','decline'),'통화 요청 오류',422)
    if action=='list':
        r=current(c,ws,tid)
        return {'call':summary(r) if r and enabled(c,ws,agent) else None}
    i=bounded(body.get('id',''),100);r=lookup(c,ws,tid,i)
    if action=='decline':
        require(effective(r)=='ringing','이미 처리된 요청입니다.',409)
        c.execute("UPDATE web_call SET state='ended',offer='',answer='',claim='',updated=? WHERE ws=? AND id=?",(now(),ws,i))
        return {'state':'ended'}
    h=claim_hash(body.get('key',''))
    if action=='claim':
        require(enabled(c,ws,agent) and body.get('confirmed') is True and effective(r)=='ringing','수락 가능한 통화 없음',409)
        c.execute("UPDATE web_call SET state='claimed',claim=?,actor=?,updated=? WHERE ws=? AND id=? AND state='ringing'",(h,actor,now(),ws,i))
        return summary(r)|{'state':'claimed','offer':r['offer']}
    require(r['actor']==actor and r['claim']==h,'통화 참여 권한 없음',403)
    if action=='end' or not enabled(c,ws,agent):
        c.execute("UPDATE web_call SET state='ended',offer='',answer='',claim='',updated=? WHERE ws=? AND id=?",(now(),ws,i))
        return {'state':'ended'}
    state=effective(r)
    if action=='answer':
        require(state=='claimed','통화 요청이 만료되었습니다.',409)
        answer=validate_sdp(body,'answer')
        require((r['kind']=='video')==('m=video ' in answer),'통화 유형 불일치',422)
        expires=now()+CALL_TTL
        c.execute("UPDATE web_call SET answer=?,state='answered',expires=?,updated=? WHERE ws=? AND id=?",(answer,expires,now(),ws,i))
        return {'state':'answered','expires':expires}
    if state=='expired':
        c.execute("UPDATE web_call SET state='expired',offer='',answer='',claim='',updated=? WHERE ws=? AND id=?",(now(),ws,i))
    return summary(r)

@app.post('/api/inbox/{tid}/web-call')
def owner_call(tid:str,body:dict,ws=Depends(ident)):
    limit('webcall-owner:'+ws,60,60)
    with db(True) as c:return operate(c,*owner_scope(c,ws,tid),body)

@app.post('/api/staff/{mid}/threads/{tid}/web-call')
def staff_call(mid:str,tid:str,body:dict,ws=Depends(ident)):
    limit('webcall-staff:'+ws,60,60)
    with db(True) as c:return operate(c,*employee_scope(c,ws,mid,tid),body)

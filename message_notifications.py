"""Transactional operator SMS/Alimtalk, SOLAPI adapter, disabled by default.

Never accepts arbitrary text or recipients from public chat. A workspace requests
its own notification phone; live sends require an operator-approved recipient.
One purchased message unit is reserved per delivery. Explicit provider rejection
restores that unit; ambiguous outcomes are held for reconciliation, never resent.
"""
import os,re,hmac,hashlib,secrets
from datetime import datetime,timezone
import httpx
from fastapi import Depends,Request
from app import app,ident,require,require_operator,limit
from store import *

EVENTS={'handoff':'new_alert','handoff_urgent':'new_alert','unanswered':'new_alert','new':'new_alert','unknown':'unknown_alert','booking':'booking_alert','report':'report'}
KINDS=('SMS','알림톡')
BODY='[CS AI] 새 업무 알림이 있습니다. 관리자 페이지에서 확인해 주세요.'
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS message_notify_config(ws TEXT PRIMARY KEY REFERENCES workspace(id),phone TEXT NOT NULL,kind TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,verified INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS message_notify_delivery(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),event TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,provider_id TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,event,kind));
        """)
init()

def configured(kind):
    return bool(os.getenv('SOLAPI_API_KEY') and os.getenv('SOLAPI_API_SECRET') and os.getenv('SOLAPI_SENDER') and (kind=='SMS' or (os.getenv('SOLAPI_ALIMTALK_PFID') and os.getenv('SOLAPI_ALIMTALK_TEMPLATE_ID'))))
def live(kind):
    return not DEMO and os.getenv('ENABLE_LIVE_MESSAGES')=='1' and configured(kind)
def phone(value):
    require(isinstance(value,str),'전화번호 오류',422)
    v=re.sub(r'[- ]','',value)
    require(bool(re.fullmatch(r'010[0-9]{8}',v)),'국내 휴대전화번호를 입력하세요.',422)
    return v
def mask(v):return v[:3]+'-****-'+v[-4:] if v else ''
def balance(c,ws,kind):
    row=one(c,'SELECT n FROM message_balance WHERE ws=? AND kind=?',(ws,kind))
    return row['n'] if row else 0

@app.get('/api/message-notifications')
def status(ws=Depends(ident)):
    with db() as c:
        conf=one(c,'SELECT * FROM message_notify_config WHERE ws=?',(ws,))
        return {'settings':{'phone':mask(conf['phone']),'kind':conf['kind'],'enabled':bool(conf['enabled']),'verified':bool(conf['verified'])} if conf else None,'balance':{k:balance(c,ws,k) for k in KINDS},'configured':{k:configured(k) for k in KINDS},'live':{k:live(k) for k in KINDS},'deliveries':rows(c,'SELECT id,kind,status,created,updated FROM message_notify_delivery WHERE ws=? ORDER BY created DESC LIMIT 50',(ws,))}

@app.post('/api/message-notifications')
def save(body:dict,ws=Depends(ident)):
    kind=body.get('kind');require(kind in KINDS,'발송 종류 오류',422)
    require(body.get('consent') is True,'업무 알림 수신 및 연락처 처리 동의가 필요합니다.',422)
    with db(True) as c:
        w=getw(c,ws);require(public_access(w),'구독 또는 운영자 권한 필요',403)
        old=one(c,'SELECT * FROM message_notify_config WHERE ws=?',(ws,))
        p=phone(body.get('phone')) if body.get('phone') else old['phone'] if old else phone('')
        verified=int(bool(old and old['phone']==p and old['verified']))
        c.execute('INSERT INTO message_notify_config VALUES(?,?,?,?,?,?) ON CONFLICT(ws) DO UPDATE SET phone=excluded.phone,kind=excluded.kind,enabled=excluded.enabled,verified=excluded.verified,updated=excluded.updated',(ws,p,kind,int(body.get('enabled') is True),verified,now()))
    return {'ok':True,'verified':bool(verified)}

@app.delete('/api/message-notifications')
def disable(ws=Depends(ident)):
    with db(True) as c:c.execute('DELETE FROM message_notify_config WHERE ws=?',(ws,))
    return {'ok':True}

@app.get('/api/operator/message-notifications')
def pending(req:Request):
    require_operator(req)
    with db() as c:return rows(c,'SELECT ws,phone,kind,verified,enabled,updated FROM message_notify_config ORDER BY updated DESC LIMIT 200')

@app.post('/api/operator/message-notifications/{ws}/verify')
def verify(ws:str,body:dict,req:Request):
    require_operator(req);require(body.get('confirmed') is True,'실제 번호 소유권과 수신 동의 확인 필요',422)
    with db(True) as c:
        p=phone(body.get('phone'));row=one(c,'SELECT phone FROM message_notify_config WHERE ws=?',(ws,))
        require(row and hmac.compare_digest(row['phone'],p),'등록 번호 불일치',409)
        c.execute('UPDATE message_notify_config SET verified=1 WHERE ws=? AND phone=?',(ws,p))
    return {'ok':True}

def auth():
    date=datetime.now(timezone.utc).isoformat(timespec='seconds')
    salt=secrets.token_hex(16);sig=hmac.new(os.environ['SOLAPI_API_SECRET'].encode(),(date+salt).encode(),hashlib.sha256).hexdigest()
    return {'Authorization':'HMAC-SHA256 apiKey='+os.environ['SOLAPI_API_KEY']+', date='+date+', salt='+salt+', signature='+sig}

def send(row,conf):
    if DEMO:return 'simulated',''
    if not live(row['kind']):return 'rejected',''
    message={'to':conf['phone'],'from':os.environ['SOLAPI_SENDER'],'type':'SMS' if row['kind']=='SMS' else 'ATA','country':'82','text':BODY,'autoTypeDetect':False,'customFields':{'csaiDelivery':row['id']}}
    if row['kind']=='알림톡':
        message['kakaoOptions']={'pfId':os.environ['SOLAPI_ALIMTALK_PFID'],'templateId':os.environ['SOLAPI_ALIMTALK_TEMPLATE_ID'],'disableSms':True}
    try:
        r=httpx.post('https://api.solapi.com/messages/v4/send-many/detail',headers=auth(),json={'messages':[message],'showMessageList':True,'strict':True},timeout=15,follow_redirects=False)
        data=r.json()
        results=data.get('messageList') or []
        if isinstance(results,list) and len(results)==1 and results[0].get('messageId'):
            return 'accepted',str(results[0]['messageId'])[:100]
        if data.get('failedMessageList') and not results:return 'rejected',''
    except Exception:pass
    return 'uncertain',''

def complete(row,state,provider_id=''):
    with db(True) as c:
        latest=one(c,'SELECT status FROM message_notify_delivery WHERE id=?',(row['id'],))
        if not latest or latest['status'] not in ('sending','accepted'):return
        if state=='rejected':
            c.execute('INSERT INTO message_balance VALUES(?,?,1) ON CONFLICT(ws,kind) DO UPDATE SET n=message_balance.n+1',(row['ws'],row['kind']))
        c.execute('UPDATE message_notify_delivery SET status=?,provider_id=?,updated=? WHERE id=?',(state,provider_id or row.get('provider_id',''),now(),row['id']))

def dispatch(ws):
    with db(True) as c:
        w=getw(c,ws);conf=one(c,'SELECT * FROM message_notify_config WHERE ws=? AND enabled=1',(ws,))
        if not w or not conf or not public_access(w):return 0
        if not DEMO and (not conf['verified'] or not live(conf['kind'])):return 0
        rights=entitlements(w)
        available=balance(c,ws,conf['kind'])
        if available<=0:return 0
        pending=rows(c,"SELECT e.* FROM event_log e LEFT JOIN message_notify_delivery d ON d.ws=e.ws AND d.event=e.id AND d.kind=? WHERE e.ws=? AND e.seen=0 AND e.created>=? AND d.id IS NULL ORDER BY e.created LIMIT 100",(conf['kind'],ws,max(conf['updated'],now()-86400)))
        chosen=[x for x in pending if EVENTS.get(x['kind']) in rights][:min(5,available)]
        jobs=[]
        for event in chosen:
            i=uid();row={'id':i,'ws':ws,'kind':conf['kind'],'event':event['id']}
            c.execute('UPDATE message_balance SET n=n-1 WHERE ws=? AND kind=?',(ws,conf['kind']))
            c.execute('INSERT INTO message_notify_delivery VALUES(?,?,?,?,?,?,?,?)',(i,ws,event['id'],conf['kind'],'sending','',now(),now()))
            jobs.append(row)
    for row in jobs:
        with db() as c:
            latest=one(c,'SELECT * FROM message_notify_config WHERE ws=? AND enabled=1',(ws,));w=getw(c,ws)
            event=one(c,'SELECT kind FROM event_log WHERE id=? AND ws=?',(row['event'],ws))
            valid=bool(latest and latest['phone']==conf['phone'] and latest['kind']==conf['kind'] and latest['updated']==conf['updated'] and w and public_access(w) and event and EVENTS.get(event['kind']) in entitlements(w) and (DEMO or latest['verified']))
        state,pid=send(row,conf) if valid else ('rejected','')
        complete(row,state,pid)
    return len(jobs)

def reconcile(row):
    if not live(row['kind']) or not row['provider_id']:return
    try:
        r=httpx.get('https://api.solapi.com/messages/v4/list',headers=auth(),params={'criteria':'messageId','cond':'eq','value':row['provider_id'],'limit':1},timeout=10,follow_redirects=False)
        r.raise_for_status();m=r.json().get('messageList',{}).get(row['provider_id'])
        if not m or m.get('customFields',{}).get('csaiDelivery')!=row['id'] or m.get('status')!='COMPLETE':return
        code=str(m.get('statusCode',''))
        if code=='4000':complete(row,'delivered')
        # Final failure requires a known documented non-success code. Unknown values stay accepted for review.
        elif code.isdigit() and 4001<=int(code)<6000:complete(row,'rejected')
    except Exception:return

def tick():
    if os.getenv('ENABLE_AUTO_MESSAGES')!='1':return
    with db(True) as c:
        c.execute("UPDATE message_notify_delivery SET status='uncertain',updated=? WHERE status='sending' AND created<?",(now(),now()-1800))
        workspaces=rows(c,'SELECT ws FROM message_notify_config WHERE enabled=1')
        sent=rows(c,"SELECT * FROM message_notify_delivery WHERE status='accepted' AND updated<? ORDER BY updated LIMIT 20",(now()-60,))
    for x in workspaces:dispatch(x['ws'])
    for row in sent:reconcile(row)

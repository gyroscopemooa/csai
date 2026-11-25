"""Opt-in administrator Web Push. Only known browser push endpoints; no arbitrary webhooks."""
import base64,hashlib,re
from urllib.parse import urlsplit
from fastapi import Depends
from fastapi.responses import FileResponse
from app import app,ident,require
from store import *

EVENT_RIGHTS={'new':'new_alert','unknown':'unknown_alert','booking':'booking_alert','report':'report','work':'tasks'}
HOSTS={'fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com'}

def init_push():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS push_subscription(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),endpoint TEXT UNIQUE NOT NULL,keys TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS push_delivery(id TEXT PRIMARY KEY,ws TEXT NOT NULL,sub TEXT NOT NULL REFERENCES push_subscription(id) ON DELETE CASCADE,event TEXT NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(sub,event));
        """)
init_push()

def configured():
    return bool(os.getenv('VAPID_PUBLIC_KEY') and os.getenv('VAPID_PRIVATE_KEY') and os.getenv('VAPID_SUBJECT'))

def live_enabled():
    return configured() and not DEMO and os.getenv('ENABLE_LIVE_PUSH')=='1'

def decode_key(value,n):
    require(isinstance(value,str) and len(value)<200 and bool(re.fullmatch(r'[A-Za-z0-9_-]+={0,2}',value)),'잘못된 푸시 키',422)
    try:b=base64.urlsafe_b64decode(value+'='*((-len(value))%4))
    except Exception:require(False,'잘못된 푸시 키',422)
    require(len(b)==n,'잘못된 푸시 키',422)
    return b

def validate(body):
    endpoint=body.get('endpoint');keys=body.get('keys')
    require(isinstance(endpoint,str) and 0<len(endpoint)<=2048 and not any(ch.isspace() for ch in endpoint),'푸시 주소 오류',422)
    p=urlsplit(endpoint)
    require(p.scheme=='https' and p.netloc in HOSTS and p.path.startswith('/') and not p.fragment and not p.query,'지원 브라우저 푸시 서비스가 아닙니다.',422)
    require(isinstance(keys,dict),'푸시 키 없음',422)
    pub=decode_key(keys.get('p256dh'),65);decode_key(keys.get('auth'),16)
    from cryptography.hazmat.primitives.asymmetric import ec
    try:ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),pub)
    except ValueError:require(False,'잘못된 공개 키',422)
    return endpoint,{'p256dh':keys['p256dh'],'auth':keys['auth']}

@app.get('/push-sw.js')
def push_sw():return FileResponse(ROOT/'web/push-sw.js',media_type='application/javascript')

@app.get('/api/push')
def status(ws=Depends(ident)):
    with db() as c:
        require('push' in entitlements(getw(c,ws)))
        return {'configured':configured(),'live':live_enabled(),'public_key':os.getenv('VAPID_PUBLIC_KEY',''),'devices':rows(c,'SELECT id,created FROM push_subscription WHERE ws=? ORDER BY created DESC',(ws,)),'deliveries':rows(c,'SELECT status,created FROM push_delivery WHERE ws=? ORDER BY created DESC LIMIT 30',(ws,))}

@app.post('/api/push')
def subscribe(body:dict,ws=Depends(ident)):
    endpoint,keys=validate(body)
    with db(True) as c:
        require('push' in entitlements(getw(c,ws)));require(configured(),'VAPID 환경변수 설정 필요',503)
        old=one(c,'SELECT id,ws FROM push_subscription WHERE endpoint=?',(endpoint,))
        require(not old or old['ws']==ws,'이 브라우저의 기존 계정 알림을 해제하세요.',409)
        if old:
            c.execute('UPDATE push_subscription SET keys=? WHERE id=?',(dump(keys),old['id']));return {'id':old['id']}
        require(one(c,'SELECT COUNT(*) n FROM push_subscription WHERE ws=?',(ws,))['n']<10,'등록 기기는 최대 10개',409)
        i=uid();c.execute('INSERT INTO push_subscription VALUES(?,?,?,?,?)',(i,ws,endpoint,dump(keys),now()));return {'id':i}

@app.delete('/api/push/{i}')
def unsubscribe(i:str,ws=Depends(ident)):
    with db(True) as c:c.execute('DELETE FROM push_subscription WHERE id=? AND ws=?',(i,ws))
    return {'ok':True}

def send(sub,event):
    if not live_enabled():return 'simulated'
    import requests
    from pywebpush import webpush,WebPushException
    class NoRedirect(requests.Session):
        def request(self,*args,**kwargs):
            kwargs['allow_redirects']=False
            return super().request(*args,**kwargs)
    endpoint,keys=validate({'endpoint':sub['endpoint'],'keys':loads(sub['keys'])})
    with NoRedirect() as session:
        session.trust_env=False
        try:
            response=webpush(subscription_info={'endpoint':endpoint,'keys':keys},data=dump({'title':'CS AI 알림','body':'새로운 업무 알림이 있습니다. 관리자 화면에서 확인하세요.'}),vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],vapid_claims={'sub':os.environ['VAPID_SUBJECT']},timeout=10,ttl=300,requests_session=session)
            return 'sent' if 200<=response.status_code<300 else 'failed'
        except WebPushException as e:
            return 'expired' if getattr(e.response,'status_code',0) in (404,410) else 'failed'

def tick():
    if os.getenv('ENABLE_AUTO_PUSH')!='1' or (not DEMO and not live_enabled()):return 0
    count=0
    with db(True) as c:
        c.execute("UPDATE push_delivery SET status='failed' WHERE status='sending' AND created<?",(now()-1800,))
        devices=rows(c,'SELECT * FROM push_subscription ORDER BY created')
    for sub in devices:
        with db(True) as c:
            w=getw(c,sub['ws'])
            if not w or 'push' not in entitlements(w):continue
            rights=entitlements(w)
            events=rows(c,"SELECT e.* FROM event_log e LEFT JOIN push_delivery d ON d.sub=? AND d.event=e.id WHERE e.ws=? AND e.created>=? AND d.id IS NULL AND e.seen=0 ORDER BY e.created LIMIT 100",(sub['id'],sub['ws'],max(sub['created'],now()-86400)))
            events=[x for x in events if EVENT_RIGHTS.get(x['kind']) in rights][:5]
            for x in events:c.execute('INSERT INTO push_delivery VALUES(?,?,?,?,?,?)',(uid(),sub['ws'],sub['id'],x['id'],'sending',now()))
        for x in events:
            try:
                with db() as c:
                    w=getw(c,sub['ws']);active=one(c,'SELECT id FROM push_subscription WHERE id=? AND ws=?',(sub['id'],sub['ws']))
                    allowed=bool(active and w and {'push',EVENT_RIGHTS[x['kind']]}.issubset(entitlements(w)))
                result=send(sub,x) if allowed else 'failed'
            except Exception:result='failed'
            with db(True) as c:
                if result=='expired':c.execute('DELETE FROM push_subscription WHERE id=? AND ws=?',(sub['id'],sub['ws']))
                else:c.execute('UPDATE push_delivery SET status=? WHERE sub=? AND event=?',(result,sub['id'],x['id']))
            count+=1
    return count

"""Opt-in provider webhook implementation. Real accounts and approval required.
Persistent queue; no network work in ingress; no arbitrary callback host allowed.
"""
import hashlib,secrets,os,json,httpx,time
from urllib.parse import urlsplit
from fastapi import Depends,Request,Response
from app import app,ident,require,fail,bounded,chat,limit
from store import *
from google_calendar import encryption
from integrations.channels import naver_in,naver_out,kakao_in,kakao_out

def init_channels():
    with db(True) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS channel_link(ws TEXT NOT NULL,channel TEXT NOT NULL,secret_hash TEXT NOT NULL UNIQUE,secret TEXT NOT NULL,credential TEXT NOT NULL,partner TEXT NOT NULL,active INTEGER NOT NULL,PRIMARY KEY(ws,channel));
        CREATE TABLE IF NOT EXISTS channel_job(id TEXT PRIMARY KEY,ws TEXT NOT NULL,channel TEXT NOT NULL,event_key TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL,created INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,channel,event_key));
        ''')
init_channels()
def enabled():return os.getenv('ENABLE_CHANNEL_WEBHOOKS','0')=='1' and APP_URL.startswith('https://')
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def lock_text(t):return encryption().encrypt(t.encode()).decode()
def unlock(t):return encryption().decrypt(t.encode()).decode()

def checked_callback(url):
    u=urlsplit(url);hosts={h.strip().lower() for h in os.getenv('KAKAO_CALLBACK_HOSTS','').split(',') if h.strip()}
    return u.scheme=='https' and u.hostname in hosts and u.port in (None,443) and not u.username and not u.password and not u.fragment

@app.get('/api/integrations/channels/{ch}')
def status(ch:str,ws=Depends(ident)):
    require(ch in ['naver','kakao'],'채널 오류',422)
    with db() as c:
        w=getw(c,ws);require(ch in entitlements(w));r=one(c,'SELECT * FROM channel_link WHERE ws=? AND channel=?',(ws,ch));jobs=rows(c,'SELECT id,status,error,created FROM channel_job WHERE ws=? AND channel=? ORDER BY rowid DESC LIMIT 30',(ws,ch))
    return {'configured':enabled(),'saved':bool(r),'active':bool(r and r['active']),'partner':r['partner'] if r else '', 'webhook':APP_URL+'/hooks/'+ch+'/'+unlock(r['secret']) if r else '', 'jobs':jobs}
@app.post('/api/integrations/channels/{ch}')
def setup(ch:str,body:dict,ws=Depends(ident)):
    require(ch in ['naver','kakao'],'채널 오류',422);require(os.getenv('INTEGRATION_ENCRYPTION_KEY'),'암호화 키를 먼저 설정하세요.',503);partner=bounded(body.get('partner',''),200);cred=bounded(body.get('credential',''),1000)
    require(partner,'파트너 ID 또는 봇 ID 필요',422)
    if ch=='naver':require(cred,'보내기 API Authorization 필요',422)
    if ch=='kakao' and body.get('active'):require(bool(os.getenv('KAKAO_CALLBACK_HOSTS')),'공식 콜백 호스트 확인 후 등록 필요',503)
    with db(True) as c:
        require(ch in entitlements(getw(c,ws)));old=one(c,'SELECT * FROM channel_link WHERE ws=? AND channel=?',(ws,ch));st=unlock(old['secret']) if old else secrets.token_urlsafe(32)
        active=int(body.get('active') is True);require(not active or enabled(),'HTTPS 및 서버 연동 활성화 필요',503)
        c.execute('INSERT INTO channel_link VALUES(?,?,?,?,?,?,?) ON CONFLICT(ws,channel) DO UPDATE SET credential=excluded.credential,partner=excluded.partner,active=excluded.active',(ws,ch,digest(st),lock_text(st),lock_text(cred),partner,active))
    return {'webhook':APP_URL+'/hooks/'+ch+'/'+st,'active':bool(active)}
@app.post('/api/integrations/channels/{ch}/disconnect')
def disconnect(ch:str,ws=Depends(ident)):
    with db(True) as c:c.execute('DELETE FROM channel_link WHERE ws=? AND channel=?',(ws,ch));c.execute("UPDATE channel_job SET status='cancelled',body='' WHERE ws=? AND channel=? AND status='queued'",(ws,ch))
    return {'ok':True}
@app.post('/hooks/{ch}/{secret}')
def ingress(ch:str,secret:str,body:dict,req:Request):
    require(enabled() and ch in ['naver','kakao'],'연동 비활성화',404)
    with db(True) as c:
        link=one(c,'SELECT * FROM channel_link WHERE channel=? AND secret_hash=? AND active=1',(ch,digest(secret)));require(link,'채널 인증 실패',404);ws=link['ws'];w=getw(c,ws);require(ch in entitlements(w) and w['enabled'],'상담 비활성화',403);limit('hook:'+ws+':'+ch,120)
        if ch=='naver':
            m=naver_in(body)
            if not m:return Response(status_code=200) # ignore echo and non-text events
            if body.get('partner'):require(body['partner']==link['partner'],'파트너 ID 불일치',403)
            target=''
        else:
            require(body.get('bot',{}).get('id')==link['partner'],'봇 ID 불일치',403);m=kakao_in(body);require(m,'텍스트 문의만 지원',422);target=body.get('userRequest',{}).get('callbackUrl','');require(isinstance(target,str) and checked_callback(target),'승인된 콜백 URL 필요',422)
        # Kakao callback is a one-use event ID. Naver has no reliable ID in the documented text event.
        key=digest(target if target else dump(body)+':'+str(now()//10))
        if not one(c,'SELECT id FROM channel_job WHERE ws=? AND channel=? AND event_key=?',(ws,ch,key)):
            c.execute('INSERT INTO channel_job VALUES(?,?,?,?,?,?,?,?,?)',(uid(),ws,ch,key,lock_text(dump({'user':m.user,'text':m.text,'target':target})),'queued','',now(),now()))
    return {'version':'2.0','useCallback':True} if ch=='kakao' else Response(status_code=200)

def process_one(ws=None):
    """Returns True if a job was handled. Ambiguous outbound failure is not auto-retried."""
    with db(True) as c:
        sql="SELECT * FROM channel_job WHERE status='queued'";args=()
        if ws:sql+=' AND ws=?';args=(ws,)
        j=one(c,sql+' ORDER BY rowid LIMIT 1',args)
        if not j:return False
        c.execute("UPDATE channel_job SET status='running',updated=? WHERE id=?",(now(),j['id']));link=one(c,'SELECT * FROM channel_link WHERE ws=? AND channel=? AND active=1',(j['ws'],j['channel']));w=getw(c,j['ws'])
    state='sent';error='';ch=j['channel'];ws=j['ws']
    try:
        if not enabled() or not link or ch not in entitlements(w) or not w['enabled']:raise RuntimeError('연동 비활성화')
        if now()-j['created']>240:raise RuntimeError('메시지 처리 기한 초과')
        body=loads(unlock(j['body']));external=digest(body['user'])
        with db(True) as c:
            ss=one(c,'SELECT token FROM channel_session WHERE ws=? AND channel=? AND external_user=?',(ws,ch,external));token=ss['token'] if ss else None
            if not token or not one(c,'SELECT token FROM visitor WHERE token=? AND expires>?',(token,now())):
                token=uid();c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'));c.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(uid(),ws,token,ch,now()));c.execute('INSERT INTO channel_session VALUES(?,?,?,?) ON CONFLICT(ws,channel,external_user) DO UPDATE SET token=excluded.token',(ws,ch,external,token))
        r=chat({'token':token,'message':body['text'],'clientMessageId':j['id']});reply=r['reply']
        if r.get('booking'):reply='예약 가능한 시간과 정보 확인은 다음 공식 상담 링크에서 진행해 주세요.\n'+APP_URL+'/c/'+w['slug']
        if ch=='naver':resp=httpx.post('https://gw.talk.naver.com/chatbot/v1/event',headers={'Authorization':unlock(link['credential'])},json=naver_out(body['user'],reply),timeout=10,follow_redirects=False);ok=resp.is_success and resp.json().get('success') is not False
        else:
            if not checked_callback(body['target']):raise RuntimeError('콜백 호스트 불일치')
            resp=httpx.post(body['target'],json=kakao_out(reply),timeout=10,follow_redirects=False);ok=resp.is_success and resp.json().get('status')=='SUCCESS'
        if not ok:raise RuntimeError('외부 채널 응답 실패')
    except Exception as e:state='failed';error=type(e).__name__+': '+('외부 채널 처리 실패 또는 응답 미확인' if not isinstance(e,RuntimeError) else str(e)[:100])
    with db(True) as c:c.execute('UPDATE channel_job SET status=?,error=?,body=\'\',updated=? WHERE id=?',(state,error,now(),j['id']))
    return True
@app.post('/api/integrations/channel-jobs/process')
def process(ws=Depends(ident)):
    require(enabled(),'연동 비활성화',503);return {'processed':process_one(ws)}

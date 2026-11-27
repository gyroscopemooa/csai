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
        CREATE TABLE IF NOT EXISTS channel_destination(ws TEXT NOT NULL,thread TEXT NOT NULL,channel TEXT NOT NULL,link_hash TEXT NOT NULL,partner TEXT NOT NULL,recipient TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,thread));
        CREATE TABLE IF NOT EXISTS channel_job_thread(ws TEXT NOT NULL,job TEXT NOT NULL,thread TEXT NOT NULL,PRIMARY KEY(ws,job));
        CREATE TABLE IF NOT EXISTS channel_staff_outbox(id TEXT PRIMARY KEY,ws TEXT NOT NULL,thread TEXT NOT NULL,client TEXT NOT NULL,channel TEXT NOT NULL,link_hash TEXT NOT NULL,partner TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL,created INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,thread,client));
        CREATE TABLE IF NOT EXISTS channel_job(id TEXT PRIMARY KEY,ws TEXT NOT NULL,channel TEXT NOT NULL,event_key TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL,created INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,channel,event_key));
        ''')
init_channels()
def enabled():return os.getenv('ENABLE_CHANNEL_WEBHOOKS','0')=='1' and APP_URL.startswith('https://')
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def lock_text(t):return encryption().encrypt(t.encode()).decode()
def unlock(t):return encryption().decrypt(t.encode()).decode()

def staff_enabled():
    return enabled() and os.getenv('ENABLE_NAVER_STAFF_SEND','0')=='1'

def naver_success(resp):
    if not resp.is_success:return False
    result=resp.json()
    return isinstance(result,dict) and result.get('success') is True and result.get('resultCode')=='00'

def staff_destination(c,ws,t):
    if not staff_enabled() or t['kind']!='naver':return None
    w=getw(c,ws)
    if not w or not w['enabled'] or not public_access(w) or 'naver' not in entitlements(w):return None
    target=one(c,"SELECT * FROM channel_destination WHERE ws=? AND thread=? AND channel='naver'",(ws,t['id']))
    link=one(c,"SELECT * FROM channel_link WHERE ws=? AND channel='naver' AND active=1",(ws,))
    if not target or not link or target['link_hash']!=link['secret_hash'] or target['partner']!=link['partner']:return None
    # Only the current live conversation may be used to send; no guessed recipient, no expired old thread.
    ss=one(c,"SELECT token FROM channel_session WHERE ws=? AND channel='naver' AND external_user=?",(ws,digest(unlock(target['recipient']))))
    v=one(c,"SELECT token FROM visitor WHERE ws=? AND token=? AND expires>?",(ws,t['visitor'],now()))
    if not ss or not v or ss['token']!=t['visitor']:return None
    return target,link

def staff_info(c,ws,t):
    available=False
    try:available=bool(staff_destination(c,ws,t))
    except Exception:pass
    jobs=rows(c,'SELECT id,status,error,created,updated FROM channel_staff_outbox WHERE ws=? AND thread=? ORDER BY created DESC LIMIT 20',(ws,t['id']))
    inbound=rows(c,'SELECT j.id,j.status,j.error,j.created,j.updated FROM channel_job j JOIN channel_job_thread jt ON jt.ws=j.ws AND jt.job=j.id WHERE j.ws=? AND jt.thread=? ORDER BY j.created DESC LIMIT 20',(ws,t['id']))
    return {'available':available,'jobs':jobs,'inbound':inbound}

def staff_pending(c,ws,thread):
    return one(c,"SELECT id FROM channel_staff_outbox WHERE ws=? AND thread=? AND status IN ('queued','running')",(ws,thread))

@app.post('/api/inbox/{thread}/channel-reply')
def queue_staff(thread:str,body:dict,ws=Depends(ident)):
    raw=body.get('reply');client=body.get('client')
    require(isinstance(raw,str) and 0<len(raw.strip())<=1000 and isinstance(client,str) and 1<=len(client)<=100 and body.get('confirmed') is True,'답변 1~1000자 및 발송 확인 필요',422)
    reply=raw.strip()
    with db(True) as c:
        t=one(c,'SELECT * FROM thread WHERE ws=? AND id=?',(ws,thread));require(t and thread_accessible(c,getw(c,ws),thread),'상담 없음 또는 조회 범위 초과',404)
        require(not one(c,'SELECT thread FROM demo_sample WHERE ws=? AND thread=?',(ws,thread)),'샘플은 발송할 수 없습니다.',409)
        old=one(c,'SELECT id,status FROM channel_staff_outbox WHERE ws=? AND thread=? AND client=?',(ws,thread,client))
        if old:return old
        target=staff_destination(c,ws,t);require(target,'네이버 실연동·직접 발송 허용 및 최신 고객 수신 필요',409)
        require(not staff_pending(c,ws,thread),'이전 답변 발송 중입니다.',409)
        require(not one(c,"SELECT id FROM channel_job WHERE ws=? AND channel='naver' AND status='running'",(ws,)),'외부 응답 처리 완료 후 발송하세요.',409)
        require(not one(c,"SELECT client FROM request WHERE ws=? AND thread=? AND state='running'",(ws,thread)),'AI 응답 완료 후 발송하세요.',409)
        i=uid();dest,link=target
        c.execute("UPDATE thread SET manual=1,status='pending' WHERE ws=? AND id=?",(ws,thread))
        c.execute('INSERT INTO channel_staff_outbox VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,thread,client,'naver',link['secret_hash'],link['partner'],lock_text(reply),'queued','',now(),now()))
    return {'id':i,'status':'queued'}

def process_staff_one(ws=None):
    # Claim before network I/O. Ambiguous outcome is never automatically resent.
    with db(True) as c:
        c.execute("UPDATE channel_staff_outbox SET status='unknown',error='발송 결과 확인 필요',body='',updated=? WHERE status='running' AND updated<?",(now(),now()-120))
        if not staff_enabled():return False
        sql="SELECT * FROM channel_staff_outbox o WHERE o.status='queued' AND NOT EXISTS(SELECT 1 FROM channel_job j WHERE j.ws=o.ws AND j.channel=o.channel AND j.status='running') AND NOT EXISTS(SELECT 1 FROM channel_staff_outbox r WHERE r.ws=o.ws AND r.channel=o.channel AND r.status='running')"
        args=()
        if ws:sql+=' AND o.ws=?';args=(ws,)
        j=one(c,sql+' ORDER BY o.created,o.id LIMIT 1',args)
        if not j:return False
        c.execute("UPDATE channel_staff_outbox SET status='running',updated=? WHERE id=?",(now(),j['id']))
        t=one(c,'SELECT * FROM thread WHERE ws=? AND id=?',(j['ws'],j['thread']))
        try:target=staff_destination(c,j['ws'],t) if t and t['manual'] and thread_accessible(c,getw(c,j['ws']),t['id']) else None
        except Exception:target=None
    state='failed';error='연결 변경, 만료 또는 권한 해제';reply=''
    if target and target[1]['secret_hash']==j['link_hash'] and target[1]['partner']==j['partner'] and now()-j['created']<=300:
        try:
            dest,link=target;reply=unlock(j['body']);recipient=unlock(dest['recipient']);credential=unlock(link['credential'])
            # All outbound credentials and destination are server-owned; fixed official URL.
            resp=httpx.post('https://gw.talk.naver.com/chatbot/v1/event',headers={'Authorization':credential},json=naver_out(recipient,reply),timeout=10,follow_redirects=False)
            if naver_success(resp):state='sent';error=''
            else:state='unknown';error='공급자 응답 확인 필요'
        except Exception:state='unknown';error='발송 결과 미확인 · 재전송 전 톡톡 확인'
    with db(True) as c:
        current=one(c,'SELECT status FROM channel_staff_outbox WHERE ws=? AND id=?',(j['ws'],j['id']))
        if current and current['status']=='running':
            if state=='sent':
                c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),j['ws'],j['thread'],'staff',reply,now()))
                c.execute("UPDATE thread SET status='open' WHERE ws=? AND id=?",(j['ws'],j['thread']))
            c.execute('UPDATE channel_staff_outbox SET status=?,error=?,body=?,updated=? WHERE ws=? AND id=?',(state,error,'',now(),j['ws'],j['id']))
    return True

def checked_callback(url):
    u=urlsplit(url);hosts={h.strip().lower() for h in os.getenv('KAKAO_CALLBACK_HOSTS','').split(',') if h.strip()}
    return u.scheme=='https' and u.hostname in hosts and u.port in (None,443) and not u.username and not u.password and not u.fragment

@app.get('/api/channel-delivery-issues')
def delivery_issues(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);cutoff=history_cutoff(w)
        incoming=rows(c,"SELECT j.id,j.channel,j.status,j.error,j.created,j.updated,COALESCE(jt.thread,'') AS thread FROM channel_job j LEFT JOIN channel_job_thread jt ON jt.ws=j.ws AND jt.job=j.id WHERE j.ws=? AND j.created>=? AND j.status IN ('failed','running','queued','cancelled') ORDER BY j.updated DESC LIMIT 100",(ws,cutoff))
        outgoing=rows(c,"SELECT id,channel,status,error,created,updated,thread FROM channel_staff_outbox WHERE ws=? AND created>=? AND status IN ('failed','unknown','running','queued') ORDER BY updated DESC LIMIT 100",(ws,cutoff))
        result=[]
        for origin,items in [('auto',incoming),('staff',outgoing)]:
            for item in items:
                if item['thread'] and not thread_accessible(c,w,item['thread']):continue
                result.append(item|{'origin':origin})
        return sorted(result,key=lambda x:(x['updated'],x['id']),reverse=True)[:100]

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
        require(ch in entitlements(getw(c,ws)));require(not one(c,"SELECT id FROM channel_job WHERE ws=? AND channel=? AND status='running'",(ws,ch)),'외부 메시지 처리 완료 후 연결을 변경하세요.',409);require(not one(c,"SELECT id FROM channel_staff_outbox WHERE ws=? AND channel=? AND status IN ('queued','running')",(ws,ch)),'직접 답변 발송 완료 후 연결을 변경하세요.',409);old=one(c,'SELECT * FROM channel_link WHERE ws=? AND channel=?',(ws,ch));st=unlock(old['secret']) if old and old['partner']==partner else secrets.token_urlsafe(32)
        active=int(body.get('active') is True);require(not active or enabled(),'HTTPS 및 서버 연동 활성화 필요',503)
        c.execute('INSERT INTO channel_link VALUES(?,?,?,?,?,?,?) ON CONFLICT(ws,channel) DO UPDATE SET secret_hash=excluded.secret_hash,secret=excluded.secret,credential=excluded.credential,partner=excluded.partner,active=excluded.active',(ws,ch,digest(st),lock_text(st),lock_text(cred),partner,active))
    return {'webhook':APP_URL+'/hooks/'+ch+'/'+st,'active':bool(active)}
@app.post('/api/integrations/channels/{ch}/disconnect')
def disconnect(ch:str,ws=Depends(ident)):
    with db(True) as c:require(not one(c,"SELECT id FROM channel_job WHERE ws=? AND channel=? AND status='running'",(ws,ch)),'외부 메시지 처리 완료 후 연결을 해제하세요.',409);require(not one(c,"SELECT id FROM channel_staff_outbox WHERE ws=? AND channel=? AND status='running'",(ws,ch)),'직접 답변 발송 완료 후 연결을 해제하세요.',409);c.execute("UPDATE channel_staff_outbox SET status='failed',error='연결 해제',body='',updated=? WHERE ws=? AND channel=? AND status='queued'",(now(),ws,ch));c.execute('DELETE FROM channel_link WHERE ws=? AND channel=?',(ws,ch));c.execute('DELETE FROM channel_destination WHERE ws=? AND channel=?',(ws,ch));c.execute("UPDATE channel_job SET status='cancelled',body='' WHERE ws=? AND channel=? AND status='queued'",(ws,ch))
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
            c.execute('INSERT INTO channel_job VALUES(?,?,?,?,?,?,?,?,?)',(uid(),ws,ch,key,lock_text(dump({'user':m.user,'text':m.text,'target':target,'link_hash':link['secret_hash'],'partner':link['partner']})),'queued','',now(),now()))
    return {'version':'2.0','useCallback':True} if ch=='kakao' else Response(status_code=200)

def process_one(ws=None):
    """Returns True if a job was handled. Ambiguous outbound failure is not auto-retried."""
    with db(True) as c:
        # Stale claims are marked unknown, not retried. Allow a later message to proceed.
        c.execute("UPDATE channel_job SET status='failed',error='처리 결과 미확인 · 재전송 금지',body='',updated=? WHERE status='running' AND updated<?",(now(),now()-900))
        sql="SELECT * FROM channel_job j WHERE status='queued' AND NOT EXISTS(SELECT 1 FROM channel_staff_outbox o WHERE o.ws=j.ws AND o.channel=j.channel AND o.status='running') AND NOT EXISTS(SELECT 1 FROM channel_job r WHERE r.ws=j.ws AND r.channel=j.channel AND r.status='running')";args=()
        if ws:sql+=' AND j.ws=?';args=(ws,)
        j=one(c,sql+' ORDER BY rowid LIMIT 1',args)
        if not j:return False
        c.execute("UPDATE channel_job SET status='running',updated=? WHERE id=?",(now(),j['id']));link=one(c,'SELECT * FROM channel_link WHERE ws=? AND channel=? AND active=1',(j['ws'],j['channel']));w=getw(c,j['ws'])
    state='sent';error='';ch=j['channel'];ws=j['ws']
    try:
        if not enabled() or not link or ch not in entitlements(w) or not w['enabled']:raise RuntimeError('연동 비활성화')
        if now()-j['created']>(55 if ch=='kakao' else 240):raise RuntimeError('메시지 처리 기한 초과')
        body=loads(unlock(j['body']));external=digest(body['user'])
        if body.get('link_hash')!=link['secret_hash'] or body.get('partner')!=link['partner']:raise RuntimeError('연결 변경 또는 이전 대기 메시지')
        with db(True) as c:
            ss=one(c,'SELECT token FROM channel_session WHERE ws=? AND channel=? AND external_user=?',(ws,ch,external));token=ss['token'] if ss else None
            t=one(c,'SELECT id FROM thread WHERE ws=? AND visitor=? AND kind=?',(ws,token,ch)) if token else None
            dest=one(c,'SELECT link_hash,partner FROM channel_destination WHERE ws=? AND thread=?',(ws,t['id'])) if t else None
            if not token or not t or not dest or dest['link_hash']!=link['secret_hash'] or dest['partner']!=link['partner'] or not one(c,'SELECT token FROM visitor WHERE ws=? AND token=? AND expires>?',(ws,token,now())):
                token=uid();tid=uid();c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'));c.execute('INSERT INTO thread(id,ws,visitor,kind,created,manual) VALUES(?,?,?,?,?,?)',(tid,ws,token,ch,now(),int(loads(w['settings']).get('consultation_mode')=='staff')));c.execute('INSERT INTO channel_session VALUES(?,?,?,?) ON CONFLICT(ws,channel,external_user) DO UPDATE SET token=excluded.token',(ws,ch,external,token))
            else:tid=t['id']
            c.execute('INSERT INTO channel_job_thread VALUES(?,?,?) ON CONFLICT(ws,job) DO NOTHING',(ws,j['id'],tid))
            c.execute('INSERT INTO channel_destination VALUES(?,?,?,?,?,?,?) ON CONFLICT(ws,thread) DO UPDATE SET updated=excluded.updated',(ws,tid,ch,link['secret_hash'],link['partner'],lock_text(body['user']) if ch=='naver' else '',now()))
        r=chat({'token':token,'message':body['text'],'clientMessageId':j['id']});reply=r['reply']
        if r.get('booking'):reply='예약 가능한 시간과 정보 확인은 다음 공식 상담 링크에서 진행해 주세요.\n'+APP_URL+'/c/'+w['slug']
        if ch=='naver' and r.get('manual'):ok=True;state='held'
        elif ch=='naver':resp=httpx.post('https://gw.talk.naver.com/chatbot/v1/event',headers={'Authorization':unlock(link['credential'])},json=naver_out(body['user'],reply),timeout=10,follow_redirects=False);ok=naver_success(resp)
        else:
            if now()-j['created']>55:raise RuntimeError('카카오 콜백 유효 시간 초과 · 답변 전송 안 됨')
            if not checked_callback(body['target']):raise RuntimeError('콜백 호스트 불일치')
            resp=httpx.post(body['target'],json=kakao_out(reply),timeout=10,follow_redirects=False);ok=resp.is_success and resp.json().get('status')=='SUCCESS'
        if not ok:raise RuntimeError('외부 채널 응답 실패')
    except Exception as e:state='failed';error=type(e).__name__+': '+('외부 채널 처리 실패 또는 응답 미확인' if not isinstance(e,RuntimeError) else str(e)[:100])
    with db(True) as c:c.execute('UPDATE channel_job SET status=?,error=?,body=\'\',updated=? WHERE id=? AND status=\'running\'',(state,error,now(),j['id']))
    return True
@app.post('/api/integrations/channel-jobs/process')
def process(ws=Depends(ident)):
    require(enabled(),'연동 비활성화',503);return {'processed':process_staff_one(ws) or process_one(ws)}

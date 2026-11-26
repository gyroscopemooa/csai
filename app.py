import base64,copy,io,json,os,re,secrets,math,time,threading
from collections import defaultdict,deque
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit,urlencode
import httpx,qrcode
from fastapi import FastAPI,Request,HTTPException,Response,Depends
from fastapi.responses import FileResponse,RedirectResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from store import *
import ai
app=FastAPI(title='CS AI local development',docs_url='/api/docs')
RATE=defaultdict(deque); RATE_LOCK=threading.Lock()
def limit(key,maximum=30,window=60):
    with RATE_LOCK:
        q=RATE[key];t=now()
        while q and q[0]<=t-window:q.popleft()
        if len(q)>=maximum:raise HTTPException(429,'요청이 너무 많습니다.')
        q.append(t)
        if len(RATE)>5000:
            for k in list(RATE):
                if not RATE[k] or RATE[k][-1]<t-window:RATE.pop(k,None)
app.mount('/assets',StaticFiles(directory=ROOT/'web'),name='assets')
@app.get('/health')
def health():return {'ok':True,'service':'CS AI','mode':'development' if DEMO else 'configured'}

def fail(status,msg):raise HTTPException(status,msg)
def require(ok,msg='추가 기능 구매가 필요합니다.',status=403):
    if not ok:fail(status,msg)
def bounded(v,n=2000):
    if not isinstance(v,str) or len(v)>n:fail(422,'텍스트 형식 또는 길이 오류')
    return v.strip()
MODEL_RATES={
    'gpt-6.2-sol':(2.0,10.0,0.10),
    'gpt-6-luna':(0.05,0.25,0.005),
}
def record_usage(c,ws,kind,model,result):
    # Real Responses usage is attached by the adapter when available; demo events are never revenue.
    u=result.pop('_usage',{}) if isinstance(result,dict) else {}
    inp=int(u.get('input_tokens',0) or 0);cached=int(u.get('cached_input_tokens',u.get('input_tokens_details',{}).get('cached_tokens',0)) or 0);out=int(u.get('output_tokens',0) or 0)
    prefix='TRAIN' if kind=='training' else 'CHAT';ri,ro,rc=MODEL_RATES.get(model,(0.0,0.0,0.0))
    ri=float(os.getenv(prefix+'_INPUT_USD_PER_M',str(ri)));ro=float(os.getenv(prefix+'_OUTPUT_USD_PER_M',str(ro)));rc=float(os.getenv(prefix+'_CACHED_USD_PER_M',str(rc)));cost=(max(0,inp-cached)*ri+cached*rc+out*ro)/1_000_000
    c.execute('INSERT INTO model_usage VALUES(?,?,?,?,?,?,?,?,?,?)',(uid(),ws,kind,model,'actual' if u and ai.KEY else ('local_rule' if ai.KEY else 'simulation'),inp,cached,out,cost,now()))
def ident(req:Request):
    with db() as c:
        s=one(c,'SELECT * FROM session WHERE token=? AND expires>?',(req.cookies.get('csai_session',''),now()))
    if not s:fail(401,'로그인이 필요합니다.')
    return s['ws']
@app.middleware('http')
async def guard(req,call_next):
    allowed_origin=APP_URL
    context=None
    host=(req.url.hostname or '').lower()
    if os.getenv('ENABLE_CUSTOM_DOMAINS')=='1' and host!=urlsplit(APP_URL).hostname and req.url.path!='/health':
        from starlette.concurrency import run_in_threadpool
        def lookup():
            with db() as c:return domains.resolve_host(c,host)
        w=await run_in_threadpool(lookup)
        if not w:return Response('Unknown or inactive domain',404)
        path=req.url.path
        if path=='/' and req.method=='GET':return RedirectResponse('/c/'+w['slug'],307)
        allowed=path in ('/c/'+w['slug'],'/api/config','/api/public/'+w['slug'],'/api/session','/api/chat','/api/booking/availability','/api/booking/draft','/api/customer/requests','/api/customer/bookings/recover') or path.startswith('/assets/') or bool(re.fullmatch(r'/api/(?:session/[A-Za-z0-9_-]+/messages|booking/form/[A-Za-z0-9_-]+|booking/[A-Za-z0-9_-]+/confirm|customer/bookings/[A-Za-z0-9_-]+(?:/change|/recovery-code)?|customer/requests/[A-Za-z0-9_-]+)',path))
        if not allowed:return Response('Public consultation only',404)
        allowed_origin='https://'+host
        context=domains.current_ws.set(w['id'])
    try:
        if req.method in ['POST','PATCH','DELETE','PUT']:
            origin=req.headers.get('origin')
            if origin and origin!=allowed_origin:return Response('Origin rejected',403)
            if int(req.headers.get('content-length','0') or 0)>8_000_000:return Response('Payload too large',413)
        res=await call_next(req)
        res.headers['X-Content-Type-Options']='nosniff';res.headers['Referrer-Policy']='no-referrer';res.headers['Cache-Control']='no-store'
        if not req.url.path.startswith('/widget/'):res.headers['X-Frame-Options']='SAMEORIGIN'
        return res
    finally:
        if context is not None:domains.current_ws.reset(context)

def session_response(owner,verified_email=None):
    with db(True) as c:
        w=workspace(c,owner)
        if owner.startswith('google:') and verified_email:
            c.execute('UPDATE workspace SET owner_email=? WHERE id=?',(verified_email.lower(),w['id']))
        t=uid();c.execute('INSERT INTO session VALUES(?,?,?)',(t,w['id'],now()+86400*7))
    r=RedirectResponse('/#education',303);r.set_cookie('csai_session',t,httponly=True,samesite='lax',secure=APP_URL.startswith('https://'),max_age=86400*7);return r
def current_workspace(req):
    with db() as c:
        s=one(c,'SELECT * FROM session WHERE token=? AND expires>?',(req.cookies.get('csai_session',''),now()))
        return getw(c,s['ws']) if s else None
def require_operator(req):
    w=current_workspace(req);require(w and is_operator(w),'운영자 권한이 필요합니다.',403);return w
@app.get('/auth/demo')
def login_demo():
    require(DEMO and not SHARED_TEST,'공유 테스트 환경에서는 Google 로그인이 필요합니다.',403);return session_response('demo:'+uid())
@app.post('/auth/operator-local')
def login_operator_local(req:Request,body:dict):
    require(DEMO and not SHARED_TEST and 'local:operator' in OPERATOR_OWNERS,'로컬 전용 운영자 로그인만 허용됩니다.',403)
    expected=os.getenv('LOCAL_OPERATOR_TOKEN','');supplied=str(body.get('token',''))
    require(len(expected)>=24 and secrets.compare_digest(expected,supplied),'운영자 토큰이 올바르지 않습니다.',401)
    return session_response('local:operator')
@app.get('/auth/google')
def google():
    client=os.getenv('GOOGLE_CLIENT_ID');require(client and os.getenv('GOOGLE_CLIENT_SECRET'),'Google OAuth 환경변수를 먼저 설정하세요.',503)
    st=uid()
    with db(True) as c:c.execute('INSERT INTO oauth_state VALUES(?,?)',(st,now()+600))
    r=RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':client,'redirect_uri':APP_URL+'/auth/google/callback','response_type':'code','scope':'openid email profile','state':st,'prompt':'select_account'}));r.set_cookie('oauth_state',st,httponly=True,samesite='lax',secure=APP_URL.startswith('https://'),max_age=600);return r
@app.get('/auth/google/callback')
def callback(req:Request,code:str,state:str):
    require(secrets.compare_digest(req.cookies.get('oauth_state',''),state),'잘못된 OAuth 상태')
    with db(True) as c:
        require(one(c,'SELECT * FROM oauth_state WHERE state=? AND expires>?',(state,now())),'OAuth 만료');c.execute('DELETE FROM oauth_state WHERE state=?',(state,))
    t=httpx.post('https://oauth2.googleapis.com/token',data={'code':code,'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET'],'redirect_uri':APP_URL+'/auth/google/callback','grant_type':'authorization_code'},timeout=15);require(t.status_code==200,'Google 인증 실패',502)
    p=httpx.get('https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+t.json()['access_token']},timeout=15);require(p.status_code==200 and p.json().get('sub'),'Google 사용자 확인 실패',502)
    identity=p.json();verified_email=identity.get('email') if identity.get('email_verified') is True else None
    return session_response('google:'+identity['sub'],verified_email)
@app.post('/api/logout')
def logout(req:Request):
    with db(True) as c:c.execute('DELETE FROM session WHERE token=?',(req.cookies.get('csai_session',''),))
    r=Response(status_code=204);r.delete_cookie('csai_session');return r
@app.get('/api/config')
def config():return {'demo':DEMO,'shared_test':SHARED_TEST,'ai_connected':bool(ai.KEY),'google_configured':bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET')),'train_model':ai.TRAIN,'chat_model':ai.CHAT,'catalog':CAT}
@app.get('/api/me')
def me(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);t=trial(c,w);op=is_operator(w);credits=(10000-operator_wallet(c,w)['credit_used']) if op else (t['credit_limit']-t['credit_used'] if t else w['credits']);return {'slug':w['slug'],'settings':loads(w['settings']),'plan':w['plan'],'credits':credits,'remaining':remaining(c,w),'quota':10000 if op else t['chat_limit'] if t else PLAN[w['plan']]['quantity'],'public_access':public_access(w),'sandbox_allowed':sandbox_allowed(c,w),'addons':loads(w['addons']),'entitlements':sorted(entitlements(w)),'enabled':bool(w['enabled']),'published':loads(w['published']),'operator':op,'trial':({'expires':t['expires'],'bookings_remaining':trial_bookings_remaining(c,w)} if t else None)}
@app.patch('/api/settings')
def settings(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);s=loads(w['settings']);old=copy.deepcopy(s)
        if 'prompt' in body:require(body['prompt']==s['prompt'],'상담 지침 변경은 AI 교육에서 진행하세요.',422)
        for k in ['brand','tone','notice','price','location','hours','welcome','fallback']:
            if k in body:s[k]=bounded(body[k],2500 if k=='prompt' else 1500)
        if 'emoji' in body:s['emoji']=bool(body['emoji'])
        if 'links' in body:
            require(isinstance(body['links'],list) and len(body['links'])<=10,'판매처 최대 10개',422);s['links']=[]
            for x in body['links']:
                u=bounded(x['url'],1000);p=urlsplit(u);require(p.scheme=='https' and p.hostname and not p.username,'HTTPS 링크만 등록',422);s['links'].append({'name':bounded(x['name'],100),'url':u})
        if 'modes' in body:
            for k,v in body['modes'].items():
                if k in s['modes'] and v in ['auto','manual','off']:s['modes'][k]=v
        if any(k in body for k in ['fields','open','close','duration','buffer','closed_days','payment_required','timezone','resources']):require('calendar' in entitlements(w))
        if 'resources' in body:
            rs=body['resources'];require(isinstance(rs,list) and 1<=len(rs)<=20,'담당자는 1~20명',422);out=[];seen=set()
            for r in rs:
                require(isinstance(r,dict),'담당자 형식',422);k=bounded(r.get('id',''),60);n=bounded(r.get('name',''),100);require(re.fullmatch(r'[a-zA-Z0-9_-]+',k) and k not in seen and n,'담당자 정보 오류',422);seen.add(k);out.append({'id':k,'name':n})
            require('default' in seen,'기본 담당자는 유지해야 합니다.',422)
            for existing in rows(c,"SELECT DISTINCT resource FROM booking WHERE ws=? AND status IN ('confirmed','pending','pending_payment') AND start>?",(ws,datetime.now(timezone.utc).isoformat())):require(existing['resource'] in seen,'예정 예약이 있는 담당자는 삭제할 수 없습니다.',409)
            s['resources']=out
            if old.get('resources')!=out:s['template_version']+=1
        if 'fields' in body:
            fs=body['fields'];require(isinstance(fs,list) and len(fs)<=30,'양식 최대 30개',422);keys=set();out=[]
            for f in fs:
                key=bounded(f['key'],60);require(re.fullmatch(r'[a-zA-Z0-9_-]+',key) and key not in keys,'필드 키 중복/오류',422);keys.add(key);require(f['type'] in ['text','phone','number','date','time','select','boolean'],'필드 유형 오류',422);out.append({'key':key,'label':bounded(f['label'],100),'type':f['type'],'required':bool(f['required']),'options':[bounded(x,100) for x in f.get('options',[])[:20]]})
            if out!=s['fields']:s['template_version']+=1
            s['fields']=out
        for k in ['open','close']:
            if k in body:require(bool(re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',body[k])),'시간 오류',422);s[k]=body[k]
        require(s['open']<s['close'],'영업 시작은 종료보다 빨라야 합니다.',422)
        for k in ['duration','buffer']:
            if k in body:require(type(body[k])==int and (5 if k=='duration' else 0)<=body[k]<=480,'시간 간격 오류',422);s[k]=body[k]
        if 'closed_days' in body:require(isinstance(body['closed_days'],list) and all(type(x)==int and 0<=x<=6 for x in body['closed_days']),'휴무 요일 오류',422);s['closed_days']=body['closed_days']
        if 'payment_required' in body:s['payment_required']=bool(body['payment_required'])
        if 'timezone' in body:
            try:ZoneInfo(body['timezone']);s['timezone']=body['timezone']
            except Exception:fail(422,'시간대 오류')
        if any(old[k]!=s[k] for k in ['open','close','duration','buffer','closed_days','payment_required','timezone']):s['template_version']+=1
        enabled=w['enabled']
        if 'enabled' in body:require(public_access(w) or not body['enabled'],'구독 또는 초청 체험 후 공개할 수 있습니다.');enabled=int(bool(body['enabled']))
        c.execute('UPDATE workspace SET settings=?,enabled=? WHERE id=?',(dump(s),enabled,ws))
    return {'ok':True}
@app.post('/api/demo/billing')
def demo_billing(body:dict,ws=Depends(ident)):
    require(DEMO,'실제 결제 연동 전에는 변경할 수 없습니다.')
    with db(True) as c:
        w=getw(c,ws);require(sandbox_allowed(c,w),'공유 환경에서는 운영자만 테스트 구매할 수 있습니다.',403);p=body.get('plan',w['plan']);require(p in PLAN,'요금제 오류',422);a=body.get('addons',loads(w['addons']));require(isinstance(a,list) and all(x in ADD or x in PACK for x in a),'상품 오류',422)
        # normalize duplicated channel subscriptions
        a=set(a)
        if 'channels' in a:a-= {'naver','kakao'}
        for i in list(a):
            if i in PACK:a-=set(PACK[i]['includes'])
        for i in list(a):
            if i in ADD:a.update(ADD[i]['requires'])
        q=body.get('education');n=0
        if q:
            e=next((e for e in CAT['education'] if e['id']==q and e['price']>0),None);require(e,'교육 상품 오류',422);n=e['quantity']
        c.execute('UPDATE workspace SET plan=?,addons=?,credits=credits+?,enabled=CASE WHEN ?=\'free\' THEN 0 ELSE enabled END WHERE id=?',(p,dump(sorted(a)),n,p,ws))
        if n:c.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uid(),ws,'demo_grant',n,q,now()))
    return {'ok':True,'demo':True}
@app.get('/api/operator/invites')
def invite_list(req:Request):
    require_operator(req)
    with db() as c:return rows(c,'SELECT id,chat_limit,credit_limit,booking_limit,expires,days,created,revoked,used_by,used_at FROM trial_invite ORDER BY created DESC')
@app.post('/api/operator/invites')
def invite_create(body:dict,req:Request):
    require_operator(req)
    chats=body.get('chat_limit',50);credits=body.get('credit_limit',100);days=body.get('days',14)
    require(chats in [50,100,300],'상담 체험은 50, 100, 300회만 선택할 수 있습니다.',422);require(type(credits)==int and 20<=credits<=300,'교육 체험은 20~300C여야 합니다.',422);require(type(days)==int and 1<=days<=30,'체험 기간은 1~30일입니다.',422)
    code=secrets.token_urlsafe(24);i=uid()
    accept_expires=now()+7*86400
    with db(True) as c:c.execute('INSERT INTO trial_invite(id,code_hash,chat_limit,credit_limit,booking_limit,expires,days,created,revoked) VALUES(?,?,?,?,?,?,?,?,?)',(i,__import__('hashlib').sha256(code.encode()).hexdigest(),chats,credits,10,accept_expires,days,now(),0))
    return {'id':i,'code':code,'accept_path':'/#invite='+code,'chat_limit':chats,'credit_limit':credits,'days':days,'accept_expires':accept_expires}
@app.post('/api/operator/invites/{i}/revoke')
def invite_revoke(i:str,req:Request):
    require_operator(req)
    with db(True) as c:
        r=one(c,'SELECT * FROM trial_invite WHERE id=?',(i,));require(r,'초청 링크 없음',404);c.execute('UPDATE trial_invite SET revoked=1 WHERE id=?',(i,))
        if r['used_by']:
            w=one(c,'SELECT id FROM workspace WHERE owner=?',(r['used_by'],));
            if w:c.execute('DELETE FROM trial_access WHERE ws=?',(w['id'],))
    return {'ok':True}
@app.post('/api/invites/accept')
def invite_accept(body:dict,req:Request,ws=Depends(ident)):
    code=bounded(body.get('code',''),200);h=__import__('hashlib').sha256(code.encode()).hexdigest()
    with db(True) as c:
        w=getw(c,ws);require(w['owner'].startswith('google:'),'Google 로그인 후 초청을 수락할 수 있습니다.',403);require(not is_operator(w) and w['plan']=='free','무료 가입 계정만 초청 체험에 참여할 수 있습니다.',409);require(not one(c,'SELECT id FROM trial_invite WHERE used_by=?',(w['owner'],)),'이 계정은 이미 체험에 참여했습니다.',409)
        x=one(c,'SELECT * FROM trial_invite WHERE code_hash=? AND revoked=0 AND used_by IS NULL AND expires>?',(h,now()));require(x,'유효하지 않거나 만료된 초청 링크입니다.',404)
        trial_expires=now()+x['days']*86400
        c.execute('UPDATE trial_invite SET used_by=?,used_at=? WHERE id=?',(w['owner'],now(),x['id']));c.execute('INSERT INTO trial_access VALUES(?,?,?,?,?,?,?,?)',(w['id'],x['id'],x['chat_limit'],0,x['credit_limit'],0,x['booking_limit'],trial_expires));c.execute('UPDATE workspace SET free_used=1 WHERE id=?',(ws,))
    return {'ok':True,'expires':trial_expires}
@app.get('/api/operator/costs')
def operator_costs(req:Request):
    w=require_operator(req)
    with db() as c:
        r=rows(c,'SELECT kind,model,mode,SUM(input_tokens) input_tokens,SUM(cached_input_tokens) cached_input_tokens,SUM(output_tokens) output_tokens,CAST(ROUND(CAST(SUM(estimated_cost_usd) AS NUMERIC),6) AS REAL) estimated_cost_usd,COUNT(*) calls FROM model_usage GROUP BY kind,model,mode ORDER BY kind,model,mode')
    return {'models':{'training':ai.TRAIN,'chat':ai.CHAT},'rows':r,'note':'모의 호출은 실제 비용/매출에 집계하지 않습니다.'}
@app.get('/api/faq')
def listfaq(ws=Depends(ident)):
    with db() as c:return rows(c,'SELECT id,q,a FROM faq WHERE ws=?',(ws,))
@app.post('/api/faq')
def faq(body:dict,ws=Depends(ident)):
    q=bounded(body.get('q',''),500);a=bounded(body.get('a',''),2000);require(q and a,'질문과 답변을 입력하세요.',422)
    with db(True) as c:
        w=getw(c,ws);unknown_id=body.get('unknown');u=one(c,"SELECT u.id,v.agent FROM unknown u JOIN thread t ON t.id=u.thread JOIN visitor v ON v.token=t.visitor WHERE u.ws=? AND u.id=? AND u.status='open'",(ws,unknown_id)) if unknown_id else None;require(not unknown_id or u,'미학습 질문 없음',404);agent_id=(u.get('agent') or '') if u else ''
        if agent_id:require('extra_agent' in entitlements(w),'추가 상담원 권한 필요',403)
        text=ai.clean(q+' => '+a);estimate=ai.estimate(text,[]);i=uid();c.execute('INSERT INTO training VALUES(?,?,?,?,?,?,?,?)',(i,ws,'estimated',estimate,0,dump({'text':text,'images':[],'unknown':unknown_id,'agent':agent_id}),None,now()))
        t=trial(c,w);credits=10000-operator_wallet(c,w)['credit_used'] if is_operator(w) else (t['credit_limit']-t['credit_used'] if t else w['credits'])
    return {'id':i,'maxCredits':estimate,'credits':credits,'enough':credits>=estimate,'requires_run':True}
@app.delete('/api/faq/{i}')
def delete_faq(i:str,ws=Depends(ident)):
    with db(True) as c:c.execute('DELETE FROM faq WHERE ws=? AND id=?',(ws,i))
    return {'ok':True}
@app.get('/api/files')
def files(ws=Depends(ident)):
    with db() as c:return rows(c,'SELECT id,name,created,length(content) AS chars FROM file WHERE ws=? ORDER BY created DESC',(ws,))
@app.post('/api/files')
def upload(body:dict,ws=Depends(ident)):
    try:
        name=bounded(body['name'],200);raw=base64.b64decode(body['data'],validate=True);t,ims,sha=ai.extract(name,raw)
    except Exception as e:fail(422,'파일 분석 실패: '+str(e)[:200])
    with db(True) as c:
        old=one(c,'SELECT id FROM file WHERE ws=? AND sha=?',(ws,sha))
        if old:return {'id':old['id'],'duplicate':True}
        require((one(c,'SELECT count(*) AS n FROM file WHERE ws=?',(ws,)))['n']<50,'파일 최대 50개',422)
        i=uid();c.execute('INSERT INTO file VALUES(?,?,?,?,?,?,?)',(i,ws,name,sha,t,dump(ims),now()))
    return {'id':i,'chars':len(t),'images':len(ims),'estimate':ai.estimate(t,ims)}
@app.delete('/api/files/{i}')
def delete_file(i:str,ws=Depends(ident)):
    with db(True) as c:c.execute('DELETE FROM file WHERE ws=? AND id=?',(ws,i))
    return {'ok':True}
@app.post('/api/training/estimate')
def estimate(body:dict,ws=Depends(ident)):
    text=bounded(body.get('text',''),30000);images=[];ids=body.get('files',[]);require(isinstance(ids,list) and len(ids)<=10,'최대 10개 파일',422)
    with db(True) as c:
        w=getw(c,ws);agent_id=body.get('agent','');require(isinstance(agent_id,str),'상담원 형식 오류',422)
        if agent_id:require('extra_agent' in entitlements(w) and one(c,'SELECT id FROM agent_profile WHERE ws=? AND id=?',(ws,agent_id)),'추가 상담원 권한 또는 정보 없음',403)
        for i in dict.fromkeys(ids):
            f=one(c,'SELECT * FROM file WHERE id=? AND ws=?',(i,ws));require(f,'파일 없음',404);text+='\n'+f['name']+'\n'+f['content'];images+=loads(f['images'])
        require((text.strip() or images) and len(text)<=60000 and len(images)<=8,'교육 자료 없음 또는 한도 초과',422)
        text=ai.clean(text);n=ai.estimate(text,images);i=uid();c.execute('INSERT INTO training VALUES(?,?,?,?,?,?,?,?)',(i,ws,'estimated',n,0,dump({'text':text,'images':images,'agent':agent_id}),None,now()))
        t=trial(c,w);credits=10000-operator_wallet(c,w)['credit_used'] if is_operator(w) else (t['credit_limit']-t['credit_used'] if t else w['credits'])
        return {'id':i,'maxCredits':n,'credits':credits,'enough':credits>=n}
@app.post('/api/training/{i}/run')
def train(i:str,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);j=one(c,'SELECT * FROM training WHERE id=? AND ws=?',(i,ws));require(j and j['state']=='estimated' and j['created']>now()-1800,'유효한 교육 견적 필요',409)
        source=loads(j['source']);agent_id=source.get('agent','');agent=one(c,'SELECT * FROM agent_profile WHERE ws=? AND id=?',(ws,agent_id)) if agent_id else None
        if agent_id:require(agent and 'extra_agent' in entitlements(w),'추가 상담원 권한 필요',403)
        try:reserve_education(c,w,j['estimate'],i)
        except ValueError as e:fail(402,str(e))
        c.execute('UPDATE training SET state=\'running\' WHERE id=?',(i,));s=loads(w['settings']);s.update(loads(agent['settings']) if agent else {})
    try:
        result,n=ai.train(source['text'],source['images'],s);require(type(n)==int and 0<=n<=j['estimate'],'교육 비용 상한 초과 또는 형식 오류',409)
    except Exception as e:
        with db(True) as c:
            settle_education(c,ws,i,0);c.execute('UPDATE training SET state=\'failed\' WHERE id=?',(i,))
        fail(502,'교육에 실패했습니다. 예약된 크레딧은 정산되었습니다.')
    with db(True) as c:
        settle_education(c,ws,i,n);record_usage(c,ws,'training',ai.TRAIN,result);c.execute('UPDATE training SET state=\'review\',cost=?,result=?,source=? WHERE id=?',(n,dump(result),dump({'unknown':source.get('unknown'),'agent':agent_id}),i))
    return {'id':i,'cost':n,'result':result}
@app.get('/api/training')
def jobs(ws=Depends(ident)):
    with db() as c:return [dict({k:v for k,v in j.items() if k!='source'},agent=loads(j['source']).get('agent',''),result=loads(j['result']) if j['result'] else None) for j in rows(c,'SELECT id,state,estimate,cost,result,created,source FROM training WHERE ws=? ORDER BY created DESC',(ws,))]
@app.post('/api/training/{i}/publish')
def publish(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        j=one(c,'SELECT * FROM training WHERE id=? AND ws=?',(i,ws));require(j and j['state'] in ['review','published'],'승인할 결과 없음',409)
        if j['state']=='published':return {'ok':True}
        result=loads(j['result']);w=getw(c,ws);source=loads(j['source']);agent_id=source.get('agent','');agent=one(c,'SELECT * FROM agent_profile WHERE ws=? AND id=?',(ws,agent_id)) if agent_id else None
        if agent_id:require(agent and 'extra_agent' in entitlements(w),'추가 상담원 권한 필요',403)
        old=loads(agent['published'] if agent else w['published'])
        if body.get('replace'):merged=result
        else:merged={'style':result.get('style',old.get('style','')),'rules':list(dict.fromkeys(old.get('rules',[])+result.get('rules',[])))[-100:],'faq':list({x['q']:x for x in old.get('faq',[])+result.get('faq',[])}.values())[-200:],'conflicts':result.get('conflicts',[])}
        if agent:
            c.execute('INSERT INTO agent_knowledge_version VALUES(?,?,?,?,?)',(uid(),ws,agent_id,agent['published'],now()));c.execute('UPDATE agent_profile SET published=? WHERE ws=? AND id=?',(dump(merged),ws,agent_id))
        else:
            ops.checkpoint(c,ws,'교육 반영 전');c.execute('UPDATE workspace SET published=? WHERE id=?',(dump(merged),ws))
        if source.get('unknown'):c.execute("UPDATE unknown SET status='resolved' WHERE ws=? AND id=?",(ws,source['unknown']))
        c.execute('UPDATE training SET state=\'published\' WHERE id=?',(i,))
    return {'ok':True}

def visitor(c,token,ws=None,kind=None):
    v=one(c,'SELECT * FROM visitor WHERE token=? AND expires>?',(token,now()));require(v and (not ws or v['ws']==ws) and (not kind or v['kind']==kind) and (not domains.current_ws.get() or (v['ws']==domains.current_ws.get() and v['kind']=='public')),'상담 세션이 만료되었습니다.',401);return v
@app.get('/api/public/{slug}')
def public_info(slug:str):
    with db() as c:
        w,agent=branding.resolve(c,slug);require(public_access(w) and w['enabled'],'상담이 비활성화되었습니다.',404);s=loads(w['settings']);s.update(loads(agent['settings']) if agent else {});return {k:s[k] for k in ['brand','notice','links','welcome']}|branding.appearance(w,s)|{'calendar':'calendar' in entitlements(w),'requests':[k for k in ['quote','complaints','tasks'] if k in entitlements(w)],'demo':DEMO}
@app.post('/api/session')
def create_session(body:dict,req:Request):
    kind='test' if body.get('test') else 'public';agent=None
    require(not domains.current_ws.get() or kind=='public','공개 상담 전용 도메인입니다.',403)
    limit('session:'+str(req.client.host if req.client else 'unknown'),60)
    with db(True) as c:
        if kind=='test':
            token=req.cookies.get('csai_session','');s=one(c,'SELECT * FROM session WHERE token=? AND expires>?',(token,now()));require(s,'로그인 필요',401);w=getw(c,s['ws'])
        else:
            w,agent=branding.resolve(c,body.get('slug'));require(public_access(w) and w['enabled'],'상담 비활성화',404);require(not domains.current_ws.get() or w['id']==domains.current_ws.get(),'다른 업체의 상담입니다.',404)
        token=uid();c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,w['id'],now()+86400,kind));
        if agent:c.execute('UPDATE visitor SET agent=? WHERE token=?',(agent['id'],token))
        i=uid();c.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(i,w['id'],token,kind,now()))
    return {'token':token,'thread':i}
@app.get('/api/session/{token}/messages')
def messages(token:str):
    with db() as c:
        v=visitor(c,token);t=one(c,'SELECT * FROM thread WHERE visitor=? AND ws=?',(token,v['ws']));return rows(c,'SELECT role,body,created FROM message WHERE ws=? AND thread=? ORDER BY rowid',(v['ws'],t['id']))
def abort_chat_request(key,period,kind):
    """Recover once; a successful but ambiguous commit is replayed, never refunded."""
    ws,tid,client=key
    with db(True) as c:
        prior=one(c,'SELECT state,result FROM request WHERE ws=? AND thread=? AND client=?',key)
        if prior and prior['state']=='done':return loads(prior['result'])
        if prior and prior['state']=='running':
            refund_chat(c,getw(c,ws),period,kind)
            c.execute("UPDATE request SET state='failed' WHERE ws=? AND thread=? AND client=?",key)
    return None

@app.post('/api/chat')
def chat(body:dict):
    token=bounded(body.get('token',''),100);client=bounded(body.get('clientMessageId',''),100);msg=bounded(body.get('message',''),2000);require(msg and client,'메시지 필요',422)
    with db(True) as c:
        v=visitor(c,token);ws=v['ws'];w=getw(c,ws);t=one(c,'SELECT * FROM thread WHERE ws=? AND visitor=?',(ws,token));tid=t['id'];s,agent=branding.merged(c,w,v);p=usage_period(w);key=(ws,tid,client)
        prior=one(c,'SELECT * FROM request WHERE ws=? AND thread=? AND client=?',key)
        if prior:
            if prior['state']=='done':return loads(prior['result'])
            if prior['state']=='running':fail(409,'이미 처리 중입니다.')
            c.execute('DELETE FROM request WHERE ws=? AND thread=? AND client=?',key)
        require(v['kind']=='test' or (w['enabled'] and public_access(w)),'상담 비활성화')
        require(one(c,'SELECT count(*) AS n FROM request WHERE ws=? AND thread=? AND created>?',(ws,tid,now()-60))['n']<12,'잠시 후 다시 문의하세요.',429)
        if t['manual']:
            r={'reply':'담당자가 확인 중입니다.','manual':True,'remaining':remaining(c,w)}
            c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,tid,'user',msg,now()));c.execute('INSERT INTO request VALUES(?,?,?,?,?,?,?,?)',(*key,'done',dump(r),p,'manual',now()));
            if v['kind']!='test' and not one(c,'SELECT id FROM event_log WHERE ws=? AND kind=? AND ref=?',(ws,'new',tid)):ops.event(c,ws,'new','신규 고객 상담',tid)
            return r
        require(not one(c,"SELECT client FROM request WHERE ws=? AND thread=? AND state='running'",(ws,tid)),'이전 응답 처리 중입니다.',409)
        try:kind=charge_chat(c,w,p)
        except ValueError as e:fail(402,str(e))
        c.execute('INSERT INTO request VALUES(?,?,?,?,?,?,?,?)',(*key,'running',None,p,kind,now()));history=list(reversed(rows(c,'SELECT role,body FROM message WHERE ws=? AND thread=? ORDER BY rowid DESC LIMIT 8',(ws,tid))));faq=loads(agent['faq']) if agent else rows(c,'SELECT q,a FROM faq WHERE ws=?',(ws,));published=loads(agent['published'] if agent else w['published']);adds=entitlements(w)
        quote_catalog=rows(c,'SELECT id,name,price FROM quote_item WHERE ws=? AND active=1 ORDER BY name LIMIT 100',(ws,)) if 'quote' in adds else []
    try:r=ai.answer(msg,history,s,faq,published,adds,loads(t.get('booking_context','{}')),quote_catalog)
    except Exception as e:
        replay=abort_chat_request(key,p,kind)
        if replay is not None:return replay
        fail(502,'상담 처리 실패. 사용량은 복구되었습니다.')
    proposal=r.pop('workDraft',None)
    if v['kind']=='public' and not r.get('booking') and s['modes'].get('general')!='off':
        work_kind=next((k for k,pat in [('quote',r'견적|제안서'),('complaints',r'불만|민원|항의'),('tasks',r'오류 신고|장애 신고|업무 요청')] if k in adds and re.search(pat,msg)),None)
        if isinstance(proposal,dict) and proposal.get('kind') in {'quote','tasks','complaints'}&adds:
            work_kind=proposal['kind']
        else:proposal=None
        if work_kind and not (work_kind=='complaints' and s['modes'].get('complaint')=='off'):
            r['workDraft']=proposal or {'kind':work_kind,'title':msg[:120],'details':msg[:2000]}
    if r.get('unknown') and s['modes'].get('unknown')=='off':r.update({'reply':'등록된 답변이 없어 안내가 어렵습니다.','unknown':False})
    try:
        with db(True) as c:
            for role,body in [('user',msg),('assistant',r['reply'])]:c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,tid,role,body,now()))
            if v['kind']!='test' and not history:ops.event(c,ws,'new','신규 고객 상담',tid)
            if v['kind']!='test':customer_ops.capture_lead(c,ws,tid,msg,r)
            if v['kind']=='public' and 'quote' in adds:customer_ops.capture_quote_suggestion(c,ws,tid,msg,r)
            if r.get('unknown'):
                if v['kind']!='test':ops.event(c,ws,'unknown','미학습 질문 접수',tid)
                c.execute('INSERT INTO unknown VALUES(?,?,?,?,?,?)',(uid(),ws,tid,msg,'open',now()));c.execute('UPDATE thread SET status=\'pending\' WHERE id=?',(tid,))
            c.execute('UPDATE thread SET booking_context=? WHERE id=?',(dump(r.get('bookingData',{})),tid))
            r['remaining']=remaining(c,getw(c,ws));r['demo']=not bool(ai.KEY);record_usage(c,ws,'chat',ai.CHAT,r);c.execute('UPDATE request SET state=\'done\',result=? WHERE ws=? AND thread=? AND client=?',(dump(r),*key))
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Chat persistence failed')
        try:replay=abort_chat_request(key,p,kind)
        except Exception:fail(503,'상담 저장 및 사용량 정산을 확인하지 못했습니다. 관리자 확인이 필요합니다.')
        if replay is not None:return replay
        fail(502,'상담 저장 실패. 사용량은 복구되었습니다.')
    return r
@app.get('/api/inbox')
def inbox(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);cutoff=history_cutoff(w)
        return rows(c,'SELECT id,kind,status,manual,created,(SELECT body FROM message WHERE ws=thread_outer.ws AND thread=thread_outer.id AND created>=? ORDER BY rowid DESC LIMIT 1) AS last FROM thread AS thread_outer WHERE ws=? AND (created>=? OR EXISTS(SELECT 1 FROM message m WHERE m.ws=thread_outer.ws AND m.thread=thread_outer.id AND m.created>=?)) ORDER BY created DESC',(cutoff,ws,cutoff,cutoff))
@app.get('/api/history-policy')
def history_policy(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);cutoff=history_cutoff(w)
        hidden=one(c,'SELECT COUNT(*) n FROM thread t WHERE t.ws=? AND t.created<? AND NOT EXISTS(SELECT 1 FROM message m WHERE m.ws=t.ws AND m.thread=t.id AND m.created>=?)',(ws,cutoff,cutoff))['n']
        return {'base_days':BASE_HISTORY_DAYS,'extended_days':EXTENDED_HISTORY_DAYS,'accessible_days':history_days(w),'older_threads':hidden,'deletion_enabled':False,'policy':'provisional_access_window'}
@app.get('/api/inbox/{i}')
def thread_detail(i:str,ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);t=one(c,'SELECT id,kind,status,manual FROM thread WHERE ws=? AND id=?',(ws,i));require(t and thread_accessible(c,w,i),'상담 없음 또는 보관 조회 범위 초과',404);return t|{'messages':rows(c,'SELECT role,body,created FROM message WHERE ws=? AND thread=? AND created>=? ORDER BY rowid',(ws,i,history_cutoff(w)))}
@app.post('/api/inbox/{i}')
def thread_update(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        t=one(c,'SELECT * FROM thread WHERE ws=? AND id=?',(ws,i));require(t and thread_accessible(c,getw(c,ws),i),'상담 없음 또는 보관 조회 범위 초과',404)
        if 'manual' in body:c.execute('UPDATE thread SET manual=? WHERE id=?',(int(bool(body['manual'])),i))
        if body.get('status') in ['open','pending','resolved']:c.execute('UPDATE thread SET status=? WHERE id=?',(body['status'],i))
        if body.get('reply'):c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,i,'staff',bounded(body['reply']),now()))
    return {'ok':True}
@app.get('/api/unknown')
def unknown(ws=Depends(ident)):
    with db() as c:return rows(c,'SELECT id,thread,q,status,created FROM unknown WHERE ws=? ORDER BY created DESC',(ws,))
@app.get('/api/qr')
def qr(ws=Depends(ident)):
    with db() as c:w=getw(c,ws);require(public_access(w),'유료 구독 또는 초청 체험 필요');url=APP_URL+'/c/'+w['slug']
    b=io.BytesIO();qrcode.make(url).save(b,format='PNG');return Response(b.getvalue(),media_type='image/png')

def interval(s,start):
    try:
        d=datetime.fromisoformat(start);require(d.tzinfo is None,'업체 현지 시간을 입력하세요.',422);d=d.replace(tzinfo=ZoneInfo(s['timezone']));end=d+timedelta(minutes=s['duration']);endbuf=end+timedelta(minutes=s['buffer'])
        require(d>datetime.now(timezone.utc) and d.weekday() not in s['closed_days'] and d.strftime('%H:%M')>=s['open'] and endbuf.date()==d.date() and endbuf.strftime('%H:%M')<=s['close'],'예약 가능한 시간이 아닙니다.',409)
        return d.astimezone(timezone.utc).isoformat(),end.astimezone(timezone.utc).isoformat()
    except HTTPException:raise
    except Exception:fail(422,'일시 형식 오류')
def resource_id(s,body):
    k=body.get('resource','default');require(k in [r['id'] for r in s.get('resources',[{'id':'default','name':'기본 담당자'}])],'담당자 선택 오류',422);return k
def available(c,ws,start,end,exclude='',buffer=0,resource='default'):
    t0=(datetime.fromisoformat(start)-timedelta(minutes=buffer)).isoformat();t1=(datetime.fromisoformat(end)+timedelta(minutes=buffer)).isoformat()
    return not one(c,'SELECT id FROM booking WHERE ws=? AND resource=? AND status=\'confirmed\' AND start<? AND end>? AND id<>?',(ws,resource,t1,t0,exclude)) and not google_calendar.busy_conflict(c,ws,t0,t1)
def validate_fields(s,data):
    require(isinstance(data,dict),'양식 오류',422);out={}
    for f in s['fields']:
        x=data.get(f['key'],'');require(not f['required'] or str(x).strip()!='','필수 항목: '+f['label'],422)
        if x=='':continue
        x=bounded(str(x),1000)
        if f['type']=='number':require(x.isdigit() and 0<int(x)<=100000,'숫자 형식: '+f['label'],422)
        if f['type']=='phone':require(bool(re.fullmatch(r'[+\d ()-]{7,25}',x)),'연락처 형식 오류',422)
        if f['type']=='select':require(x in f.get('options',[]),'선택값 오류',422)
        if f['type']=='boolean':require(x in ['예','아니오'],'선택값 오류',422)
        if f['type']=='date':
            try:datetime.strptime(x,'%Y-%m-%d')
            except ValueError:fail(422,'날짜 형식 오류')
        if f['type']=='time':require(bool(re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',x)),'시간 형식 오류',422)
        out[f['key']]=x
    return out
def booking_view(b,secret=False):
    r={k:b[k] for k in ['id','start','end','status','customer_ok','paid','version','resource']};r['payload']=loads(b['payload']);r['fields']=loads(b['fields'])
    if secret:r['token']=b['token']
    return r
@app.get('/api/booking/form/{token}')
def form(token:str):
    with db() as c:
        v=visitor(c,token);w=getw(c,v['ws']);s=loads(w['settings']);require('calendar' in entitlements(w) and s['modes'].get('booking')!='off' and (v['kind']=='test' or w['enabled']));return {k:s[k] for k in ['fields','template_version','timezone','duration','open','close','payment_required']}|{'resources':s.get('resources',[{'id':'default','name':'기본 담당자'}])}
@app.post('/api/booking/availability')
def availability(body:dict):
    with db() as c:
        v=visitor(c,body.get('token',''));w=getw(c,v['ws']);require('calendar' in entitlements(w) and (v['kind']=='test' or w['enabled']));s=loads(w['settings'])
        try:date=datetime.strptime(body['date'],'%Y-%m-%d').date()
        except Exception:fail(422,'날짜 형식 오류')
        resource=resource_id(s,body);start=datetime.fromisoformat(f'{date}T{s["open"]}');close=datetime.fromisoformat(f'{date}T{s["close"]}');out=[]
        while start+timedelta(minutes=s['duration']+s['buffer'])<=close:
            try:a,b=interval(s,start.isoformat());
            except HTTPException:start+=timedelta(minutes=30);continue
            if available(c,v['ws'],a,b,buffer=s['buffer'],resource=resource):out.append(start.strftime('%H:%M'))
            start+=timedelta(minutes=30)
        return out
@app.post('/api/booking/draft')
def draft(body:dict):
    with db(True) as c:
        v=visitor(c,body.get('token',''));w=getw(c,v['ws']);s=loads(w['settings']);t=trial(c,w);require('calendar' in entitlements(w) and s['modes'].get('booking')!='off' and (v['kind']=='test' or w['enabled']));require(v['kind']=='public','관리자 테스트에서는 실제 예약을 생성하지 않습니다.',409)
        if t:require(trial_bookings_remaining(c,w)>0,'초청 체험 예약 한도를 모두 사용했습니다.',402)
        require(body.get('version')==s['template_version'],'양식 변경됨. 다시 확인하세요.',409);data=validate_fields(s,body.get('payload',{}));resource=resource_id(s,body);a,b=interval(s,body.get('start',''));require(available(c,v['ws'],a,b,buffer=s['buffer'],resource=resource),'선택한 시간이 이미 예약되었습니다.',409);i=uid();t=uid();c.execute("UPDATE booking SET status='superseded' WHERE ws=? AND visitor=? AND status='draft'",(v['ws'],v['token']));c.execute('INSERT INTO booking VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,v['ws'],v['token'],a,b,resource,dump(data),s['template_version'],dump(s['fields']),'draft',0,0,t,now()));return booking_view(one(c,'SELECT * FROM booking WHERE id=?',(i,)),True)
@app.post('/api/booking/{i}/confirm')
def confirm(i:str,body:dict):
    with db(True) as c:
        v=visitor(c,body.get('token',''));w=getw(c,v['ws']);s=loads(w['settings']);b=one(c,'SELECT * FROM booking WHERE id=? AND ws=? AND visitor=?',(i,v['ws'],v['token']));require(b and secrets.compare_digest(b['token'],str(body.get('confirmation',''))),'예약 확인 권한 없음');require('calendar' in entitlements(w) and w['enabled'] and s['modes'].get('booking')!='off')
        require(b['status']!='superseded','이전 양식은 변경되었습니다. 최신 양식을 확인하세요.',409)
        if b['status']!='draft':return booking_view(b)
        if trial(c,w):require(trial_bookings_remaining(c,w)>0,'초청 체험 예약 한도를 모두 사용했습니다.',402)
        require(b['version']==s['template_version'] and b['created']>now()-1800,'예약 정보 만료 또는 양식 변경',409);require(available(c,v['ws'],b['start'],b['end'],buffer=s['buffer'],resource=b['resource']),'다른 고객이 먼저 예약했습니다.',409);require(datetime.fromisoformat(b['start'])>datetime.now(timezone.utc),'지난 일정은 확정할 수 없습니다.',409)
        status='pending_payment' if s['payment_required'] else 'confirmed' if s['modes'].get('booking')=='auto' and 'auto_booking' in entitlements(w) else 'pending'
        c.execute('UPDATE booking SET customer_ok=1,status=? WHERE id=?',(status,i));ops.event(c,v['ws'],'booking','예약 '+('확정' if status=='confirmed' else '확인 요청'),i);c.execute("UPDATE thread SET booking_context='{}' WHERE ws=? AND visitor=?",(v['ws'],v['token']));return booking_view(one(c,'SELECT * FROM booking WHERE id=?',(i,)))
@app.get('/api/bookings')
def bookings(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);require('calendar' in entitlements(w));return [booking_view(b) for b in rows(c,'SELECT * FROM booking WHERE ws=? AND status NOT IN (\'draft\',\'superseded\') ORDER BY start',(ws,))]
@app.post('/api/bookings')
def manual_booking(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);s=loads(w['settings']);require('calendar' in entitlements(w));
        if trial(c,w):require(trial_bookings_remaining(c,w)>0,'초청 체험 예약 한도를 모두 사용했습니다.',402)
        data=validate_fields(s,body.get('payload',{}));resource=resource_id(s,body);a,b=interval(s,body.get('start',''));require(available(c,ws,a,b,buffer=s['buffer'],resource=resource),'예약 시간이 겹칩니다.',409);i=uid();paid=bool(body.get('paid',False));status='pending_payment' if s['payment_required'] and not paid else 'confirmed';c.execute('INSERT INTO booking VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,'staff',a,b,resource,dump(data),s['template_version'],dump(s['fields']),status,1,int(paid),uid(),now()));ops.event(c,ws,'booking','관리자 예약 등록',i);return booking_view(one(c,'SELECT * FROM booking WHERE id=?',(i,)))
@app.post('/api/bookings/{i}')
def booking_admin(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);s=loads(w['settings']);require('calendar' in entitlements(w));b=one(c,'SELECT * FROM booking WHERE id=? AND ws=?',(i,ws));require(b,'일정 없음',404);act=body.get('action')
        if act=='approve':
            require(b['status'] in ['pending','pending_payment'] and b['customer_ok'],'확정할 수 없는 일정',409);require(b['version']==s['template_version'],'양식 또는 정책 변경. 신규 예약 요청 필요.',409);paid=bool(b['paid'] or body.get('paid'));require(not s['payment_required'] or paid,'결제 확인 필요',409);require(available(c,ws,b['start'],b['end'],i,s['buffer'],b['resource']) and datetime.fromisoformat(b['start'])>datetime.now(timezone.utc),'예약 시간 충돌 또는 만료',409);c.execute('UPDATE booking SET paid=?,status=\'confirmed\' WHERE id=?',(int(paid),i));ops.event(c,ws,'booking','예약 확정',i)
        elif act=='cancel':require(b['status'] in ['confirmed','pending','pending_payment'],'취소 불가',409);c.execute('UPDATE booking SET status=\'cancelled\' WHERE id=?',(i,));ops.event(c,ws,'booking','관리자 예약 취소',i)
        elif act=='complete':require(b['status']=='confirmed','확정 일정만 완료 가능',409);c.execute('UPDATE booking SET status=\'completed\' WHERE id=?',(i,));ops.event(c,ws,'booking','예약 완료',i)
        elif act=='change':
            require('change_booking' in entitlements(w));require(b['status']=='confirmed','확정 일정만 변경',409);a,z=interval(s,body.get('start',''));require(available(c,ws,a,z,i,s['buffer'],b['resource']),'일정 충돌',409);c.execute('UPDATE booking SET start=?,end=? WHERE id=?',(a,z,i));ops.event(c,ws,'booking','관리자 예약 변경',i)
        else:fail(422,'업무 유형 오류')
        return booking_view(one(c,'SELECT * FROM booking WHERE id=?',(i,)))
@app.get('/api/work')
def work_list(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);a=entitlements(w);return [r for r in rows(c,'SELECT * FROM work WHERE ws=? ORDER BY created DESC',(ws,)) if r['kind'] in a]
@app.post('/api/work')
def work_add(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);k=body.get('kind');require(k in ['crm','quote','tasks','leads','complaints'] and k in entitlements(w));c.execute('INSERT INTO work VALUES(?,?,?,?,?,?,?)',(uid(),ws,k,bounded(body.get('title',''),200),bounded(body.get('details',''),2000),'open',now()))
    return {'ok':True}
@app.post('/api/work/{i}')
def work_done(i:str,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);r=one(c,'SELECT * FROM work WHERE ws=? AND id=?',(ws,i));require(r and r['kind'] in entitlements(w));c.execute('UPDATE work SET status=\'resolved\' WHERE id=?',(i,))
    return {'ok':True}
@app.get('/api/stats')
def stats(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);require('stats' in entitlements(w));return {'threads':one(c,'SELECT count(*) n FROM thread WHERE ws=?',(ws,))['n'],'unknown':one(c,'SELECT count(*) n FROM unknown WHERE ws=? AND status=\'open\'',(ws,))['n'],'messages':one(c,'SELECT count(*) n FROM message WHERE ws=?',(ws,))['n'],'remaining':remaining(c,w)}
@app.get('/api/export')
def export(ws=Depends(ident)):
    from openpyxl import Workbook
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    def safe(v):
        if not isinstance(v,str):return v
        v=ILLEGAL_CHARACTERS_RE.sub('',v)[:32760]
        return "'"+v if v.lstrip().startswith(('=','+','-','@')) else v
    def add_sheet(book,name,headers,records):
        sheet=book.create_sheet(name);sheet.append(headers)
        for row in records:sheet.append([safe(x) for x in row])
        sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
    b=Workbook();b.remove(b.active)
    with db() as c:
        w=getw(c,ws);a=entitlements(w);require('export' in a)
        rr=rows(c,'SELECT m.thread,m.role,m.body,m.created FROM message m JOIN thread t ON t.id=m.thread AND t.ws=m.ws WHERE m.ws=? AND t.kind<>? AND m.created>=? ORDER BY m.created',(ws,'test',history_cutoff(w)))
        require(len(rr)<=50000,'상담 기록이 너무 많습니다. 관리자에게 문의하세요.',422)
        add_sheet(b,'상담 기록',['상담 ID','역할','본문','일시 UTC'],[(r['thread'],r['role'],r['body'],datetime.fromtimestamp(r['created'],timezone.utc).isoformat()) for r in rr])
        if 'crm' in a:
            contacts=rows(c,'SELECT id,name,email,phone,notes FROM crm_contact WHERE ws=? ORDER BY updated DESC',(ws,))
            add_sheet(b,'고객',['고객 ID','이름','이메일','전화번호','메모'],[tuple(r[k] for k in ('id','name','email','phone','notes')) for r in contacts])
        if 'calendar' in a:
            reservations=rows(c,"SELECT id,start,end,status FROM booking WHERE ws=? AND status NOT IN ('draft','superseded') ORDER BY start",(ws,))
            add_sheet(b,'예약',['예약 ID','시작 UTC','종료 UTC','상태'],[tuple(r[k] for k in ('id','start','end','status')) for r in reservations])
        work=rows(c,'SELECT kind,title,details,status FROM work WHERE ws=? ORDER BY created',(ws,))
        add_sheet(b,'업무',['구분','제목','내용','상태'],[tuple(r[k] for k in ('kind','title','details','status')) for r in work if r['kind'] in a])
    o=io.BytesIO();b.save(o);return Response(o.getvalue(),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename=consultations.xlsx'})
@app.get('/widget/{slug}')
def widget(slug:str):
    with db() as c:
        w,agent=branding.resolve(c,slug);require(w and w['enabled'] and 'widget' in entitlements(w),'위젯 비활성화',404)
    return FileResponse(ROOT/'web/index.html')
@app.get('/invite/{code}')
def invite_redirect(code:str):
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]{20,100}',code)),'잘못된 초청 링크',404);return RedirectResponse('/#invite='+code)
@app.get('/')
@app.get('/c/{slug}')
def index(slug:str=''):return FileResponse(ROOT/'web/index.html')

# Operational endpoints are registered after the original routes.
import ops
import billing
import google_calendar
import channel_live
import branding
import recovery
import developer_api
import education_url
import customer_ops
import reporting
import push_notifications
import domains
import message_notifications
import custom_integration

# Optional one-process worker for the development container. Disabled unless configured.
_worker_stop=None
_worker_thread=None
@app.on_event('startup')
def start_background_worker():
    global _worker_stop,_worker_thread
    if os.getenv('ENABLE_BACKGROUND_WORKER')!='1' or (_worker_thread and _worker_thread.is_alive()):return
    import worker
    _worker_stop=threading.Event();_worker_thread=threading.Thread(target=worker.loop,args=(_worker_stop,),name='csai-worker',daemon=True);_worker_thread.start()
@app.on_event('shutdown')
def stop_background_worker():
    if _worker_stop:_worker_stop.set()
    if _worker_thread:_worker_thread.join(timeout=2)

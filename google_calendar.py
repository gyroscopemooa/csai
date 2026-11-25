"""Google Calendar OAuth and explicit per-booking sync; never deletes unrelated events.
Only writes booking time and a generic title, not customer data. No real account in tests.
"""
from fastapi import Depends,Request
from fastapi.responses import RedirectResponse
from app import app,ident,require,fail,bounded
from store import *
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlencode,quote
import hashlib,httpx
from cryptography.fernet import Fernet,InvalidToken
SCOPE='https://www.googleapis.com/auth/calendar.events'
BASE='https://www.googleapis.com/calendar/v3/calendars/'

def init_gc():
    with db(True) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS calendar_oauth(state TEXT PRIMARY KEY,ws TEXT NOT NULL,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS calendar_link(ws TEXT PRIMARY KEY,secret TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS calendar_sync(ws TEXT NOT NULL,booking TEXT NOT NULL,status TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,booking));
        CREATE TABLE IF NOT EXISTS calendar_policy(ws TEXT PRIMARY KEY,auto_sync INTEGER NOT NULL DEFAULT 0,block_busy INTEGER NOT NULL DEFAULT 0,refreshed INTEGER NOT NULL DEFAULT 0,horizon INTEGER NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS calendar_busy(ws TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS calendar_busy_range ON calendar_busy(ws,start,end);
        CREATE TABLE IF NOT EXISTS calendar_revision(ws TEXT NOT NULL,booking TEXT NOT NULL,fingerprint TEXT NOT NULL,attempted INTEGER NOT NULL,error TEXT NOT NULL DEFAULT '',PRIMARY KEY(ws,booking));
        ''')
init_gc()
def encryption():
    try:return Fernet(os.environ['INTEGRATION_ENCRYPTION_KEY'].encode())
    except Exception:fail(503,'INTEGRATION_ENCRYPTION_KEY 설정 필요')
def configured():return bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET') and os.getenv('INTEGRATION_ENCRYPTION_KEY'))
def permission(c,ws):require('google_calendar' in entitlements(getw(c,ws)))
def callback_url():return APP_URL+'/auth/calendar/callback'
def token_exchange(data):
    try:r=httpx.post('https://oauth2.googleapis.com/token',data={'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET'],**data},timeout=15);require(r.is_success,'Google 캘린더 인증 실패',502);return r.json()
    except httpx.HTTPError:fail(502,'Google 캘린더 인증 연결 실패')
def access(ws):
    require(configured(),'Google Calendar 환경변수 미설정',503)
    with db() as c:permission(c,ws);l=one(c,'SELECT * FROM calendar_link WHERE ws=?',(ws,));require(l,'캘린더 연결 필요',409)
    try:refresh=encryption().decrypt(l['secret'].encode()).decode()
    except InvalidToken:fail(503,'저장 키가 변경되었습니다. 다시 연결하세요.')
    t=token_exchange({'grant_type':'refresh_token','refresh_token':refresh});require(t.get('access_token'),'Google 토큰 없음',502);return t['access_token']
@app.get('/api/integrations/calendar')
def status(ws=Depends(ident)):
    with db() as c:permission(c,ws);return {'configured':configured(),'connected':bool(one(c,'SELECT ws FROM calendar_link WHERE ws=?',(ws,))),'sync':rows(c,'SELECT booking,status,updated FROM calendar_sync WHERE ws=?',(ws,)),'policy':policy(c,ws),'worker_enabled':os.getenv('ENABLE_AUTO_CALENDAR')=='1','errors':rows(c,"SELECT booking,error FROM calendar_revision WHERE ws=? AND error<>''",(ws,))}
@app.get('/auth/calendar/connect')
def connect(ws=Depends(ident)):
    require(configured(),'Google Calendar 환경변수 미설정',503);encryption();st=uid()
    with db(True) as c:permission(c,ws);c.execute('INSERT INTO calendar_oauth VALUES(?,?,?)',(st,ws,now()+600))
    return RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':os.environ['GOOGLE_CLIENT_ID'],'redirect_uri':callback_url(),'response_type':'code','scope':SCOPE,'access_type':'offline','prompt':'consent','state':st}))
@app.get('/auth/calendar/callback')
def callback(code:str,state:str,ws=Depends(ident)):
    with db(True) as c:
        permission(c,ws);require(one(c,'SELECT * FROM calendar_oauth WHERE ws=? AND state=? AND expires>?',(ws,state,now())),'캘린더 인증 상태 오류');c.execute('DELETE FROM calendar_oauth WHERE state=?',(state,))
    t=token_exchange({'code':code,'redirect_uri':callback_url(),'grant_type':'authorization_code'});require(t.get('refresh_token'),'오프라인 연결 권한 필요',409);secret=encryption().encrypt(t['refresh_token'].encode()).decode()
    with db(True) as c:c.execute('INSERT INTO calendar_link VALUES(?,?,?) ON CONFLICT(ws) DO UPDATE SET secret=excluded.secret,created=excluded.created',(ws,secret,now()));c.execute('DELETE FROM calendar_busy WHERE ws=?',(ws,));c.execute('DELETE FROM calendar_revision WHERE ws=?',(ws,));c.execute("UPDATE calendar_policy SET refreshed=0,horizon=0,error='' WHERE ws=?",(ws,))
    return RedirectResponse('/#channels',303)
@app.post('/api/integrations/calendar/disconnect')
def disconnect(ws=Depends(ident)):
    # Disconnect is available even after downgrade. No remote events deleted.
    with db(True) as c:c.execute('DELETE FROM calendar_link WHERE ws=?',(ws,));c.execute('DELETE FROM calendar_oauth WHERE ws=?',(ws,));c.execute('DELETE FROM calendar_policy WHERE ws=?',(ws,));c.execute('DELETE FROM calendar_busy WHERE ws=?',(ws,));c.execute('DELETE FROM calendar_revision WHERE ws=?',(ws,))
    return {'ok':True}
def event_id(ws,b):return hashlib.sha256((ws+':'+b).encode()).hexdigest()
def api(method,path,token,**kwargs):
    try:return httpx.request(method,BASE+'primary/events'+path,headers={'Authorization':'Bearer '+token},timeout=15,**kwargs)
    except httpx.HTTPError:fail(502,'Google 캘린더 요청 실패')
@app.post('/api/integrations/calendar/sync/{i}')
def sync(i:str,ws=Depends(ident)):
    with db() as c:permission(c,ws);b=one(c,'SELECT * FROM booking WHERE id=? AND ws=?',(i,ws));require(b and b['status'] in ['confirmed','completed','cancelled'],'동기화 가능한 일정 없음',404)
    token=access(ws);eid=event_id(ws,i);marker={'csai_workspace':ws,'csai_booking':i};data={'summary':'CS AI 예약','start':{'dateTime':b['start']},'end':{'dateTime':b['end']},'extendedProperties':{'private':marker},'visibility':'private'};existing=api('GET','/'+eid,token)
    if existing.status_code==200:
        require(all(existing.json().get('extendedProperties',{}).get('private',{}).get(k)==v for k,v in marker.items()),'다른 일정과 충돌: 수정하지 않음',409)
        if b['status']=='cancelled':r=api('DELETE','/'+eid,token,params={'sendUpdates':'none'});require(r.status_code in (204,404,410),'캘린더 삭제 실패',502)
        else:r=api('PATCH','/'+eid,token,json=data,params={'sendUpdates':'none'});require(r.is_success,'캘린더 수정 실패',502)
    elif existing.status_code in (404,410):
        if b['status']!='cancelled':r=api('POST','',token,json={'id':eid,**data},params={'sendUpdates':'none'});require(r.is_success,'캘린더 등록 실패 또는 기존 삭제 이벤트 충돌',502)
    else:fail(502,'캘린더 일정 조회 실패')
    state='deleted' if b['status']=='cancelled' else 'synced'
    with db(True) as c:
        c.execute('INSERT INTO calendar_sync VALUES(?,?,?,?) ON CONFLICT(ws,booking) DO UPDATE SET status=excluded.status,updated=excluded.updated',(ws,i,state,now()))
        c.execute("INSERT INTO calendar_revision VALUES(?,?,?,?,?) ON CONFLICT(ws,booking) DO UPDATE SET fingerprint=excluded.fingerprint,attempted=excluded.attempted,error=excluded.error",(ws,i,fingerprint(b),now(),''))
    return {'status':state}
@app.get('/api/integrations/calendar/preview')
def preview(ws=Depends(ident)):
    token=access(ws);r=api('GET','',token,params={'timeMin':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'singleEvents':'true','orderBy':'startTime','maxResults':50});require(r.is_success,'캘린더 일정 조회 실패',502)
    # Only return time ranges, not external private titles or attendees.
    return [{'start':x.get('start',{}),'end':x.get('end',{}),'owned':x.get('extendedProperties',{}).get('private',{}).get('csai_workspace')==ws} for x in r.json().get('items',[]) if x.get('status')!='cancelled']

# External busy intervals are a bounded snapshot, never used to overwrite CS AI bookings.
FRESH_SECONDS=300
HORIZON_DAYS=90

def policy(c,ws):
    return one(c,'SELECT auto_sync,block_busy,refreshed,horizon,error FROM calendar_policy WHERE ws=?',(ws,)) or {'auto_sync':0,'block_busy':0,'refreshed':0,'horizon':0,'error':''}

def fingerprint(b):
    return hashlib.sha256(dump([b['start'],b['end'],b['status']]).encode()).hexdigest()

def busy_conflict(c,ws,start,end):
    w=getw(c,ws)
    if 'google_calendar' not in entitlements(w):return False
    p=policy(c,ws)
    if not p['block_busy']:return False
    require(p['refreshed']>=now()-FRESH_SECONDS and p['horizon']>=datetime.fromisoformat(end).timestamp(),'외부 일정 확인이 필요합니다. 잠시 후 다시 시도하세요.',503)
    return bool(one(c,'SELECT start FROM calendar_busy WHERE ws=? AND start<? AND end>? LIMIT 1',(ws,end,start)))

def event_time(value,zone):
    if value.get('dateTime'):
        d=datetime.fromisoformat(value['dateTime'].replace('Z','+00:00'))
        require(d.tzinfo is not None,'외부 일정 시간대 없음',502)
    else:d=datetime.fromisoformat(value['date']).replace(tzinfo=ZoneInfo(value.get('timeZone') or zone))
    return d.astimezone(timezone.utc).isoformat()

def refresh_busy(ws):
    with db() as c:
        permission(c,ws);link=one(c,'SELECT secret FROM calendar_link WHERE ws=?',(ws,));require(link,'캘린더 연결 필요',409);zone=loads(getw(c,ws)['settings'])['timezone']
    token=access(ws);begin=datetime.now(timezone.utc)-timedelta(days=1);horizon=datetime.now(timezone.utc)+timedelta(days=HORIZON_DAYS);found=[];page=None
    for _ in range(20):
        params={'timeMin':begin.isoformat(),'timeMax':horizon.isoformat(),'singleEvents':'true','showDeleted':'false','maxResults':250}
        if page:params['pageToken']=page
        r=api('GET','',token,params=params);require(r.is_success,'외부 일정 조회 실패',502);data=r.json();calendar_zone=data.get('timeZone') or zone
        for item in data.get('items',[]):
            if item.get('status')=='cancelled' or item.get('transparency')=='transparent':continue
            marker=item.get('extendedProperties',{}).get('private',{});bid=marker.get('csai_booking','')
            if marker.get('csai_workspace')==ws and bid and item.get('id')==event_id(ws,bid):continue
            a=event_time(item['start'],calendar_zone);b=event_time(item['end'],calendar_zone)
            if a<b:found.append((ws,a,b))
        page=data.get('nextPageToken')
        if not page:break
    require(not page,'외부 일정 수집 한도 초과',503)
    with db(True) as c:
        permission(c,ws);current=one(c,'SELECT secret FROM calendar_link WHERE ws=?',(ws,));require(current and current['secret']==link['secret'],'캘린더 연결 변경',409)
        c.execute('DELETE FROM calendar_busy WHERE ws=?',(ws,));c.executemany('INSERT INTO calendar_busy VALUES(?,?,?)',found)
        c.execute("INSERT INTO calendar_policy(ws,refreshed,horizon) VALUES(?,?,?) ON CONFLICT(ws) DO UPDATE SET refreshed=excluded.refreshed,horizon=excluded.horizon,error=''",(ws,now(),int(horizon.timestamp())))
    return {'count':len(found),'horizon':int(horizon.timestamp())}

@app.post('/api/integrations/calendar/policy')
def set_policy(body:dict,ws=Depends(ident)):
    auto=body.get('auto_sync') is True;block=body.get('block_busy') is True
    with db() as c:permission(c,ws);require(one(c,'SELECT ws FROM calendar_link WHERE ws=?',(ws,)),'캘린더 연결 필요',409)
    if block:refresh_busy(ws)
    with db(True) as c:
        permission(c,ws);require(one(c,'SELECT ws FROM calendar_link WHERE ws=?',(ws,)),'캘린더 연결 필요',409)
        c.execute('INSERT INTO calendar_policy(ws,auto_sync,block_busy) VALUES(?,?,?) ON CONFLICT(ws) DO UPDATE SET auto_sync=excluded.auto_sync,block_busy=excluded.block_busy',(ws,int(auto),int(block)))
    return {'ok':True}

@app.post('/api/integrations/calendar/refresh')
def refresh_endpoint(ws=Depends(ident)):return refresh_busy(ws)

def tick():
    if os.getenv('ENABLE_AUTO_CALENDAR')!='1':return 0
    with db() as c:targets=rows(c,'SELECT p.* FROM calendar_policy p JOIN calendar_link l ON l.ws=p.ws WHERE p.auto_sync=1 OR p.block_busy=1')
    done=0
    for p in targets:
        ws=p['ws']
        with db() as c:
            w=getw(c,ws)
            if not w or 'google_calendar' not in entitlements(w):continue
        if p['block_busy'] and p['refreshed']<now()-120:
            try:refresh_busy(ws);done+=1
            except Exception:
                with db(True) as c:c.execute('UPDATE calendar_policy SET error=? WHERE ws=?',('외부 일정 새로고침 실패',ws))
        if not p['auto_sync']:continue
        with db() as c:
            candidates=rows(c,"SELECT b.*,r.fingerprint,r.attempted,r.error FROM booking b LEFT JOIN calendar_revision r ON r.ws=b.ws AND r.booking=b.id WHERE b.ws=? AND b.status IN ('confirmed','completed','cancelled') AND (b.end>=? OR r.booking IS NOT NULL) ORDER BY b.created DESC LIMIT 500",(ws,datetime.now(timezone.utc).isoformat()))
        pending=[b for b in candidates if b['fingerprint']!=fingerprint(b) or b['error']]
        for b in pending[:10]:
            if b['attempted'] and b['error'] and b['attempted']>now()-120:continue
            # Stable event IDs make retries idempotent. Only one worker should run per database.
            try:sync(b['id'],ws=ws);done+=1
            except Exception:
                with db(True) as c:c.execute('INSERT INTO calendar_revision VALUES(?,?,?,?,?) ON CONFLICT(ws,booking) DO UPDATE SET fingerprint=excluded.fingerprint,attempted=excluded.attempted,error=excluded.error',(ws,b['id'],fingerprint(b),now(),'동기화 실패; 재시도 예정'))
    return done

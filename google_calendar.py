"""Google Calendar OAuth and explicit per-booking sync; never deletes unrelated events.
Only writes booking time and a generic title, not customer data. No real account in tests.
"""
from fastapi import Depends,Request
from fastapi.responses import RedirectResponse
from app import app,ident,require,fail,bounded
from store import *
from datetime import datetime,timezone
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
    with db() as c:permission(c,ws);return {'configured':configured(),'connected':bool(one(c,'SELECT ws FROM calendar_link WHERE ws=?',(ws,))),'sync':rows(c,'SELECT booking,status,updated FROM calendar_sync WHERE ws=?',(ws,))}
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
    with db(True) as c:c.execute('INSERT INTO calendar_link VALUES(?,?,?) ON CONFLICT(ws) DO UPDATE SET secret=excluded.secret,created=excluded.created',(ws,secret,now()))
    return RedirectResponse('/#channels',303)
@app.post('/api/integrations/calendar/disconnect')
def disconnect(ws=Depends(ident)):
    # Disconnect is available even after downgrade. No remote events deleted.
    with db(True) as c:c.execute('DELETE FROM calendar_link WHERE ws=?',(ws,));c.execute('DELETE FROM calendar_oauth WHERE ws=?',(ws,))
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
    with db(True) as c:c.execute('INSERT INTO calendar_sync VALUES(?,?,?,?) ON CONFLICT(ws,booking) DO UPDATE SET status=excluded.status,updated=excluded.updated',(ws,i,state,now()))
    return {'status':state}
@app.get('/api/integrations/calendar/preview')
def preview(ws=Depends(ident)):
    token=access(ws);r=api('GET','',token,params={'timeMin':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'singleEvents':'true','orderBy':'startTime','maxResults':50});require(r.is_success,'캘린더 일정 조회 실패',502)
    # Only return time ranges, not external private titles or attendees.
    return [{'start':x.get('start',{}),'end':x.get('end',{}),'owned':x.get('extendedProperties',{}).get('private',{}).get('csai_workspace')==ws} for x in r.json().get('items',[]) if x.get('status')!='cancelled']

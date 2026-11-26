"""Operational workflows. Imported after app routes; no external side effects on import."""
from app import app, ident, require, fail, bounded, visitor, available, interval, booking_view, validate_fields, chat
from fastapi import Depends
from store import *
from datetime import datetime, timezone
import re, hashlib, httpx
from integrations.channels import naver_in, naver_out, kakao_in, kakao_out

def init_ops():
    with db(True) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS booking_change(id TEXT PRIMARY KEY,ws TEXT NOT NULL,booking TEXT NOT NULL,visitor TEXT NOT NULL,action TEXT NOT NULL,start TEXT,end TEXT,original_start TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS knowledge_version(id TEXT PRIMARY KEY,ws TEXT NOT NULL,content TEXT NOT NULL,created INTEGER NOT NULL,label TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS event_log(id TEXT PRIMARY KEY,ws TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL,ref TEXT NOT NULL,seen INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS notification_config(ws TEXT PRIMARY KEY,email TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS delivery(id TEXT PRIMARY KEY,ws TEXT NOT NULL,event TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL,UNIQUE(ws,event));
        CREATE TABLE IF NOT EXISTS channel_session(ws TEXT NOT NULL,channel TEXT NOT NULL,external_user TEXT NOT NULL,token TEXT NOT NULL,PRIMARY KEY(ws,channel,external_user));
        CREATE TABLE IF NOT EXISTS work_link(ws TEXT NOT NULL,thread TEXT NOT NULL,kind TEXT NOT NULL,work TEXT NOT NULL,PRIMARY KEY(ws,thread,kind));
        ''')
init_ops()

def event(c,ws,kind,title,ref):
    c.execute('INSERT INTO event_log VALUES(?,?,?,?,?,0,?)',(uid(),ws,kind,title,ref,now()))

def checkpoint(c,ws,label):
    w=getw(c,ws);c.execute('INSERT INTO knowledge_version VALUES(?,?,?,?,?)',(uid(),ws,w['published'],now(),label))

@app.get('/api/knowledge/versions')
def versions(ws=Depends(ident)):
    with db() as c:return rows(c,'SELECT id,created,label FROM knowledge_version WHERE ws=? ORDER BY rowid DESC LIMIT 100',(ws,))
@app.post('/api/knowledge/versions/{i}/restore')
def restore(i:str,ws=Depends(ident)):
    with db(True) as c:
        v=one(c,'SELECT * FROM knowledge_version WHERE ws=? AND id=?',(ws,i));require(v,'교육 버전 없음',404);checkpoint(c,ws,'복원 전 자동 백업');c.execute('UPDATE workspace SET published=? WHERE id=?',(v['content'],ws));event(c,ws,'education','교육 버전 복원',i)
    return {'ok':True}
@app.patch('/api/training/{i}/review')
def review(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        j=one(c,'SELECT * FROM training WHERE id=? AND ws=?',(i,ws));require(j and j['state']=='review','검토 중인 교육만 편집 가능',409)
        r=body.get('result');require(isinstance(r,dict),'형식 오류',422)
        for k in ['rules','faq','conflicts']:require(isinstance(r.get(k,[]),list) and len(r.get(k,[]))<=(200 if k=='faq' else 100),'교육 항목 오류',422)
        out={'style':bounded(r.get('style',''),1000),'rules':[bounded(x,1000) for x in r.get('rules',[])],'faq':[],'conflicts':[bounded(x,500) for x in r.get('conflicts',[])]}
        for f in r.get('faq',[]):
            require(isinstance(f,dict),'FAQ 오류',422);out['faq'].append({'q':bounded(f.get('q',''),500),'a':bounded(f.get('a',''),2000)})
        c.execute('UPDATE training SET result=? WHERE id=?',(dump(out),i))
    return {'ok':True}

@app.get('/api/events')
def events(ws=Depends(ident)):
    with db() as c:return rows(c,'SELECT * FROM event_log WHERE ws=? ORDER BY rowid DESC LIMIT 200',(ws,))
@app.post('/api/events/read')
def read_events(ws=Depends(ident)):
    with db(True) as c:c.execute('UPDATE event_log SET seen=1 WHERE ws=?',(ws,))
    return {'ok':True}

@app.get('/api/customer/bookings/{token}')
def own_bookings(token:str):
    with db() as c:
        v=visitor(c,token,kind='public');w=getw(c,v['ws']);require('calendar' in entitlements(w));a=entitlements(w);s=loads(w['settings']);bs=rows(c,"SELECT * FROM booking WHERE ws=? AND visitor=? AND status NOT IN ('draft','superseded') ORDER BY start",(v['ws'],token));return {'bookings':[booking_view(b) for b in bs],'canChange':'change_booking' in a and s['modes'].get('change')!='off','requests':rows(c,'SELECT id,booking,action,start,state FROM booking_change WHERE ws=? AND visitor=? ORDER BY created DESC',(v['ws'],token))}

def apply_change(c,b,r,s):
    require(b['status']=='confirmed' and b['start']==r['original_start'],'예약 상태가 변경되었습니다. 다시 요청하세요.',409)
    if r['action']=='cancel':c.execute("UPDATE booking SET status='cancelled' WHERE id=?",(b['id'],))
    else:
        require(datetime.fromisoformat(r['start'])>datetime.now(timezone.utc) and available(c,b['ws'],r['start'],r['end'],b['id'],s['buffer'],b['resource']),'변경 시간이 이미 예약되었거나 만료되었습니다.',409)
        c.execute('UPDATE booking SET start=?,end=? WHERE id=?',(r['start'],r['end'],b['id']))
    c.execute("UPDATE booking_change SET state='approved' WHERE id=?",(r['id'],))
    event(c,b['ws'],'booking','예약 '+('취소' if r['action']=='cancel' else '변경')+' 확정',b['id'])

@app.post('/api/customer/bookings/{i}/change')
def customer_change(i:str,body:dict):
    with db(True) as c:
        v=visitor(c,body.get('token',''),kind='public');ws=v['ws'];w=getw(c,ws);s=loads(w['settings']);require(w['enabled'] and 'change_booking' in entitlements(w) and s['modes'].get('change')!='off');b=one(c,'SELECT * FROM booking WHERE ws=? AND id=? AND visitor=?',(ws,i,v['token']));require(b and b['status']=='confirmed','변경 가능한 본인 예약 없음',404);require(datetime.fromisoformat(b['start'])>datetime.now(timezone.utc),'지난 예약은 변경할 수 없습니다.',409);require(body.get('confirmed') is True,'고객 최종 확인 필요',422)
        action=body.get('action');require(action in ['cancel','change'],'요청 유형 오류',422);a=z=None
        if action=='change':a,z=interval(s,body.get('start',''));require(available(c,ws,a,z,i,s['buffer'],b['resource']),'예약 시간 충돌',409)
        require(not one(c,"SELECT id FROM booking_change WHERE booking=? AND state='pending'",(i,)),'이미 승인 대기 중인 요청이 있습니다.',409)
        rid=uid();c.execute('INSERT INTO booking_change VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,ws,i,v['token'],action,a,z,b['start'],'pending',now()));r=one(c,'SELECT * FROM booking_change WHERE id=?',(rid,));event(c,ws,'booking','고객 예약 변경·취소 요청',i)
        # Paid/external bookings require staff review; never claim a refund.
        if s['modes'].get('change')=='auto' and not s['payment_required'] and not b['paid']:apply_change(c,b,r,s)
        return {'id':rid,'state':one(c,'SELECT state FROM booking_change WHERE id=?',(rid,))['state']}
@app.get('/api/booking-changes')
def changes(ws=Depends(ident)):
    with db() as c:
        require('change_booking' in entitlements(getw(c,ws)));return rows(c,'SELECT id,booking,action,start,state,created FROM booking_change WHERE ws=? ORDER BY rowid DESC',(ws,))
@app.post('/api/booking-changes/{i}')
def decide(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);require('change_booking' in entitlements(w));r=one(c,"SELECT * FROM booking_change WHERE ws=? AND id=? AND state='pending'",(ws,i));require(r,'승인 대기 요청 없음',404)
        if body.get('action')=='reject':c.execute("UPDATE booking_change SET state='rejected' WHERE id=?",(i,))
        elif body.get('action')=='approve':
            b=one(c,'SELECT * FROM booking WHERE ws=? AND id=?',(ws,r['booking']));require(b,'예약 없음',404);apply_change(c,b,r,loads(w['settings']))
        else:fail(422,'요청 유형 오류')
    return {'ok':True}

@app.post('/api/inbox/{i}/work')
def convert_work(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);k=body.get('kind');require(k in ['crm','quote','tasks','leads','complaints'] and k in entitlements(w));t=one(c,'SELECT id FROM thread WHERE ws=? AND id=?',(ws,i));require(t,'상담 없음',404)
        require(not one(c,'SELECT thread FROM demo_sample WHERE ws=? AND thread=?',(ws,i)),'샘플 상담은 업무로 등록할 수 없습니다.',409)
        existing=one(c,'SELECT work FROM work_link WHERE ws=? AND thread=? AND kind=?',(ws,i,k))
        if existing:return {'id':existing['work'],'duplicate':True}
        title=bounded(body.get('title',''),200);require(title,'제목 필요',422);detail=bounded(body.get('details',''),2000);j=uid();c.execute('INSERT INTO work VALUES(?,?,?,?,?,?,?)',(j,ws,k,title,detail,'open',now()));c.execute('INSERT INTO work_link VALUES(?,?,?,?)',(ws,i,k,j));event(c,ws,'work','상담에서 업무 등록',j)
    return {'id':j,'duplicate':False}

@app.get('/api/notifications')
def notification_status(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);require('email' in entitlements(w));return {'verified_email':w.get('owner_email') or '', 'settings':one(c,'SELECT email,enabled FROM notification_config WHERE ws=?',(ws,)) or {'email':'','enabled':0},'configured':bool(os.getenv('RESEND_API_KEY') and os.getenv('RESEND_FROM')),'auto_enabled':os.getenv('ENABLE_AUTO_EMAIL')=='1','live_enabled':not DEMO and os.getenv('ENABLE_LIVE_EMAIL')=='1' and bool(os.getenv('RESEND_API_KEY') and os.getenv('RESEND_FROM')),'deliveries':rows(c,'SELECT * FROM delivery WHERE ws=? ORDER BY rowid DESC LIMIT 50',(ws,))}
@app.post('/api/notifications')
def notification_settings(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);require('email' in entitlements(w));email=bounded(body.get('email',''),254).lower();require(bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email)),'이메일 형식 오류',422);require(DEMO or not body.get('enabled') or (w.get('owner_email') or '').lower()==email,'실제 발송은 확인된 Google 로그인 이메일로만 가능합니다.',403);c.execute('INSERT INTO notification_config VALUES(?,?,?) ON CONFLICT(ws) DO UPDATE SET email=excluded.email,enabled=excluded.enabled',(ws,email,int(body.get('enabled') is True)))
    return {'ok':True}
@app.post('/api/notifications/dispatch')
def dispatch_events(ws=Depends(ident)):
    from notifications import dispatch
    with db() as c:
        w=getw(c,ws);require('email' in entitlements(w));require(one(c,'SELECT ws FROM notification_config WHERE ws=? AND enabled=1',(ws,)),'알림 설정 필요',409);require(loads(w['settings'])['modes'].get('email')!='off','이메일 알림 OFF',409)
    return {'results':dispatch(ws)}

@app.post('/api/channels/simulate')
def simulate_channel(body:dict,ws=Depends(ident)):
    require(DEMO,'로컬 채널 시뮬레이션 전용');ch=body.get('channel');require(ch in ['naver','kakao'],'채널 오류',422);p=body.get('payload',{});require(isinstance(p,dict),'메시지 형식 오류',422)
    try:m=naver_in(p) if ch=='naver' else kakao_in(p)
    except (TypeError,AttributeError):m=None
    require(m,'지원되는 메시지 형식이 아닙니다.',422);external=hashlib.sha256(m.user.encode()).hexdigest()
    with db(True) as c:
        w=getw(c,ws);require(ch in entitlements(w) and w['enabled'],'채널 옵션 및 공개 활성화 필요');s=one(c,'SELECT token FROM channel_session WHERE ws=? AND channel=? AND external_user=?',(ws,ch,external));token=s['token'] if s else None
        if not token or not one(c,'SELECT token FROM visitor WHERE token=? AND expires>?',(token,now())):
            token=uid();c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'));c.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(uid(),ws,token,ch,now()));c.execute('INSERT INTO channel_session VALUES(?,?,?,?) ON CONFLICT(ws,channel,external_user) DO UPDATE SET token=excluded.token',(ws,ch,external,token))
    r=chat({'token':token,'message':m.text,'clientMessageId':bounded(body.get('event_id',uid()),100)})
    return {'simulated':True,'response':naver_out(m.user,r['reply']) if ch=='naver' else kakao_out(r['reply']),'remaining':r['remaining']}

@app.get('/api/customer/requests/{token}')
def request_options(token:str):
    with db() as c:
        v=visitor(c,token,kind='public');w=getw(c,v['ws']);require(w['enabled']);return [k for k in ['quote','complaints','tasks'] if k in entitlements(w)]

@app.post('/api/customer/requests')
def customer_request(body:dict):
    with db(True) as c:
        v=visitor(c,body.get('token',''),kind='public');ws=v['ws'];w=getw(c,ws);k=body.get('kind');require(w['enabled'] and k in ['quote','complaints','tasks'] and k in entitlements(w));require(body.get('confirmed') is True,'고객 확인 필요',422)
        title=bounded(body.get('title',''),200);details=bounded(body.get('details',''),2000);require(title and details,'제목과 내용 필요',422)
        t=one(c,'SELECT id FROM thread WHERE ws=? AND visitor=?',(ws,v['token']));existing=one(c,'SELECT work FROM work_link WHERE ws=? AND thread=? AND kind=?',(ws,t['id'],k))
        if existing:return {'id':existing['work'],'duplicate':True}
        j=uid();c.execute('INSERT INTO work VALUES(?,?,?,?,?,?,?)',(j,ws,k,title,details,'open',now()));c.execute('INSERT INTO work_link VALUES(?,?,?,?)',(ws,t['id'],k,j));event(c,ws,'work','고객 업무 요청 접수',j);return {'id':j,'duplicate':False}

@app.patch('/api/work/{i}')
def edit_work(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);r=one(c,'SELECT * FROM work WHERE ws=? AND id=?',(ws,i));require(r and r['kind'] in entitlements(w),'업무 없음 또는 권한 없음',404);title=bounded(body.get('title',r['title']),200);details=bounded(body.get('details',r['details']),2000);status=body.get('status',r['status']);require(title and status in ['open','pending','resolved'],'업무 상태 오류',422);c.execute('UPDATE work SET title=?,details=?,status=? WHERE id=?',(title,details,status,i))
    return {'ok':True}

@app.delete('/api/work/{i}')
def remove_work(i:str,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);r=one(c,'SELECT * FROM work WHERE ws=? AND id=?',(ws,i));require(r and r['kind'] in entitlements(w),'업무 없음 또는 권한 없음',404);c.execute('DELETE FROM work_link WHERE ws=? AND work=?',(ws,i));c.execute('DELETE FROM work WHERE ws=? AND id=?',(ws,i))
    return {'ok':True}

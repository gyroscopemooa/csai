"""Separate brand calendars and opt-in public booking; no Google sync."""
import re
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from fastapi import Depends
from store import *

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS brand_calendar_settings(ws TEXT NOT NULL,agent TEXT NOT NULL,config TEXT NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS brand_booking(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL,resource TEXT NOT NULL,payload TEXT NOT NULL,fields TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,customer_ok INTEGER NOT NULL,paid INTEGER NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS brand_booking_customer(ws TEXT NOT NULL,agent TEXT NOT NULL,booking TEXT NOT NULL,visitor TEXT NOT NULL,secret TEXT NOT NULL,PRIMARY KEY(ws,agent,booking));
        CREATE TABLE IF NOT EXISTS brand_booking_change(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,booking TEXT NOT NULL,visitor TEXT NOT NULL,action TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL,original_start TEXT NOT NULL,version INTEGER NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS brand_booking_change_scope ON brand_booking_change(ws,agent,booking,state);
        CREATE INDEX IF NOT EXISTS brand_booking_customer_lookup ON brand_booking_customer(ws,agent,visitor);
        CREATE INDEX IF NOT EXISTS brand_booking_scope ON brand_booking(ws,agent,resource,start,end);
        """)
init()
def config(c,ws,agent):
    r=one(c,'SELECT config FROM brand_calendar_settings WHERE ws=? AND agent=?',(ws,agent))
    return ({'booking_mode':'off','allow_customer_change':False}|loads(r['config'])) if r else {'booking_mode':'off','allow_customer_change':False,'timezone':'Asia/Seoul','open':'09:00','close':'18:00','duration':60,'buffer':0,'closed_days':[],'payment_required':False,'resources':[{'id':'default','name':'기본 담당자'}],'fields':[{'key':'title','label':'일정 제목','type':'text','required':True},{'key':'contact','label':'연락처','type':'phone','required':False},{'key':'note','label':'메모','type':'text','required':False}],'template_version':1}
def access(c,ws,agent):
    from app import require
    from branding import owned_agent
    w=getw(c,ws);require(bool(agent),'추가 브랜드를 선택하세요.',422);owned_agent(c,w,agent);require('calendar' in entitlements(w),'일정표 구매 필요',403);return w
def available(c,ws,agent,start,end,buffer,resource,exclude=''):
    from app import blocked_conflict
    if blocked_conflict(config(c,ws,agent),start,end,buffer):return False
    t0=(datetime.fromisoformat(start)-timedelta(minutes=buffer)).isoformat();t1=(datetime.fromisoformat(end)+timedelta(minutes=buffer)).isoformat()
    return not one(c,"SELECT id FROM brand_booking WHERE ws=? AND agent=? AND resource=? AND status='confirmed' AND start<? AND end>? AND id<>?",(ws,agent,resource,t1,t0,exclude))
def view(b):
    from app import booking_view
    return booking_view(b)|{'agent':b['agent'],'sample':False}
def public_config(c,w,profile):
    if not profile or not w or not public_access(w) or not profile['enabled'] or trial(c,w) or 'calendar' not in entitlements(w):
        return None
    if one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(w['id'],profile['id'])):
        return None
    s=config(c,w['id'],profile['id'])
    return s if s['booking_mode'] in ('manual','auto') else None

def customer_scope(c,v,allow_test=False):
    from app import require
    from branding import owned_agent
    w=getw(c,v['ws']);a=owned_agent(c,w,v['agent'])
    require(v['kind']=='public' or allow_test,'관리자 테스트에서는 실제 예약을 만들 수 없습니다.',409)
    s=public_config(c,w,a);require(s,'브랜드 예약이 비활성화되었습니다.',409)
    return w,s

def customer_draft(c,v,body):
    from app import require,validate_fields,resource_id,interval
    w,s=customer_scope(c,v);ws=v['ws'];agent=v['agent'];token=v['token']
    require(body.get('version')==s['template_version'],'양식 변경됨. 다시 확인하세요.',409)
    data=validate_fields(s,body.get('payload',{}));resource=resource_id(s,body);a,b=interval(s,body.get('start',''))
    require(available(c,ws,agent,a,b,s['buffer'],resource),'선택한 시간이 이미 예약되었습니다.',409)
    c.execute("UPDATE brand_booking SET status='superseded' WHERE ws=? AND agent=? AND status='draft' AND id IN (SELECT booking FROM brand_booking_customer WHERE ws=? AND agent=? AND visitor=?)",(ws,agent,ws,agent,token))
    i,secret=uid(),uid()
    c.execute('INSERT INTO brand_booking VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,agent,a,b,resource,dump(data),dump(s['fields']),s['template_version'],'draft',0,0,now()))
    c.execute('INSERT INTO brand_booking_customer VALUES(?,?,?,?,?)',(ws,agent,i,token,secret))
    return view(one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,i)))|{'token':secret}

def customer_confirm(c,v,i,body):
    from app import require
    import secrets,policies,ops
    w,s=customer_scope(c,v);ws=v['ws'];agent=v['agent']
    link=one(c,'SELECT secret FROM brand_booking_customer WHERE ws=? AND agent=? AND visitor=? AND booking=?',(ws,agent,v['token'],i))
    require(link and secrets.compare_digest(link['secret'],str(body.get('confirmation',''))),'예약 확인 권한 없음',403)
    b=one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,i))
    require(b and b['status']!='superseded','이전 양식입니다.',409)
    if b['status']!='draft':return view(b)
    require(b['version']==s['template_version'] and b['created']>now()-1800 and datetime.fromisoformat(b['start'])>datetime.now(timezone.utc),'예약 정보 만료 또는 양식 변경',409)
    require(available(c,ws,agent,b['start'],b['end'],s['buffer'],b['resource']),'다른 고객이 먼저 예약했습니다.',409)
    auto=s['booking_mode']=='auto' and 'auto_booking' in entitlements(w) and policies.status(c,ws)['automation_accepted']
    status='pending_payment' if s['payment_required'] else 'confirmed' if auto else 'pending'
    c.execute('UPDATE brand_booking SET customer_ok=1,status=? WHERE ws=? AND agent=? AND id=?',(status,ws,agent,i))
    c.execute("UPDATE thread SET booking_context='{}' WHERE ws=? AND visitor=?",(ws,v['token']))
    # Brand bookings are deliberately not passed to main-brand notification/calendar workers.
    ops.event(c,ws,'brand_booking','추가 브랜드 예약 '+('확정' if status=='confirmed' else '확인 요청'),i)
    return view(one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,i)))

def customer_list(c,v):
    w,s=customer_scope(c,v)
    bs=rows(c,"SELECT b.* FROM brand_booking b JOIN brand_booking_customer x ON x.ws=b.ws AND x.agent=b.agent AND x.booking=b.id WHERE b.ws=? AND b.agent=? AND x.visitor=? AND b.status NOT IN ('draft','superseded') ORDER BY b.start",(v['ws'],v['agent'],v['token']))
    return {'bookings':[view(b) for b in bs],'canChange':s['allow_customer_change'] and 'change_booking' in entitlements(w),'canRecover':False,'requests':rows(c,'SELECT id,booking,action,start,state FROM brand_booking_change WHERE ws=? AND agent=? AND visitor=? ORDER BY created DESC',(v['ws'],v['agent'],v['token'])),'brandScoped':True}

def customer_change(c,v,i,body):
    from app import require,interval
    import ops
    w,s=customer_scope(c,v);ws=v['ws'];agent=v['agent']
    require('change_booking' in entitlements(w) and s['allow_customer_change'],'고객 예약 변경 기능이 꺼져 있습니다.',403)
    b=one(c,"SELECT b.* FROM brand_booking b JOIN brand_booking_customer x ON x.ws=b.ws AND x.agent=b.agent AND x.booking=b.id WHERE b.ws=? AND b.agent=? AND b.id=? AND x.visitor=?",(ws,agent,i,v['token']))
    require(b and b['status']=='confirmed','변경 가능한 본인 예약 없음',404)
    require(datetime.fromisoformat(b['start'])>datetime.now(timezone.utc),'지난 예약은 변경할 수 없습니다.',409)
    action=body.get('action');require(body.get('confirmed') is True and action in ('cancel','change'),'고객 최종 확인 필요',422)
    require(not one(c,"SELECT id FROM brand_booking_change WHERE ws=? AND agent=? AND booking=? AND state='pending'",(ws,agent,i)),'이미 승인 대기 중인 요청이 있습니다.',409)
    a=z=''
    if action=='change':
        a,z=interval(s,body.get('start',''));require(available(c,ws,agent,a,z,s['buffer'],b['resource'],i),'예약 시간 충돌',409)
    rid=uid();c.execute('INSERT INTO brand_booking_change VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(rid,ws,agent,i,v['token'],action,a,z,b['start'],s['template_version'],'pending',now()))
    ops.event(c,ws,'brand_booking','추가 브랜드 예약 변경·취소 요청',i)
    return {'id':rid,'state':'pending'}


def register(app,ident):
    from app import require,bounded,interval,resource_id,validate_fields
    @app.get('/api/brand-calendar/{agent}/changes')
    def changes(agent:str,ws=Depends(ident)):
        with db() as c:
            w=access(c,ws,agent);require('change_booking' in entitlements(w))
            return rows(c,'SELECT id,booking,action,start,state,created FROM brand_booking_change WHERE ws=? AND agent=? ORDER BY created DESC',(ws,agent))
    @app.post('/api/brand-calendar/{agent}/changes/{i}')
    def decide_change(agent:str,i:str,body:dict,ws=Depends(ident)):
        import ops
        with db(True) as c:
            w=access(c,ws,agent);require('change_booking' in entitlements(w))
            r=one(c,"SELECT * FROM brand_booking_change WHERE ws=? AND agent=? AND id=? AND state='pending'",(ws,agent,i));require(r,'승인 대기 요청 없음',404)
            decision=body.get('action');require(decision in ('approve','reject'),'요청 유형 오류',422)
            if decision=='approve':
                from branding import owned_agent
                s=public_config(c,w,owned_agent(c,w,agent));require(s and s['allow_customer_change'],'예약 변경 기능이 꺼져 있습니다.',409)
                b=one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,r['booking']))
                require(b and b['status']=='confirmed' and b['start']==r['original_start'] and datetime.fromisoformat(b['start'])>datetime.now(timezone.utc),'예약 상태가 변경되었거나 만료되었습니다.',409)
                if r['action']=='cancel':
                    c.execute("UPDATE brand_booking SET status='cancelled' WHERE ws=? AND agent=? AND id=?",(ws,agent,b['id']))
                else:
                    require(r['version']==s['template_version'] and b['resource'] in [x['id'] for x in s['resources']] and datetime.fromisoformat(r['start'])>datetime.now(timezone.utc) and available(c,ws,agent,r['start'],r['end'],s['buffer'],b['resource'],b['id']),'변경 시간 충돌 또는 설정 변경',409)
                    c.execute('UPDATE brand_booking SET start=?,end=? WHERE ws=? AND agent=? AND id=?',(r['start'],r['end'],ws,agent,b['id']))
                ops.event(c,ws,'brand_booking','추가 브랜드 예약 변경·취소 승인',b['id'])
            c.execute('UPDATE brand_booking_change SET state=? WHERE ws=? AND agent=? AND id=?',('approved' if decision=='approve' else 'rejected',ws,agent,i))
        return {'ok':True}
    @app.get('/api/brand-calendar/{agent}')
    def get(agent:str,ws=Depends(ident)):
        with db() as c:
            access(c,ws,agent);return {'settings':config(c,ws,agent),'bookings':[view(b) for b in rows(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND status NOT IN (\'draft\',\'superseded\') ORDER BY start',(ws,agent))]}
    @app.post('/api/brand-calendar/{agent}/settings')
    def save(agent:str,body:dict,ws=Depends(ident)):
        with db(True) as c:
            access(c,ws,agent);s=config(c,ws,agent);old=dump(s)
            for k in ['open','close']:
                if k in body:
                    require(isinstance(body[k],str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',body[k]),'시간 형식 오류',422);s[k]=body[k]
            require(s['open']<s['close'],'운영 시간 오류',422)
            for k in ['duration','buffer']:
                if k in body:
                    require(type(body[k]) is int and (5 if k=='duration' else 0)<=body[k]<=480,'시간 간격 오류',422);s[k]=body[k]
            if 'timezone' in body:
                try:ZoneInfo(body['timezone'])
                except Exception:require(False,'시간대 오류',422)
                s['timezone']=body['timezone']
            if 'closed_days' in body:
                d=body['closed_days'];require(isinstance(d,list) and all(type(x) is int and 0<=x<=6 for x in d),'휴무 요일 오류',422);s['closed_days']=sorted(set(d))
            if 'blocked_times' in body:
                from app import validate_blocked_times
                s['blocked_times']=validate_blocked_times(body['blocked_times'])
            if 'booking_mode' in body:
                import policies
                mode=body['booking_mode'];require(isinstance(mode,str) and mode in ('off','manual','auto'),'예약 모드 오류',422)
                if mode=='auto':require('auto_booking' in entitlements(getw(c,ws)) and policies.status(c,ws)['automation_accepted'],'자동 예약 옵션 및 위험 안내 확인 필요',403)
                s['booking_mode']=mode
            if 'allow_customer_change' in body:
                require(type(body['allow_customer_change']) is bool,'변경 허용 설정 오류',422)
                if body['allow_customer_change']:require('change_booking' in entitlements(getw(c,ws)))
                s['allow_customer_change']=body['allow_customer_change']
            if 'payment_required' in body:
                require(type(body['payment_required']) is bool,'결제 확인 설정 오류',422);s['payment_required']=body['payment_required']
            if 'resources' in body:
                rs=body['resources'];require(isinstance(rs,list) and 1<=len(rs)<=20,'담당자 1~20명',422);out=[];seen=set()
                for r in rs:
                    require(isinstance(r,dict),'담당자 형식 오류',422);k=bounded(r.get('id',''),60);n=bounded(r.get('name',''),100)
                    require(re.fullmatch(r'[a-zA-Z0-9_-]+',k) and k not in seen and n,'담당자 정보 오류',422);seen.add(k);out.append({'id':k,'name':n})
                require('default' in seen,'기본 담당자는 유지해야 합니다.',422)
                for r in rows(c,"SELECT DISTINCT resource FROM brand_booking WHERE ws=? AND agent=? AND status IN ('confirmed','pending','pending_payment') AND start>?",(ws,agent,datetime.now(timezone.utc).isoformat())):require(r['resource'] in seen,'예정 일정이 있는 담당자는 삭제할 수 없습니다.',409)
                s['resources']=out
            if 'fields' in body:
                fs=body['fields'];require(isinstance(fs,list) and 1<=len(fs)<=30,'양식 1~30개',422);out=[];seen=set()
                for f in fs:
                    require(isinstance(f,dict),'양식 형식 오류',422);key=bounded(f.get('key',''),60);label=bounded(f.get('label',''),100);kind=f.get('type');opts=f.get('options',[])
                    require(re.fullmatch(r'[a-zA-Z0-9_-]+',key) and key not in seen and label and kind in ('text','phone','number','date','time','select','boolean') and type(f.get('required')) is bool and isinstance(opts,list) and len(opts)<=20 and all(isinstance(x,str) for x in opts),'양식 오류',422);seen.add(key);out.append({'key':key,'label':label,'type':kind,'required':f['required'],'options':[bounded(x,100) for x in opts]})
                s['fields']=out
            if dump(s)!=old:s['template_version']+=1
            c.execute('INSERT INTO brand_calendar_settings VALUES(?,?,?) ON CONFLICT(ws,agent) DO UPDATE SET config=excluded.config',(ws,agent,dump(s)))
            return {'settings':s}
    @app.post('/api/brand-calendar/{agent}/bookings')
    def add(agent:str,body:dict,ws=Depends(ident)):
        with db(True) as c:
            w=access(c,ws,agent);require(not one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(ws,agent)),'보관된 브랜드입니다.',409);require(not trial(c,w),'초청 체험의 추가 브랜드 일정은 준비 중입니다.',409)
            s=config(c,ws,agent);require(body.get('version')==s['template_version'],'양식 변경됨. 다시 확인하세요.',409)
            data=validate_fields(s,body.get('payload',{}));resource=resource_id(s,body);start,end=interval(s,body.get('start',''));require(available(c,ws,agent,start,end,s['buffer'],resource),'예약 시간이 겹칩니다.',409)
            paid=body.get('paid') is True;i=uid();status='pending_payment' if s['payment_required'] and not paid else 'confirmed'
            c.execute('INSERT INTO brand_booking VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,agent,start,end,resource,dump(data),dump(s['fields']),s['template_version'],status,1,int(paid),now()))
            return view(one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,i)))
    @app.post('/api/brand-calendar/{agent}/bookings/{i}')
    def edit(agent:str,i:str,body:dict,ws=Depends(ident)):
        with db(True) as c:
            w=access(c,ws,agent);b=one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,i));require(b,'일정 없음',404);s=config(c,ws,agent);action=body.get('action')
            if action in ('approve','change'):
                require(not one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(ws,agent)),'보관된 브랜드입니다.',409)
                require(not trial(c,w),'초청 체험의 추가 브랜드 일정은 준비 중입니다.',409)
                require(b['resource'] in [r['id'] for r in s['resources']],'담당자가 변경되었습니다.',409)
            if action=='approve':
                require(b['status'] in ('pending','pending_payment') and b['customer_ok'],'확정할 수 없는 일정',409);paid=bool(b['paid'] or body.get('paid') is True);require(not s['payment_required'] or paid,'외부 결제 확인 필요',409);require(b['version']==s['template_version'] and datetime.fromisoformat(b['start'])>datetime.now(timezone.utc) and available(c,ws,agent,b['start'],b['end'],s['buffer'],b['resource'],i),'일정 충돌·만료 또는 설정 변경',409)
                c.execute("UPDATE brand_booking SET status='confirmed',paid=? WHERE ws=? AND agent=? AND id=?",(int(paid),ws,agent,i))
            elif action=='cancel':
                require(b['status'] in ('confirmed','pending','pending_payment'),'취소 불가',409);c.execute("UPDATE brand_booking SET status='cancelled' WHERE ws=? AND agent=? AND id=?",(ws,agent,i))
            elif action=='complete':
                require(b['status']=='confirmed','확정 일정만 완료 가능',409);c.execute("UPDATE brand_booking SET status='completed' WHERE ws=? AND agent=? AND id=?",(ws,agent,i))
            elif action=='change':
                require('change_booking' in entitlements(w) and b['status']=='confirmed','일정 변경 권한 또는 상태 오류',409);start,end=interval(s,body.get('start',''));require(available(c,ws,agent,start,end,s['buffer'],b['resource'],i),'일정 충돌',409);c.execute('UPDATE brand_booking SET start=?,end=? WHERE ws=? AND agent=? AND id=?',(start,end,ws,agent,i))
            else:require(False,'업무 유형 오류',422)
            return view(one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,i)))

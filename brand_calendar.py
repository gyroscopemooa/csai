"""Separate staff calendars for additional brands. No customer or Google sync yet."""
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
        CREATE INDEX IF NOT EXISTS brand_booking_scope ON brand_booking(ws,agent,resource,start,end);
        """)
init()
def config(c,ws,agent):
    r=one(c,'SELECT config FROM brand_calendar_settings WHERE ws=? AND agent=?',(ws,agent))
    return loads(r['config']) if r else {'timezone':'Asia/Seoul','open':'09:00','close':'18:00','duration':60,'buffer':0,'closed_days':[],'payment_required':False,'resources':[{'id':'default','name':'기본 담당자'}],'fields':[{'key':'title','label':'일정 제목','type':'text','required':True},{'key':'contact','label':'연락처','type':'phone','required':False},{'key':'note','label':'메모','type':'text','required':False}],'template_version':1}
def access(c,ws,agent):
    from app import require
    from branding import owned_agent
    w=getw(c,ws);require(bool(agent),'추가 브랜드를 선택하세요.',422);owned_agent(c,w,agent);require('calendar' in entitlements(w),'일정표 구매 필요',403);return w
def available(c,ws,agent,start,end,buffer,resource,exclude=''):
    t0=(datetime.fromisoformat(start)-timedelta(minutes=buffer)).isoformat();t1=(datetime.fromisoformat(end)+timedelta(minutes=buffer)).isoformat()
    return not one(c,"SELECT id FROM brand_booking WHERE ws=? AND agent=? AND resource=? AND status='confirmed' AND start<? AND end>? AND id<>?",(ws,agent,resource,t1,t0,exclude))
def view(b):
    from app import booking_view
    return booking_view(b)|{'agent':b['agent'],'sample':False}
def register(app,ident):
    from app import require,bounded,interval,resource_id,validate_fields
    @app.get('/api/brand-calendar/{agent}')
    def get(agent:str,ws=Depends(ident)):
        with db() as c:
            access(c,ws,agent);return {'settings':config(c,ws,agent),'bookings':[view(b) for b in rows(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? ORDER BY start',(ws,agent))]}
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
            if 'payment_required' in body:
                require(type(body['payment_required']) is bool,'결제 확인 설정 오류',422);s['payment_required']=body['payment_required']
            if 'resources' in body:
                rs=body['resources'];require(isinstance(rs,list) and 1<=len(rs)<=20,'담당자 1~20명',422);out=[];seen=set()
                for r in rs:
                    require(isinstance(r,dict),'담당자 형식 오류',422);k=bounded(r.get('id',''),60);n=bounded(r.get('name',''),100)
                    require(re.fullmatch(r'[a-zA-Z0-9_-]+',k) and k not in seen and n,'담당자 정보 오류',422);seen.add(k);out.append({'id':k,'name':n})
                require('default' in seen,'기본 담당자는 유지해야 합니다.',422)
                for r in rows(c,"SELECT DISTINCT resource FROM brand_booking WHERE ws=? AND agent=? AND status IN ('confirmed','pending_payment') AND start>?",(ws,agent,datetime.now(timezone.utc).isoformat())):require(r['resource'] in seen,'예정 일정이 있는 담당자는 삭제할 수 없습니다.',409)
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
            if action=='approve':
                require(b['status']=='pending_payment' and body.get('paid') is True,'외부 결제 확인 필요',409);require(b['version']==s['template_version'] and datetime.fromisoformat(b['start'])>datetime.now(timezone.utc) and available(c,ws,agent,b['start'],b['end'],s['buffer'],b['resource'],i),'일정 충돌·만료 또는 설정 변경',409)
                c.execute("UPDATE brand_booking SET status='confirmed',paid=1 WHERE ws=? AND agent=? AND id=?",(ws,agent,i))
            elif action=='cancel':
                require(b['status'] in ('confirmed','pending_payment'),'취소 불가',409);c.execute("UPDATE brand_booking SET status='cancelled' WHERE ws=? AND agent=? AND id=?",(ws,agent,i))
            elif action=='complete':
                require(b['status']=='confirmed','확정 일정만 완료 가능',409);c.execute("UPDATE brand_booking SET status='completed' WHERE ws=? AND agent=? AND id=?",(ws,agent,i))
            elif action=='change':
                require('change_booking' in entitlements(w) and b['status']=='confirmed','일정 변경 권한 또는 상태 오류',409);start,end=interval(s,body.get('start',''));require(available(c,ws,agent,start,end,s['buffer'],b['resource'],i),'일정 충돌',409);c.execute('UPDATE brand_booking SET start=?,end=? WHERE ws=? AND agent=? AND id=?',(start,end,ws,agent,i))
            else:require(False,'업무 유형 오류',422)
            return view(one(c,'SELECT * FROM brand_booking WHERE ws=? AND agent=? AND id=?',(ws,agent,i)))

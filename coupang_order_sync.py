"""Bounded rolling seller-only order status snapshots. No PII, GPT or mutations."""
import os
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from fastapi import Depends,HTTPException
from app import app,ident,require,limit
from store import *
import commerce,coupang_connection as cc
from google_calendar import encryption
from integrations import coupang_transport as cp

DAYS=7
STATUSES=tuple(cp.STATUSES)
RETENTION=30*86400
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS coupang_order_job(ws TEXT NOT NULL,agent TEXT NOT NULL,active INTEGER NOT NULL,state TEXT NOT NULL,error TEXT NOT NULL,next_sync INTEGER NOT NULL,last_sync INTEGER NOT NULL,claim TEXT NOT NULL,claimed INTEGER NOT NULL,scan_day TEXT NOT NULL,scan_state INTEGER NOT NULL,history_offset INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS coupang_order_state(ws TEXT NOT NULL,agent TEXT NOT NULL,shipment TEXT NOT NULL,day TEXT NOT NULL,status TEXT NOT NULL,content TEXT NOT NULL,updated INTEGER NOT NULL,present INTEGER NOT NULL,PRIMARY KEY(ws,agent,shipment));
        CREATE INDEX IF NOT EXISTS coupang_order_due ON coupang_order_job(active,next_sync);
        CREATE INDEX IF NOT EXISTS coupang_order_recent ON coupang_order_state(ws,agent,updated);
        """)
init()
def configured():return cc.configured() and os.getenv('ENABLE_COUPANG_ORDER_SYNC')=='1'
def conn(c,ws,a):return one(c,'SELECT vendor,credential FROM coupang_connection WHERE ws=? AND agent=?',(ws,a))
def valid(c,ws,a):
    try:commerce.access(c,ws,a,True);return conn(c,ws,a)
    except HTTPException:return None

def clear(c,ws,a):
    c.execute('DELETE FROM coupang_order_job WHERE ws=? AND agent=?',(ws,a))
    c.execute('DELETE FROM coupang_order_state WHERE ws=? AND agent=?',(ws,a))

def today():return datetime.now(ZoneInfo('Asia/Seoul')).date()
def view(c,ws,a):
    r=one(c,'SELECT active,state,error,last_sync,next_sync,scan_day,scan_state FROM coupang_order_job WHERE ws=? AND agent=?',(ws,a))
    return {'available':configured(),'connected':bool(conn(c,ws,a)),'active':bool(r and r['active']),'state':r['state'] if r else 'disabled','error':r['error'] if r else '', 'last_sync':r['last_sync'] if r else 0,'scan_day':r['scan_day'] if r else '', 'scan_status':STATUSES[r['scan_state']%len(STATUSES)] if r else '', 'count':one(c,'SELECT COUNT(*) n FROM coupang_order_state WHERE ws=? AND agent=? AND updated>=?',(ws,a,now()-RETENTION))['n'],'education_credits':0}

@app.get('/api/commerce/coupang/order-sync')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False);return view(c,ws,agent)

@app.post('/api/commerce/coupang/order-sync')
def enable(body:dict,agent:str='',ws=Depends(ident)):
    flag=body.get('enabled');require(type(flag) is bool,'설정 오류',422)
    require(not flag or configured(),'쿠팡 주문 동기화 비활성화',503)
    limit('cp-order-sync:'+ws,4,60)
    with db(True) as c:
        commerce.access(c,ws,agent,True);require(conn(c,ws,agent),'쿠팡 판매자 연결 필요',409)
        if not flag:clear(c,ws,agent)
        else:
            old=one(c,'SELECT state FROM coupang_order_job WHERE ws=? AND agent=?',(ws,agent))
            require(not old or old['state']!='running','동기화 중',409)
            c.execute("INSERT INTO coupang_order_job VALUES(?,?,1,'queued','',?,0,'',0,?,0,1) ON CONFLICT(ws,agent) DO UPDATE SET active=1,state='queued',error='',next_sync=excluded.next_sync,claim='',claimed=0",(ws,agent,now(),today().isoformat()))
        return view(c,ws,agent)

def next_scan(j,current_day):
    """Current day six states, then one rotating historical day six states per cycle."""
    i=j['scan_state']+1;offset=j['history_offset']
    if i<12:
        day=current_day if i<6 else current_day-timedelta(days=offset)
        return day.isoformat(),i,offset,10
    return current_day.isoformat(),0,offset%(DAYS-1)+1,600

def tick():
    if not configured():return False
    with db(True) as c:
        t=now()
        c.execute('DELETE FROM coupang_order_state WHERE updated<?',(t-RETENTION,))
        c.execute("UPDATE coupang_order_job SET state='error',error='이전 동기화 시간 초과',next_sync=?,claim='',claimed=0 WHERE state='running' AND claimed<?",(t+600,t-300))
        j=one(c,"SELECT * FROM coupang_order_job WHERE active=1 AND state<>'running' AND next_sync<=? ORDER BY next_sync LIMIT 1",(t,))
        if not j:return False
        ws,a=j['ws'],j['agent'];link=valid(c,ws,a)
        if not link:clear(c,ws,a);return True
        day=today()
        if j['scan_day']< (day-timedelta(days=DAYS-1)).isoformat() or j['scan_day']>day.isoformat():
            j.update(scan_day=day.isoformat(),scan_state=0)
        status=STATUSES[j['scan_state']%len(STATUSES)];claim=uid()
        c.execute("UPDATE coupang_order_job SET state='running',claim=?,claimed=?,scan_day=?,scan_state=? WHERE ws=? AND agent=?",(claim,t,j['scan_day'],j['scan_state'],ws,a))
    try:
        keys=loads(encryption().decrypt(link['credential'].encode()).decode())
        items=cp.ordersheets_day(link['vendor'],keys['access'],keys['secret'],j['scan_day'],status);err=''
    except cp.CoupangError as e:items=None;err=str(e)[:150]
    except Exception:items=None;err='판매자 인증 또는 연결 확인 필요'
    with db(True) as c:
        cur=one(c,'SELECT active,state,claim FROM coupang_order_job WHERE ws=? AND agent=?',(ws,a))
        if not cur or not cur['active'] or cur['state']!='running' or cur['claim']!=claim:return True
        if valid(c,ws,a)!=link:clear(c,ws,a);return True
        t=now()
        if items is None:
            # Do not erase a prior snapshot on partial or failed provider reads.
            c.execute("UPDATE coupang_order_job SET state='error',error=?,next_sync=?,claim='',claimed=0 WHERE ws=? AND agent=?",(err,t+600,ws,a))
        else:
            # Missing from a completed status page means only 'not observed'; never infer a cancellation.
            c.execute('UPDATE coupang_order_state SET present=0 WHERE ws=? AND agent=? AND day=? AND status=?',(ws,a,j['scan_day'],status))
            for x in items:
                c.execute('INSERT INTO coupang_order_state VALUES(?,?,?,?,?,?,?,1) ON CONFLICT(ws,agent,shipment) DO UPDATE SET day=excluded.day,status=excluded.status,content=excluded.content,updated=excluded.updated,present=1',(ws,a,x['shipment_id'],j['scan_day'],status,dump(x),t))
            d,i,o,delay=next_scan(j,today())
            c.execute("UPDATE coupang_order_job SET state='synced',error='',next_sync=?,last_sync=?,claim='',claimed=0,scan_day=?,scan_state=?,history_offset=? WHERE ws=? AND agent=?",(t+delay,t,d,i,o,ws,a))
    return True

@app.get('/api/commerce/coupang/order-sync/records')
def records(agent:str='',page:int=1,ws=Depends(ident)):
    require(1<=page<=200,'페이지 오류',422)
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False)
        data=rows(c,'SELECT content,updated,present FROM coupang_order_state WHERE ws=? AND agent=? AND updated>=? ORDER BY updated DESC,shipment LIMIT 100 OFFSET ?',(ws,agent,now()-RETENTION,(page-1)*100))
        return {**view(c,ws,agent),'records':[{**loads(x['content']),'as_of':x['updated'],'observed':bool(x['present'])} for x in data]}

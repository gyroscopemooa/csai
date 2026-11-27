"""SmartStore read-only changed-order feed, distinct from manual sales and customer data."""
from datetime import datetime,timezone
import os
from fastapi import Depends,HTTPException
from app import app,ident,require,limit
from store import *
import commerce,smartstore_sync as ssync
from google_calendar import encryption
from integrations import smartstore_transport as ss

INTERVAL=600
RETENTION=30*86400
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS smartstore_order_job(ws TEXT NOT NULL,agent TEXT NOT NULL,active INTEGER NOT NULL,state TEXT NOT NULL,error TEXT NOT NULL,cursor INTEGER NOT NULL,last_sync INTEGER NOT NULL,next_sync INTEGER NOT NULL,claim TEXT NOT NULL,claimed INTEGER NOT NULL,window INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS smartstore_order_state(ws TEXT NOT NULL,agent TEXT NOT NULL,reference TEXT NOT NULL,changed_at INTEGER NOT NULL,content TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,reference));
        CREATE INDEX IF NOT EXISTS smartstore_order_due ON smartstore_order_job(active,next_sync);
        CREATE INDEX IF NOT EXISTS smartstore_order_recent ON smartstore_order_state(ws,agent,changed_at);
        """)
init()

def configured():return ssync.configured() and os.getenv('ENABLE_SMARTSTORE_ORDER_SYNC')=='1'
def conn(c,ws,a):return one(c,'SELECT client_id,credential FROM smartstore_connection WHERE ws=? AND agent=? AND active=1',(ws,a))
def valid(c,ws,a):
    try:commerce.access(c,ws,a,True);return conn(c,ws,a)
    except HTTPException:return None

def view(c,ws,a):
    r=one(c,'SELECT active,state,error,cursor,last_sync,next_sync FROM smartstore_order_job WHERE ws=? AND agent=?',(ws,a))
    return {'available':configured(),'connected':bool(conn(c,ws,a)),'active':bool(r and r['active']),'state':r['state'] if r else 'disabled','error':r['error'] if r else '', 'cursor':r['cursor'] if r else 0,'last_sync':r['last_sync'] if r else 0,'count':one(c,'SELECT COUNT(*) n FROM smartstore_order_state WHERE ws=? AND agent=? AND updated>=?',(ws,a,now()-RETENTION))['n'],'interval_minutes':10,'education_credits':0}

def clear(c,ws,a):
    c.execute('DELETE FROM smartstore_order_job WHERE ws=? AND agent=?',(ws,a))
    c.execute('DELETE FROM smartstore_order_state WHERE ws=? AND agent=?',(ws,a))

@app.get('/api/commerce/smartstore/order-sync')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False);return view(c,ws,agent)

@app.post('/api/commerce/smartstore/order-sync')
def enable(body:dict,agent:str='',ws=Depends(ident)):
    flag=body.get('enabled');require(type(flag) is bool,'설정 오류',422)
    require(not flag or configured(),'주문 자동 동기화 비활성화',503)
    limit('ss-order-sync:'+ws,4,60)
    with db(True) as c:
        commerce.access(c,ws,agent,True);require(conn(c,ws,agent),'스마트스토어 연결 필요',409)
        if not flag:clear(c,ws,agent)
        else:
            old=one(c,'SELECT state,cursor FROM smartstore_order_job WHERE ws=? AND agent=?',(ws,agent))
            require(not old or old['state']!='running','동기화 중',409)
            t=now();start=t-86400 if not old else old['cursor']
            require(start>=t-7*86400,'7일 이상 동기화 지연 · 초기화 후 새로 연결하세요.',409)
            c.execute("INSERT INTO smartstore_order_job VALUES(?,?,1,'queued','',?,0,?,'',0,3600) ON CONFLICT(ws,agent) DO UPDATE SET active=1,state='queued',error='',next_sync=excluded.next_sync,claim='',claimed=0",(ws,agent,start,t))
        return view(c,ws,agent)

def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat(timespec='milliseconds')

def tick():
    if not configured():return False
    with db(True) as c:
        c.execute("DELETE FROM smartstore_order_state WHERE updated<?",(now()-RETENTION,))
        c.execute("UPDATE smartstore_order_job SET state='error',error='이전 조회 시간 초과',next_sync=?,claim='',claimed=0 WHERE state='running' AND claimed<?",(now()+600,now()-300))
        j=one(c,"SELECT * FROM smartstore_order_job WHERE active=1 AND state<>'running' AND next_sync<=? ORDER BY next_sync LIMIT 1",(now(),))
        if not j:return False
        ws,a=j['ws'],j['agent'];link=valid(c,ws,a)
        if not link:clear(c,ws,a);return True
        t=now()
        if j['cursor']<t-7*86400:
            c.execute("UPDATE smartstore_order_job SET active=0,state='paused',error='7일 이상 지연 · 초기화 후 다시 연결 필요' WHERE ws=? AND agent=?",(ws,a));return True
        # 2-minute overlap avoids provider boundary/visibility delays. Monotonic cursor advances only on complete response.
        start=j['cursor']-120;end=min(t-60,j['cursor']+j['window'])
        if end<=j['cursor']:
            c.execute('UPDATE smartstore_order_job SET next_sync=? WHERE ws=? AND agent=?',(t+INTERVAL,ws,a));return True
        claim=uid()
        c.execute("UPDATE smartstore_order_job SET state='running',claim=?,claimed=? WHERE ws=? AND agent=?",(claim,t,ws,a))
    try:
        token=ss.access_token(link['client_id'],encryption().decrypt(link['credential'].encode()).decode())
        items=ss.changed_orders(token,iso(start),iso(end));err=''
    except ss.SmartStoreError as e:items=None;err=str(e)[:150]
    except Exception:items=None;err='판매처 연결 또는 인증 확인 필요'
    with db(True) as c:
        cur=one(c,'SELECT active,state,claim FROM smartstore_order_job WHERE ws=? AND agent=?',(ws,a))
        if not cur or not cur['active'] or cur['state']!='running' or cur['claim']!=claim:return True
        if valid(c,ws,a)!=link:clear(c,ws,a);return True
        t=now()
        if items is None:
            # High-volume windows shrink until complete, without skipping unprocessed data.
            window=max(60,j['window']//2) if '1,500건' in err else j['window']
            c.execute("UPDATE smartstore_order_job SET state='error',error=?,next_sync=?,claim='',claimed=0,window=? WHERE ws=? AND agent=?",(err,t+600,window,ws,a))
        else:
            for x in items:
                c.execute('INSERT INTO smartstore_order_state VALUES(?,?,?,?,?,?) ON CONFLICT(ws,agent,reference) DO UPDATE SET changed_at=excluded.changed_at,content=excluded.content,updated=excluded.updated WHERE excluded.changed_at>=smartstore_order_state.changed_at',(ws,a,x['reference'],x['changed_at'],dump(x),t))
            c.execute("UPDATE smartstore_order_job SET state='synced',error='',cursor=?,last_sync=?,next_sync=?,claim='',claimed=0,window=? WHERE ws=? AND agent=?",(end,t,t+(10 if end<t-120 else INTERVAL),min(3600,j['window']*2),ws,a))
    return True

@app.get('/api/commerce/smartstore/order-sync/records')
def records(agent:str='',page:int=1,ws=Depends(ident)):
    require(1<=page<=200,'페이지 오류',422)
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False)
        data=rows(c,'SELECT content FROM smartstore_order_state WHERE ws=? AND agent=? AND updated>=? ORDER BY changed_at DESC,reference LIMIT 100 OFFSET ?',(ws,agent,now()-RETENTION,(page-1)*100))
        return {**view(c,ws,agent),'records':[loads(x['content']) for x in data]}

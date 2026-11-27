"""Bounded read-only product synchronization. No LLM calls or education debit."""
import os,re
from fastapi import Depends,HTTPException
from app import app,ident,require,bounded,limit
from store import *
import commerce,ops
from google_calendar import encryption
from integrations import smartstore_transport as ss

INTERVAL=21600
STALE=86400

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS smartstore_connection(ws TEXT NOT NULL,agent TEXT NOT NULL,client_id TEXT NOT NULL,credential TEXT NOT NULL,revision TEXT NOT NULL,active INTEGER NOT NULL,state TEXT NOT NULL,error TEXT NOT NULL,last_sync INTEGER NOT NULL,next_sync INTEGER NOT NULL,claimed INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS smartstore_product(ws TEXT NOT NULL,agent TEXT NOT NULL,product_id TEXT NOT NULL,name TEXT NOT NULL,price INTEGER NOT NULL,stock INTEGER NOT NULL,details TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,product_id));
        CREATE INDEX IF NOT EXISTS smartstore_due ON smartstore_connection(active,next_sync);
        """)
init()

def configured():return os.getenv('ENABLE_SMARTSTORE_SYNC')=='1' and bool(os.getenv('INTEGRATION_ENCRYPTION_KEY'))
def view(c,ws,agent):
    row=one(c,'SELECT active,state,error,last_sync,next_sync FROM smartstore_connection WHERE ws=? AND agent=?',(ws,agent))
    return {'available':configured(),'saved':bool(row),'active':bool(row and row['active']),'state':row['state'] if row else 'not_connected','error':row['error'] if row else '','last_sync':row['last_sync'] if row else 0,'next_sync':row['next_sync'] if row else 0,'count':one(c,'SELECT COUNT(*) n FROM smartstore_product WHERE ws=? AND agent=?',(ws,agent))['n'],'education_credits':0,'auto_interval_hours':6,'limit':2000}

def valid_scope(c,ws,agent):
    try:commerce.access(c,ws,agent,True);return True
    except HTTPException:return False

def run_one(ws=None,agent=None):
    if not configured():return False
    with db(True) as c:
        c.execute("UPDATE smartstore_connection SET state='error',error='이전 동기화 시간 초과',next_sync=?,claimed=0 WHERE state='running' AND claimed<?",(now()+3600,now()-600))
        q="SELECT * FROM smartstore_connection WHERE active=1 AND state<>'running' AND next_sync<=?";args=[now()]
        if ws is not None:q+=' AND ws=? AND agent=?';args.extend([ws,agent])
        row=one(c,q+' ORDER BY next_sync LIMIT 1',args)
        if not row:return False
        w,a=row['ws'],row['agent']
        if not valid_scope(c,w,a):
            c.execute("UPDATE smartstore_connection SET active=0,state='paused',error='판매 관리 또는 브랜드 권한 없음' WHERE ws=? AND agent=?",(w,a));return True
        claim=uid()
        c.execute("UPDATE smartstore_connection SET state='running',claimed=?,revision=? WHERE ws=? AND agent=?",(now(),claim,w,a))
    try:
        client=ss.access_token(row['client_id'],encryption().decrypt(row['credential'].encode()).decode())
        items=ss.product_catalog(client);err=''
    except ss.SmartStoreError as e:items=None;err=str(e)[:150]
    except Exception:items=None;err='인증 또는 공급자 연결 확인 필요'
    with db(True) as c:
        current=one(c,'SELECT revision,active,state FROM smartstore_connection WHERE ws=? AND agent=?',(w,a))
        if not current or current['revision']!=claim or not current['active'] or current['state']!='running':return True
        if not valid_scope(c,w,a):
            c.execute("UPDATE smartstore_connection SET active=0,state='paused',claimed=0 WHERE ws=? AND agent=?",(w,a));return True
        if items is None:c.execute("UPDATE smartstore_connection SET state='error',error=?,next_sync=?,claimed=0 WHERE ws=? AND agent=?",(err,now()+3600,w,a))
        else:
            stamp=now()
            c.execute('DELETE FROM smartstore_product WHERE ws=? AND agent=?',(w,a))
            for x in items:c.execute('INSERT INTO smartstore_product VALUES(?,?,?,?,?,?,?,?)',(w,a,x['id'],x['name'],x['price'],x['stock'],dump(x),stamp))
            c.execute('DELETE FROM smartstore_detail WHERE ws=? AND agent=? AND NOT EXISTS(SELECT 1 FROM smartstore_product p WHERE p.ws=smartstore_detail.ws AND p.agent=smartstore_detail.agent AND p.product_id=smartstore_detail.product_id)',(w,a))
            c.execute("UPDATE smartstore_connection SET state='synced',error='',last_sync=?,next_sync=?,claimed=0 WHERE ws=? AND agent=?",(stamp,stamp+INTERVAL,w,a))
    return True

def tick():return run_one()

def candidates(c,ws,agent):
    # A failed refresh leaves the last successful snapshot intact but it ages out.
    if not configured():return []
    row=one(c,'SELECT active,last_sync FROM smartstore_connection WHERE ws=? AND agent=?',(ws,agent))
    if not row or not row['active'] or row['last_sync']<now()-STALE:return []
    result=[]
    for p in rows(c,'SELECT details,updated FROM smartstore_product WHERE ws=? AND agent=? ORDER BY product_id',(ws,agent)):
        x=loads(p['details'])
        # No live-stock guarantee. Omit raw stock and use source time.
        result.append({'name':x['name'],'variant':'','price':x['price'],'url':'','description':'','source':'smartstore','product_id':x['id'],'discount':x['discount'],'availability':x['status'],'category':x['category'],'fees':x['facts'],'as_of':p['updated']})
    return result

@app.get('/api/commerce/smartstore')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False)
        return view(c,ws,agent)

@app.post('/api/commerce/smartstore/connect')
def connect(body:dict,agent:str='',ws=Depends(ident)):
    require(configured(),'스마트스토어 상품 연동 서버 비활성화',503)
    require(body.get('confirmed') is True,'읽기 전용 연동 및 6시간 동기화 동의 필요',422)
    cid=bounded(body.get('client_id',''),55);secret=bounded(body.get('client_secret',''),100)
    limit('smartstore-connect:'+ws,5,60)
    with db() as c:commerce.access(c,ws,agent,True)
    try:
        token=ss.access_token(cid,secret)
        # Verify product read permission without sending any data to an AI.
        d=ss.read_json(token,'/v1/products/search',{'page':1,'size':1,'productStatusTypes':['SALE','OUTOFSTOCK']})
        require(isinstance(d.get('contents'),list),'상품 조회 권한 확인 실패',422)
        encrypted=encryption().encrypt(secret.encode()).decode()
    except ss.SmartStoreError as e:require(False,str(e),422)
    with db(True) as c:
        commerce.access(c,ws,agent,True)
        c.execute('DELETE FROM smartstore_detail WHERE ws=? AND agent=?',(ws,agent))
        c.execute('DELETE FROM smartstore_product WHERE ws=? AND agent=?',(ws,agent))
        c.execute("INSERT INTO smartstore_connection VALUES(?,?,?,?,?,1,'queued','',0,?,0) ON CONFLICT(ws,agent) DO UPDATE SET client_id=excluded.client_id,credential=excluded.credential,revision=excluded.revision,active=1,state='queued',error='',last_sync=0,next_sync=excluded.next_sync,claimed=0",(ws,agent,cid,encrypted,uid(),now()))
        return view(c,ws,agent)

@app.post('/api/commerce/smartstore/sync')
def sync(agent:str='',ws=Depends(ident)):
    require(configured(),'상품 동기화 비활성화',503);limit('smartstore-sync:'+ws,3,60)
    with db(True) as c:
        commerce.access(c,ws,agent,True)
        row=one(c,'SELECT active,state FROM smartstore_connection WHERE ws=? AND agent=?',(ws,agent))
        require(row and row['active'],'연결 필요',409);require(row['state']!='running','동기화 중',409)
        c.execute("UPDATE smartstore_connection SET state='queued',next_sync=? WHERE ws=? AND agent=?",(now(),ws,agent))
    # Worker performs the actual bounded fetch outside request transactions.
    with db() as c:return view(c,ws,agent)

@app.post('/api/commerce/smartstore/disconnect')
def disconnect(agent:str='',ws=Depends(ident)):
    with db(True) as c:
        ops.work_scope(c,getw(c,ws),agent)
        c.execute('DELETE FROM smartstore_connection WHERE ws=? AND agent=?',(ws,agent))
        c.execute('DELETE FROM smartstore_detail WHERE ws=? AND agent=?',(ws,agent))
        c.execute('DELETE FROM smartstore_product WHERE ws=? AND agent=?',(ws,agent))
    return {'ok':True}

@app.get('/api/commerce/smartstore/products')
def products(agent:str='',page:int=1,ws=Depends(ident)):
    require(1<=page<=20,'페이지 오류',422)
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False)
        return {'products':[{**loads(x['details']),'as_of':x['updated']} for x in rows(c,'SELECT details,updated FROM smartstore_product WHERE ws=? AND agent=? ORDER BY name,product_id LIMIT 100 OFFSET ?',(ws,agent,(page-1)*100))],**view(c,ws,agent)}

@app.post('/api/commerce/smartstore/order-status')
def order_status(body:dict,agent:str='',ws=Depends(ident)):
    require(configured(),'스마트스토어 조회 비활성화',503)
    require(body.get('confirmed') is True,'사업주 주문 조회 확인 필요',422);ref=bounded(body.get('reference',''),32)
    limit('smartstore-order:'+ws,10,60)
    with db() as c:
        commerce.access(c,ws,agent,True)
        row=one(c,'SELECT * FROM smartstore_connection WHERE ws=? AND agent=? AND active=1',(ws,agent))
        require(row,'스마트스토어 연결 필요',409)
    try:
        token=ss.access_token(row['client_id'],encryption().decrypt(row['credential'].encode()).decode())
        result=ss.order_status(token,ref)
    except ss.SmartStoreError as e:require(False,str(e),422)
    with db() as c:
        commerce.access(c,ws,agent,True)
        current=one(c,'SELECT client_id,credential,active FROM smartstore_connection WHERE ws=? AND agent=?',(ws,agent))
        require(current and current['active'] and current['client_id']==row['client_id'] and current['credential']==row['credential'],'연결 변경됨',409)
    return result

"""Opt-in, credit-free approved product catalog snapshots; no assumed price or stock."""
import os
from fastapi import Depends,HTTPException
from app import app,ident,require,limit
from store import *
import commerce,coupang_connection as cc
from google_calendar import encryption
from integrations import coupang_transport as cp

INTERVAL=21600
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS coupang_catalog_job(ws TEXT NOT NULL,agent TEXT NOT NULL,active INTEGER NOT NULL,state TEXT NOT NULL,error TEXT NOT NULL,last_sync INTEGER NOT NULL,next_sync INTEGER NOT NULL,claim TEXT NOT NULL,claimed INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS coupang_catalog_product(ws TEXT NOT NULL,agent TEXT NOT NULL,product_id TEXT NOT NULL,details TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,product_id));
        """)
init()

def configured():return cc.configured() and os.getenv('ENABLE_COUPANG_CATALOG')=='1'

def connection(c,ws,agent):
    return one(c,'SELECT vendor,credential FROM coupang_connection WHERE ws=? AND agent=?',(ws,agent))

def view(c,ws,agent):
    r=one(c,'SELECT active,state,error,last_sync,next_sync FROM coupang_catalog_job WHERE ws=? AND agent=?',(ws,agent))
    return {'available':configured(),'connected':bool(connection(c,ws,agent)),'active':bool(r and r['active']),'state':r['state'] if r else 'disabled','error':r['error'] if r else '', 'last_sync':r['last_sync'] if r else 0,'count':one(c,'SELECT COUNT(*) n FROM coupang_catalog_product WHERE ws=? AND agent=?',(ws,agent))['n'],'education_credits':0}

def clear(c,ws,agent):
    import coupang_detail
    coupang_detail.clear(c,ws,agent)
    c.execute('DELETE FROM coupang_catalog_job WHERE ws=? AND agent=?',(ws,agent))
    c.execute('DELETE FROM coupang_catalog_product WHERE ws=? AND agent=?',(ws,agent))

@app.get('/api/commerce/coupang/catalog')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False);return view(c,ws,agent)

@app.post('/api/commerce/coupang/catalog')
def enable(body:dict,agent:str='',ws=Depends(ident)):
    flag=body.get('enabled');require(type(flag) is bool,'설정 오류',422)
    require(not flag or configured(),'쿠팡 상품 수집 비활성화',503)
    limit('cp-catalog:'+ws,3,60)
    with db(True) as c:
        commerce.access(c,ws,agent,True);require(connection(c,ws,agent),'쿠팡 연결 필요',409)
        if not flag:clear(c,ws,agent)
        else:
            old=one(c,'SELECT state FROM coupang_catalog_job WHERE ws=? AND agent=?',(ws,agent))
            require(not old or old['state']!='running','동기화 중',409)
            c.execute("INSERT INTO coupang_catalog_job VALUES(?,?,1,'queued','',0,?,'',0) ON CONFLICT(ws,agent) DO UPDATE SET active=1,state='queued',error='',next_sync=excluded.next_sync,claim='',claimed=0",(ws,agent,now()))
        return view(c,ws,agent)

def valid(c,ws,agent):
    try:commerce.access(c,ws,agent,True);return connection(c,ws,agent)
    except HTTPException:return None

def tick():
    if not configured():return False
    with db(True) as c:
        c.execute("UPDATE coupang_catalog_job SET state='error',error='동기화 시간 초과',next_sync=?,claim='',claimed=0 WHERE state='running' AND claimed<?",(now()+3600,now()-600))
        j=one(c,"SELECT * FROM coupang_catalog_job WHERE active=1 AND state<>'running' AND next_sync<=? ORDER BY next_sync LIMIT 1",(now(),))
        if not j:return False
        ws,a=j['ws'],j['agent'];conn=valid(c,ws,a)
        if not conn:clear(c,ws,a);return True
        claim=uid()
        c.execute("UPDATE coupang_catalog_job SET state='running',claim=?,claimed=? WHERE ws=? AND agent=?",(claim,now(),ws,a))
    try:
        keys=loads(encryption().decrypt(conn['credential'].encode()).decode())
        items=cp.product_catalog(conn['vendor'],keys['access'],keys['secret']);err=''
    except cp.CoupangError as e:items=None;err=str(e)[:150]
    except Exception:items=None;err='API 인증 확인 필요'
    with db(True) as c:
        j=one(c,'SELECT active,claim,state FROM coupang_catalog_job WHERE ws=? AND agent=?',(ws,a))
        if not j or not j['active'] or j['claim']!=claim or j['state']!='running':return True
        if valid(c,ws,a)!=conn:clear(c,ws,a);return True
        if items is None:c.execute("UPDATE coupang_catalog_job SET state='error',error=?,next_sync=?,claim='',claimed=0 WHERE ws=? AND agent=?",(err,now()+3600,ws,a))
        else:
            stamp=now();c.execute('DELETE FROM coupang_catalog_product WHERE ws=? AND agent=?',(ws,a))
            for x in items:c.execute('INSERT INTO coupang_catalog_product VALUES(?,?,?,?,?)',(ws,a,x['id'],dump(x),stamp))
            import coupang_detail
            coupang_detail.prune(c,ws,a)
            c.execute("UPDATE coupang_catalog_job SET state='synced',error='',last_sync=?,next_sync=?,claim='',claimed=0 WHERE ws=? AND agent=?",(stamp,stamp+INTERVAL,ws,a))
    return True

def candidates(c,ws,agent):
    if not configured() or not connection(c,ws,agent):return []
    j=one(c,'SELECT active,last_sync FROM coupang_catalog_job WHERE ws=? AND agent=?',(ws,agent))
    if not j or not j['active'] or j['last_sync']<now()-86400:return []
    result=[]
    for row in rows(c,'SELECT details,updated FROM coupang_catalog_product WHERE ws=? AND agent=? ORDER BY product_id',(ws,agent)):
        x=loads(row['details'])
        result.append({'name':x['name'],'source':'coupang','product_id':x['id'],'public_id':x['public_id'],'as_of':row['updated'],'price':None,'description':'','variant':'','url':''})
    return result

@app.get('/api/commerce/coupang/catalog/products')
def products(agent:str='',page:int=1,ws=Depends(ident)):
    require(1<=page<=20,'페이지 오류',422)
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False)
        return {**view(c,ws,agent),'products':[loads(x['details']) for x in rows(c,'SELECT details FROM coupang_catalog_product WHERE ws=? AND agent=? ORDER BY product_id LIMIT 100 OFFSET ?',(ws,agent,(page-1)*100))]}

"""Read-only Coupang seller connection. Explicit setup and no customer exposure."""
import os
from fastapi import Depends
from app import app,ident,require,bounded,limit
from store import *
import commerce,ops
from google_calendar import encryption
from integrations import coupang_transport as cp

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS coupang_connection(ws TEXT NOT NULL,agent TEXT NOT NULL,vendor TEXT NOT NULL,credential TEXT NOT NULL,verified INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        """)
init()
def configured():return os.getenv('ENABLE_COUPANG_READ')=='1' and bool(os.getenv('INTEGRATION_ENCRYPTION_KEY'))

@app.get('/api/commerce/coupang')
def status(agent:str='',ws=Depends(ident)):
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False)
        r=one(c,'SELECT vendor,verified FROM coupang_connection WHERE ws=? AND agent=?',(ws,agent))
        return {'available':configured(),'connected':bool(r),'vendor':r['vendor'] if r else '', 'verified':r['verified'] if r else 0,'auto_sync':False}

@app.post('/api/commerce/coupang/connect')
def connect(body:dict,agent:str='',ws=Depends(ident)):
    require(configured(),'쿠팡 조회 서버 비활성화',503)
    require(body.get('confirmed') is True,'읽기 전용 조회와 암호화 저장 동의 필요',422)
    vendor=bounded(body.get('vendor',''),30);access=bounded(body.get('access_key',''),200);secret=bounded(body.get('secret_key',''),200);ref=bounded(body.get('reference',''),32)
    limit('coupang-connect:'+ws,5,60)
    with db() as c:commerce.access(c,ws,agent,True)
    try:cp.order_status(vendor,access,secret,ref)
    except cp.CoupangError as e:require(False,str(e),422)
    encrypted=encryption().encrypt(dump({'access':access,'secret':secret}).encode()).decode()
    with db(True) as c:
        commerce.access(c,ws,agent,True)
        import coupang_catalog
        coupang_catalog.clear(c,ws,agent)
        c.execute('INSERT INTO coupang_connection VALUES(?,?,?,?,?) ON CONFLICT(ws,agent) DO UPDATE SET vendor=excluded.vendor,credential=excluded.credential,verified=excluded.verified',(ws,agent,vendor,encrypted,now()))
    return {'connected':True,'vendor':vendor}

@app.post('/api/commerce/coupang/order-status')
def lookup(body:dict,agent:str='',ws=Depends(ident)):
    require(configured(),'쿠팡 조회 비활성화',503);require(body.get('confirmed') is True,'사업주 조회 확인 필요',422)
    ref=bounded(body.get('reference',''),32);limit('coupang-order:'+ws,10,60)
    with db() as c:
        commerce.access(c,ws,agent,True)
        r=one(c,'SELECT vendor,credential FROM coupang_connection WHERE ws=? AND agent=?',(ws,agent));require(r,'쿠팡 연결 필요',409)
    try:
        keys=loads(encryption().decrypt(r['credential'].encode()).decode())
        result=cp.order_status(r['vendor'],keys['access'],keys['secret'],ref)
    except cp.CoupangError as e:require(False,str(e),422)
    with db() as c:
        commerce.access(c,ws,agent,True);require(one(c,'SELECT vendor,credential FROM coupang_connection WHERE ws=? AND agent=?',(ws,agent))==r,'연결 변경됨',409)
    return result

@app.post('/api/commerce/coupang/disconnect')
def disconnect(agent:str='',ws=Depends(ident)):
    with db(True) as c:
        ops.work_scope(c,getw(c,ws),agent)
        import coupang_catalog
        coupang_catalog.clear(c,ws,agent)
        c.execute('DELETE FROM coupang_connection WHERE ws=? AND agent=?',(ws,agent))
    return {'ok':True}

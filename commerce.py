"""Brand-scoped manual commerce records. No provider, payment or refund execution."""
from urllib.parse import urlsplit
import re
from fastapi import Depends
from app import app,ident,require,bounded,visitor,limit
from store import *
import ops
CHANNELS={'smartstore','coupang','cafe24','imweb','shopify','11st','gmarket','auction','own','other'}
ORDER_STATES={'received','preparing','shipped','delivered','cancelled'}
REQUEST_KINDS={'delivery','exchange','return','refund','defect','restock','other'}
REQUEST_STATES={'pending','review','resolved','rejected'}

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS commerce_settings(ws TEXT NOT NULL,agent TEXT NOT NULL,enabled INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS commerce_product(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,sku TEXT NOT NULL,name TEXT NOT NULL,variant TEXT NOT NULL,price INTEGER NOT NULL CHECK(price>=0),stock INTEGER NOT NULL CHECK(stock>=0),url TEXT NOT NULL,description TEXT NOT NULL,published INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,agent,sku));
        CREATE TABLE IF NOT EXISTS commerce_order(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,channel TEXT NOT NULL,reference TEXT NOT NULL,product TEXT NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0),amount INTEGER NOT NULL CHECK(amount>=0),state TEXT NOT NULL,carrier TEXT NOT NULL,tracking TEXT NOT NULL,created INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,agent,channel,reference));
        CREATE TABLE IF NOT EXISTS commerce_request(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,client TEXT NOT NULL,kind TEXT NOT NULL,channel TEXT NOT NULL,reference TEXT NOT NULL,details TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,thread,client));
        CREATE INDEX IF NOT EXISTS commerce_product_scope ON commerce_product(ws,agent,published);
        CREATE INDEX IF NOT EXISTS commerce_order_scope ON commerce_order(ws,agent,created);
        CREATE INDEX IF NOT EXISTS commerce_request_scope ON commerce_request(ws,agent,state,created);
        """)
init()

def enabled(c,ws,agent):
    r=one(c,'SELECT enabled FROM commerce_settings WHERE ws=? AND agent=?',(ws,agent))
    return bool(r and r['enabled'])

def access(c,ws,agent,write=False,need_enabled=True):
    w=getw(c,ws);ops.work_scope(c,w,agent,write);require(public_access(w),'유료 상담 또는 체험 이용 권한 필요',403)
    if need_enabled:require(enabled(c,ws,agent),'판매 관리 활성화 필요',409)
    return w

def public_enabled(c,w,agent):
    if not public_access(w):return False
    aid=agent['id'] if agent else ''
    return enabled(c,w['id'],aid) and bool(agent['enabled'] if agent else w['enabled']) and (not aid or not one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(w['id'],aid)))

def public_products(c,ws,agent):
    return rows(c,'SELECT name,variant,price,url,description FROM commerce_product WHERE ws=? AND agent=? AND published=1 ORDER BY name,variant LIMIT 100',(ws,agent))

def chat_products(c,w,agent,msg):
    if not public_enabled(c,w,agent):return []
    from smartstore_sync import candidates
    from coupang_catalog import candidates as cp_candidates
    aid=agent['id'] if agent else ''
    all_items=rows(c,'SELECT name,variant,price,url,description FROM commerce_product WHERE ws=? AND agent=? AND published=1',(w['id'],aid))+candidates(c,w['id'],aid)+cp_candidates(c,w['id'],aid)
    from product_education import enrich
    selected=rank_products(all_items,msg)
    from coupang_detail import enrich as cp_enrich
    return [{**p,**enrich(c,w['id'],aid,p['product_id'])} if p.get('source')=='smartstore' else {**p,**cp_enrich(c,w['id'],aid,p['product_id'])} if p.get('source')=='coupang' else p for p in selected]

def rank_products(items,msg):
    def norm(x):return re.sub(r'[^\w]','',x.lower())
    query=norm(msg);words={norm(x) for x in re.findall(r'[\w]+',msg) if len(x)>=2}
    def score(p):
        title=norm(p['name'])
        if not title:return 0
        if p.get('product_id') and p['product_id'] in re.findall(r'[0-9]+',msg):return 200
        if title in query:return 100+min(len(title),50)
        overlap=sum(len(x) for x in words if len(x)>=2 and x in title and x not in {'상품','가격','배송','얼마','재고','문의','제품','있나요'})
        return overlap if overlap>=2 else 0
    ranked=sorted(((score(p),p) for p in items),key=lambda x:x[0],reverse=True)
    # Keep context bounded regardless of catalog size.
    return [p for s,p in ranked[:3] if s>0]

def int_value(body,k,minimum,maximum):
    n=body.get(k);require(type(n) is int and minimum<=n<=maximum,'숫자 범위 오류: '+k,422);return n

def channel(body):
    ch=body.get('channel');require(isinstance(ch,str) and ch in CHANNELS,'판매처 오류',422);return ch

def valid_url(s):
    if not s:return True
    try:
        p=urlsplit(s)
        return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password and not any(x.isspace() for x in s)
    except ValueError:return False

@app.get('/api/commerce')
def overview(agent:str='',ws=Depends(ident)):
    with db() as c:
        access(c,ws,agent,need_enabled=False)
        return {'enabled':enabled(c,ws,agent),'products':rows(c,'SELECT * FROM commerce_product WHERE ws=? AND agent=? ORDER BY updated DESC LIMIT 500',(ws,agent)), 'orders':rows(c,'SELECT * FROM commerce_order WHERE ws=? AND agent=? ORDER BY created DESC LIMIT 200',(ws,agent)), 'requests':rows(c,'SELECT * FROM commerce_request WHERE ws=? AND agent=? ORDER BY created DESC LIMIT 200',(ws,agent))}

@app.post('/api/commerce/settings')
def settings(body:dict,agent:str='',ws=Depends(ident)):
    require(type(body.get('enabled')) is bool,'설정 오류',422)
    with db(True) as c:
        access(c,ws,agent,True,False)
        c.execute('INSERT INTO commerce_settings VALUES(?,?,?) ON CONFLICT(ws,agent) DO UPDATE SET enabled=excluded.enabled',(ws,agent,int(body['enabled'])))
    return {'ok':True}

@app.post('/api/commerce/products')
def save_product(body:dict,agent:str='',ws=Depends(ident)):
    i=bounded(body.get('id',''),100);sku=bounded(body.get('sku',''),80);name=bounded(body.get('name',''),120);variant=bounded(body.get('variant',''),120);url=bounded(body.get('url',''),500);desc=bounded(body.get('description',''),1000);price=int_value(body,'price',0,100000000);stock=int_value(body,'stock',0,1000000);published=body.get('published',False)
    require(sku and name and valid_url(url) and type(published) is bool,'상품명·SKU·HTTPS 링크 확인 필요',422)
    with db(True) as c:
        access(c,ws,agent,True)
        old=one(c,'SELECT id FROM commerce_product WHERE ws=? AND agent=? AND id=?',(ws,agent,i)) if i else None
        require(not i or old,'상품 없음',404)
        require(not one(c,'SELECT id FROM commerce_product WHERE ws=? AND agent=? AND sku=? AND id<>?',(ws,agent,sku,i)),'이미 등록된 SKU',409)
        if i:c.execute('UPDATE commerce_product SET sku=?,name=?,variant=?,price=?,stock=?,url=?,description=?,published=?,updated=? WHERE ws=? AND agent=? AND id=?',(sku,name,variant,price,stock,url,desc,int(published),now(),ws,agent,i))
        else:
            require(one(c,'SELECT COUNT(*) n FROM commerce_product WHERE ws=? AND agent=?',(ws,agent))['n']<500,'상품 최대 500개',409);i=uid()
            c.execute('INSERT INTO commerce_product VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,agent,sku,name,variant,price,stock,url,desc,int(published),now()))
    return {'id':i}

@app.post('/api/commerce/orders')
def save_order(body:dict,agent:str='',ws=Depends(ident)):
    i=bounded(body.get('id',''),100);ch=channel(body);ref=bounded(body.get('reference',''),120);product=bounded(body.get('product',''),200);qty=int_value(body,'quantity',1,100000);amount=int_value(body,'amount',0,1000000000);state=body.get('state','received');carrier=bounded(body.get('carrier',''),80);tracking=bounded(body.get('tracking',''),100)
    require(ref and product and isinstance(state,str) and state in ORDER_STATES,'주문 정보 오류',422)
    with db(True) as c:
        access(c,ws,agent,True)
        old=one(c,'SELECT id FROM commerce_order WHERE ws=? AND agent=? AND id=?',(ws,agent,i)) if i else None
        require(not i or old,'주문 없음',404)
        require(not one(c,'SELECT id FROM commerce_order WHERE ws=? AND agent=? AND channel=? AND reference=? AND id<>?',(ws,agent,ch,ref,i)),'이미 등록된 판매처 주문번호',409)
        if i:c.execute('UPDATE commerce_order SET channel=?,reference=?,product=?,quantity=?,amount=?,state=?,carrier=?,tracking=?,updated=? WHERE ws=? AND agent=? AND id=?',(ch,ref,product,qty,amount,state,carrier,tracking,now(),ws,agent,i))
        else:
            i=uid();c.execute('INSERT INTO commerce_order VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,agent,ch,ref,product,qty,amount,state,carrier,tracking,now(),now()))
    return {'id':i}

@app.patch('/api/commerce/requests/{i}')
def review(i:str,body:dict,agent:str='',ws=Depends(ident)):
    state=body.get('state');require(isinstance(state,str) and state in REQUEST_STATES,'상태 오류',422)
    with db(True) as c:
        access(c,ws,agent,True)
        require(one(c,'SELECT id FROM commerce_request WHERE ws=? AND agent=? AND id=?',(ws,agent,i)),'요청 없음',404)
        c.execute('UPDATE commerce_request SET state=?,updated=? WHERE ws=? AND agent=? AND id=?',(state,now(),ws,agent,i))
    return {'ok':True}

@app.get('/api/customer/commerce/{token}')
def customer_catalog(token:str):
    with db() as c:
        v=visitor(c,token,kind='public');w=getw(c,v['ws']);agent=ops.public_work_scope(c,w,v)
        require(enabled(c,v['ws'],agent),'판매 관리 비활성화',403)
        return {'products':public_products(c,v['ws'],agent)}

@app.post('/api/customer/commerce')
def customer_request(body:dict):
    token=bounded(body.get('token',''),100);client=bounded(body.get('client',''),100);kind=body.get('kind');ch=channel(body);ref=bounded(body.get('reference',''),120);details=bounded(body.get('details',''),1500)
    require(body.get('confirmed') is True and isinstance(kind,str) and kind in REQUEST_KINDS and client and details,'요청 내용과 고객 확인 필요',422)
    require(kind in ('restock','other') or ref,'주문번호 필요',422)
    limit('commerce:'+token,10,60)
    with db(True) as c:
        v=visitor(c,token,kind='public');ws=v['ws'];w=getw(c,ws);agent=ops.public_work_scope(c,w,v)
        require(enabled(c,ws,agent),'판매 관리 비활성화',403)
        t=one(c,"SELECT id FROM thread WHERE ws=? AND visitor=? AND kind='public'",(ws,token));require(t and ops.thread_brand(c,w,t['id'],True)==agent,'상담 없음',404)
        old=one(c,'SELECT id FROM commerce_request WHERE ws=? AND thread=? AND client=?',(ws,t['id'],client))
        if old:return {'id':old['id'],'duplicate':True}
        i=uid();c.execute('INSERT INTO commerce_request VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,agent,t['id'],client,kind,ch,ref,details,'pending',now(),now()))
        ops.event(c,ws,'work','온라인 판매 고객 확인 요청',i)
        return {'id':i,'duplicate':False}

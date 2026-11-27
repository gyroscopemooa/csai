"""Read-only, product-scoped public detail and explicitly requested inventory."""
from html import unescape
import re,hashlib
from fastapi import Depends
from app import app,ident,require,bounded,limit
from store import *
import ai,commerce,coupang_catalog as catalog
from google_calendar import encryption
from integrations import coupang_transport as cp
from product_education import PublicText

DETAIL_AGE=7*86400
STOCK_AGE=300
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS coupang_detail(ws TEXT NOT NULL,agent TEXT NOT NULL,product_id TEXT NOT NULL,content TEXT NOT NULL,fingerprint TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,product_id));
        CREATE TABLE IF NOT EXISTS coupang_inventory(ws TEXT NOT NULL,agent TEXT NOT NULL,product_id TEXT NOT NULL,item_id TEXT NOT NULL,content TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,product_id,item_id));
        """)
init()

def normalize(raw):
    items=raw.get('items')
    if not isinstance(items,list) or not 1<=len(items)<=200:raise cp.CoupangError('상품 옵션 목록 확인 필요')
    title=ai.clean(cp.text(raw.get('displayProductName'),200))
    variants=[];seen=set();description=[];size=0;images=0
    for item in items:
        if not isinstance(item,dict):raise cp.CoupangError('옵션 형식 오류')
        iid=item.get('vendorItemId')
        if type(iid) is not int or iid<=0:continue
        if iid in seen:raise cp.CoupangError('중복 옵션')
        seen.add(iid)
        attrs=[]
        for a in item.get('attributes') or []:
            if isinstance(a,dict) and a.get('exposed')=='EXPOSED':
                name=ai.clean(cp.text(a.get('attributeTypeName'),80));value=ai.clean(cp.text(a.get('attributeValueName'),120))
                if name and value:attrs.append({'name':name,'value':value})
        # Do not expose supply price, internal SKU, hidden attributes or raw seller item name.
        label=' / '.join(a['value'] for a in attrs[:10]) or '옵션 '+str(iid)
        variants.append({'id':str(iid),'name':label,'attributes':attrs[:10]})
        for group in item.get('contents') or []:
            if not isinstance(group,dict):continue
            for part in group.get('contentDetails') or []:
                if not isinstance(part,dict):continue
                if part.get('detailType')=='IMAGE':images+=1;continue
                if part.get('detailType')!='TEXT' or size>=30000:continue
                parser=PublicText();parser.feed(unescape(cp.text(part.get('content'),1000000)));parser.close()
                images+=parser.images
                text=ai.clean(''.join(parser.parts).strip())[:min(30000-size,4000)]
                if text and text not in description:description.append(text);size+=len(text)
    if not variants:raise cp.CoupangError('승인된 옵션 없음')
    fees={}
    for k in ('deliveryCharge','freeShipOverAmount','deliveryChargeOnReturn','returnCharge'):
        v=raw.get(k)
        if type(v) is int and 0<=v<=100000000:fees[k]=v
    return {'name':title,'variants':variants,'text':'\n'.join(description),'fees':fees,'image_count':images}

def get_product(c,ws,a,pid):
    require(cp.positive_id(pid),'등록상품번호 오류',422)
    row=one(c,'SELECT * FROM coupang_catalog_product WHERE ws=? AND agent=? AND product_id=?',(ws,a,pid));require(row,'수집된 상품 없음',404)
    return row

def detail(c,ws,a,pid):
    return one(c,'SELECT * FROM coupang_detail WHERE ws=? AND agent=? AND product_id=?',(ws,a,pid))

def keys(conn):
    k=loads(encryption().decrypt(conn['credential'].encode()).decode())
    return conn['vendor'],k['access'],k['secret']

def scope(c,ws,a,pid,write=False):
    commerce.access(c,ws,a,write)
    require(catalog.configured(),'쿠팡 상품 연동 비활성화',503)
    get_product(c,ws,a,pid);conn=catalog.connection(c,ws,a)
    require(conn,'쿠팡 연결 필요',409)
    return conn

@app.get('/api/commerce/coupang/catalog/products/{pid}/detail')
def view(pid:str,agent:str='',ws=Depends(ident)):
    with db() as c:
        scope(c,ws,agent,pid);r=detail(c,ws,agent,pid)
        if not r:return {'collected':False}
        return {'collected':True,'content':loads(r['content']),'updated':r['updated'],'stale':r['updated']<now()-DETAIL_AGE}

@app.post('/api/commerce/coupang/catalog/products/{pid}/detail')
def collect(pid:str,agent:str='',ws=Depends(ident)):
    limit('cp-detail:'+ws,15,60)
    with db() as c:conn=scope(c,ws,agent,pid,True)
    try:data=normalize(cp.product_detail(*keys(conn),pid))
    except cp.CoupangError as e:require(False,str(e),422)
    fp=hashlib.sha256(dump(data).encode()).hexdigest()
    with db(True) as c:
        require(scope(c,ws,agent,pid,True)==conn,'연결 변경됨',409)
        old=detail(c,ws,agent,pid)
        if not old or old['fingerprint']!=fp:c.execute('DELETE FROM coupang_inventory WHERE ws=? AND agent=? AND product_id=?',(ws,agent,pid))
        c.execute('INSERT INTO coupang_detail VALUES(?,?,?,?,?,?) ON CONFLICT(ws,agent,product_id) DO UPDATE SET content=excluded.content,fingerprint=excluded.fingerprint,updated=excluded.updated',(ws,agent,pid,dump(data),fp,now()))
    return {'collected':True,'content':data,'education_credits':0}

@app.post('/api/commerce/coupang/catalog/products/{pid}/inventory')
def lookup(pid:str,body:dict,agent:str='',ws=Depends(ident)):
    iid=bounded(body.get('item_id',''),32);limit('cp-inventory:'+ws,20,60)
    with db() as c:
        conn=scope(c,ws,agent,pid,True);r=detail(c,ws,agent,pid)
        require(r and r['updated']>=now()-DETAIL_AGE and any(x['id']==iid for x in loads(r['content'])['variants']),'상품 상세정보 또는 옵션 확인 필요',409)
        fp=r['fingerprint']
    try:result=cp.inventory(*keys(conn),iid)
    except cp.CoupangError as e:require(False,str(e),422)
    with db(True) as c:
        require(scope(c,ws,agent,pid,True)==conn,'연결 변경됨',409)
        r=detail(c,ws,agent,pid);require(r and r['fingerprint']==fp,'상품 상세 변경됨',409)
        c.execute('INSERT INTO coupang_inventory VALUES(?,?,?,?,?,?) ON CONFLICT(ws,agent,product_id,item_id) DO UPDATE SET content=excluded.content,updated=excluded.updated',(ws,agent,pid,iid,dump(result),now()))
    return result

def enrich(c,ws,a,pid):
    r=detail(c,ws,a,pid)
    if not r or r['updated']<now()-DETAIL_AGE:return {}
    d=loads(r['content']);variants=d['variants'][:8]
    # Only selected public product data, with fresh inventory snapshots; no network I/O in chat transaction.
    snapshots={x['item_id']:loads(x['content']) for x in rows(c,'SELECT item_id,content FROM coupang_inventory WHERE ws=? AND agent=? AND product_id=? AND updated>=?',(ws,a,pid,now()-STOCK_AGE))}
    return {'display_name':d['name'],'description':d['text'][:1600],'detail_fees':d['fees'],'detail_as_of':r['updated'],'options':[{**v,'inventory':snapshots.get(v['id'])} for v in variants]}

def clear(c,ws,a):
    for table in ('coupang_inventory','coupang_detail'):c.execute('DELETE FROM '+table+' WHERE ws=? AND agent=?',(ws,a))

def prune(c,ws,a):
    for table in ('coupang_inventory','coupang_detail'):
        c.execute('DELETE FROM '+table+' WHERE ws=? AND agent=? AND NOT EXISTS(SELECT 1 FROM coupang_catalog_product p WHERE p.ws='+table+'.ws AND p.agent='+table+'.agent AND p.product_id='+table+'.product_id)',(ws,a))

"""Product-specific free text collection and opt-in paid analysis.
Existing training reservation/run/recovery machinery is reused; no automatic AI education.
"""
import hashlib,re
from html.parser import HTMLParser
from fastapi import Depends
from app import app,ident,require,bounded,limit
from store import *
import ai,commerce,smartstore_sync as sync
from google_calendar import encryption
from integrations import smartstore_transport as ss

GUIDANCE='이 상품에 관한 공개 상품 사실만 분석하세요. 상담 말투나 업체 전체 규칙을 변경하지 말고 상품명, 사용법, 특징, 옵션, 주의사항을 FAQ 또는 상품별 설명으로 정리하세요. 배송·가격·재고를 확정하지 마세요. 자료에 없는 내용은 추측하지 마세요.'
DETAIL_MAX=30000
DETAIL_AGE=7*86400

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS smartstore_detail(ws TEXT NOT NULL,agent TEXT NOT NULL,product_id TEXT NOT NULL,fingerprint TEXT NOT NULL,content TEXT NOT NULL,approved TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,product_id));
        CREATE TABLE IF NOT EXISTS product_training(ws TEXT NOT NULL,training TEXT PRIMARY KEY REFERENCES training(id),agent TEXT NOT NULL,product_id TEXT NOT NULL,fingerprint TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS product_training_scope ON product_training(ws,agent,product_id);
        """)
init()

class PublicText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[];self.hidden=0;self.images=0;self.n=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','iframe','object','svg','template'):self.hidden+=1
        if not self.hidden:
            if tag=='img':self.images+=1
            if tag in ('p','br','div','li','tr','h1','h2','h3'):self.handle_data('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style','iframe','object','svg','template'):self.hidden=max(0,self.hidden-1)
        if tag in ('p','div','li','tr'):self.handle_data('\n')
    def handle_data(self,data):
        if not self.hidden and self.n<DETAIL_MAX:
            part=data[:DETAIL_MAX-self.n];self.parts.append(part);self.n+=len(part)

def extract(origin):
    p=PublicText();p.feed(origin['detailContent'][:1_000_000]);p.close()
    text=ai.clean(re.sub(r'\n{3,}','\n\n',''.join(p.parts)).strip())[:DETAIL_MAX]
    # Only public policy values. Do not store seller address, phone, credentials or raw JSON.
    delivery=origin.get('deliveryInfo');delivery=delivery if isinstance(delivery,dict) else {}
    fee=delivery.get('deliveryFee');fee=fee if isinstance(fee,dict) else {}
    claim=delivery.get('claimDeliveryInfo');claim=claim if isinstance(claim,dict) else {}
    facts={}
    for field,val in [('deliveryType',delivery.get('deliveryType')),('deliveryFeeType',fee.get('deliveryFeeType')),('baseFee',fee.get('baseFee')),('freeConditionalAmount',fee.get('freeConditionalAmount')),('returnDeliveryFee',claim.get('returnDeliveryFee')),('exchangeDeliveryFee',claim.get('exchangeDeliveryFee'))]:
        if type(val) is int and 0<=val<=100000000:facts[field]=val
        elif field.endswith('Type') and isinstance(val,str) and re.fullmatch(r'[A-Z_]{1,60}',val):facts[field]=val
    content={'text':text,'fees':facts,'image_count':p.images,'truncated':p.n>=DETAIL_MAX or len(origin['detailContent'])>1_000_000}
    return content,hashlib.sha256(dump(content).encode()).hexdigest()

def get_product(c,ws,agent,pid):
    require(isinstance(pid,str) and re.fullmatch(r'[0-9]{1,32}',pid),'상품번호 오류',422)
    row=one(c,'SELECT name,details FROM smartstore_product WHERE ws=? AND agent=? AND product_id=?',(ws,agent,pid));require(row,'동기화된 상품 없음',404);return row

def detail_row(c,ws,agent,pid):
    return one(c,'SELECT * FROM smartstore_detail WHERE ws=? AND agent=? AND product_id=?',(ws,agent,pid))

def detail_view(row):
    if not row:return {'collected':False}
    return {'collected':True,'updated':row['updated'],'fingerprint':row['fingerprint'],'content':loads(row['content']),'educated':bool(row['approved']),'stale':row['updated']<now()-DETAIL_AGE}

@app.get('/api/commerce/smartstore/products/{pid}/detail')
def get_detail(pid:str,agent:str='',ws=Depends(ident)):
    with db() as c:
        commerce.access(c,ws,agent);p=get_product(c,ws,agent,pid)
        return {'product':p['name'],**detail_view(detail_row(c,ws,agent,pid))}

@app.post('/api/commerce/smartstore/products/{pid}/detail')
def collect(pid:str,agent:str='',ws=Depends(ident)):
    require(sync.configured(),'스마트스토어 상품 조회 비활성화',503);limit('product-detail:'+ws,15,60)
    with db() as c:
        commerce.access(c,ws,agent,True);p=get_product(c,ws,agent,pid)
        conn=one(c,'SELECT client_id,credential FROM smartstore_connection WHERE ws=? AND agent=? AND active=1',(ws,agent));require(conn,'연결 필요',409)
    try:
        token=ss.access_token(conn['client_id'],encryption().decrypt(conn['credential'].encode()).decode())
        content,fp=extract(ss.product_detail(token,pid))
    except ss.SmartStoreError as e:require(False,str(e),422)
    with db(True) as c:
        commerce.access(c,ws,agent,True);get_product(c,ws,agent,pid)
        current=one(c,'SELECT client_id,credential FROM smartstore_connection WHERE ws=? AND agent=? AND active=1',(ws,agent));require(current==conn,'연결 변경됨',409)
        old=detail_row(c,ws,agent,pid)
        approved=old['approved'] if old and old['fingerprint']==fp else ''
        c.execute('INSERT INTO smartstore_detail VALUES(?,?,?,?,?,?,?) ON CONFLICT(ws,agent,product_id) DO UPDATE SET fingerprint=excluded.fingerprint,content=excluded.content,approved=excluded.approved,updated=excluded.updated',(ws,agent,pid,fp,dump(content),approved,now()))
        return {'product':p['name'],'changed':bool(old and old['fingerprint']!=fp),'education_credits':0,**detail_view(detail_row(c,ws,agent,pid))}

@app.post('/api/commerce/smartstore/products/{pid}/education')
def estimate(pid:str,body:dict,agent:str='',ws=Depends(ident)):
    require(body.get('confirmed') is True,'상품 자료 이용 권한 확인 필요',422)
    ids=body.get('files',[]);require(isinstance(ids,list) and len(ids)<=4 and all(isinstance(i,str) and len(i)<=100 for i in ids),'상품 이미지 파일 최대 4개',422)
    with db(True) as c:
        w=commerce.access(c,ws,agent,True);p=get_product(c,ws,agent,pid);row=detail_row(c,ws,agent,pid)
        require(row and row['updated']>=now()-DETAIL_AGE,'상품 상세정보를 먼저 수집하세요.',409)
        content=loads(row['content']);text='상품명: '+ai.clean(p['name'])+'\n'+content['text']+'\n공개 배송 정책: '+dump(content['fees'])
        images=[]
        for i in dict.fromkeys(ids):
            file=one(c,"SELECT images FROM file WHERE id=? AND ws=? AND COALESCE((SELECT agent FROM file_brand WHERE file=file.id AND ws=file.ws),'')=?",(i,ws,agent));require(file,'상품 이미지 파일 없음',404)
            imgs=loads(file['images']);require(imgs,'이미지 파일을 선택하세요.',422);images+=imgs
        require(len(images)<=4 and (content['text'] or images or content['fees']),'분석할 공개 텍스트 또는 이미지 필요',422)
        # Estimates alone never debit credits. Existing /run reserves and settles.
        n=ai.estimate(text,images,GUIDANCE);job=uid()
        c.execute('INSERT INTO training VALUES(?,?,?,?,?,?,?,?)',(job,ws,'estimated',n,0,dump({'text':text,'guidance':GUIDANCE,'images':images,'agent':agent}),None,now()))
        c.execute('INSERT INTO product_training VALUES(?,?,?,?,?)',(ws,job,agent,pid,row['fingerprint']))
        t=trial(c,w);credits=10000-operator_wallet(c,w)['credit_used'] if is_operator(w) else (t['credit_limit']-t['credit_used'] if t else w['credits'])
        return {'id':job,'maxCredits':n,'credits':credits,'enough':credits>=n,'product':p['name']}

def mapping(c,ws,job):
    return one(c,'SELECT * FROM product_training WHERE ws=? AND training=?',(ws,job))

def validate_job(c,ws,m):
    commerce.access(c,ws,m['agent'],True);get_product(c,ws,m['agent'],m['product_id'])
    row=detail_row(c,ws,m['agent'],m['product_id'])
    require(row and row['fingerprint']==m['fingerprint'] and row['updated']>=now()-DETAIL_AGE,'상품 정보 변경 또는 만료 · 다시 수집하세요.',409)
    return row

def publish(c,ws,j,m):
    validate_job(c,ws,m);result=loads(j['result'])
    # Product-local data, never global instructions or style. Only approved result is used.
    clean={'faq':[{'q':ai.clean(x['q'])[:300],'a':ai.clean(x['a'])[:600]} for x in result.get('faq',[])[:10] if isinstance(x,dict) and isinstance(x.get('q'),str) and isinstance(x.get('a'),str)],'facts':[ai.clean(x)[:400] for x in result.get('rules',[])[:10] if isinstance(x,str)]}
    c.execute('UPDATE smartstore_detail SET approved=? WHERE ws=? AND agent=? AND product_id=? AND fingerprint=?',(dump(clean),ws,m['agent'],m['product_id'],m['fingerprint']))
    c.execute("UPDATE training SET state='published' WHERE ws=? AND id=?",(ws,j['id']))
    return {'ok':True,'product_only':True}

def enrich(c,ws,agent,pid):
    row=detail_row(c,ws,agent,pid)
    if not row or row['updated']<now()-DETAIL_AGE:return {}
    data=loads(row['content']);approved=loads(row['approved']) if row['approved'] else {}
    # Strict context budget. Raw detail is useful even before any paid AI analysis.
    return {'description':data['text'][:1600],'detail_fees':data['fees'],'detail_as_of':row['updated'],'approved_product_facts':approved.get('facts',[])[:3],'approved_product_faq':approved.get('faq',[])[:2]}

def clear(c,ws,agent):
    c.execute('DELETE FROM smartstore_detail WHERE ws=? AND agent=?',(ws,agent))

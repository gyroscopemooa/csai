"""Explicit manual CSV import and opt-in provider credential probe."""
import csv,io,re,hashlib,os
from fastapi import Depends
from app import app,ident,require,bounded,limit
from store import *
import commerce
from integrations import smartstore_transport as smartstore

COLUMNS=('channel','reference','product','quantity','amount','state','carrier','tracking')
def parse_csv(text):
    require(isinstance(text,str) and 0<len(text)<=250000,'CSV 250,000자 이하',422)
    try:
        reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),strict=True)
        require(tuple(reader.fieldnames or ())==COLUMNS,'CSV 헤더가 공통 주문 양식과 일치해야 합니다.',422)
        items=[];keys=set()
        for line,row in enumerate(reader,2):
            require(len(items)<500,'한 번에 최대 500건',422)
            require(None not in row and all(isinstance(row.get(k),str) for k in COLUMNS),'열 개수 오류: '+str(line),422)
            ch=commerce.channel(row);ref=bounded(row['reference'],120);product=bounded(row['product'],200)
            require(ref and product,'주문번호와 상품명 필요: '+str(line),422)
            require(re.fullmatch(r'[0-9]{1,9}',row['quantity']) and re.fullmatch(r'[0-9]{1,10}',row['amount']),'수량·금액 형식 오류: '+str(line),422)
            qty=commerce.int_value({'quantity':int(row['quantity'])},'quantity',1,100000)
            amount=commerce.int_value({'amount':int(row['amount'])},'amount',0,1000000000)
            state=row['state'];require(state in commerce.ORDER_STATES,'주문 상태 오류: '+str(line),422)
            key=(ch,ref);require(key not in keys,'CSV 내부 중복 주문: '+str(line),422);keys.add(key)
            items.append((ch,ref,product,qty,amount,state,bounded(row['carrier'],80),bounded(row['tracking'],100)))
        require(items,'등록할 주문 없음',422)
        return items
    except csv.Error:require(False,'CSV 형식 오류',422)

@app.post('/api/commerce/import-orders')
def import_orders(body:dict,agent:str='',ws=Depends(ident)):
    raw=body.get('csv');items=parse_csv(raw);checksum=hashlib.sha256(raw.encode()).hexdigest()
    confirmed=body.get('confirmed') is True
    if confirmed:require(body.get('checksum')==checksum,'미리보기 이후 CSV가 변경되었습니다.',409)
    with db(confirmed) as c:
        commerce.access(c,ws,agent,confirmed)
        new=[];duplicates=0
        for item in items:
            if one(c,'SELECT id FROM commerce_order WHERE ws=? AND agent=? AND channel=? AND reference=?',(ws,agent,item[0],item[1])):duplicates+=1
            else:new.append(item)
        if confirmed:
            for item in new:c.execute('INSERT INTO commerce_order VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(uid(),ws,agent,*item,now(),now()))
        return {'checksum':checksum,'total':len(items),'new':len(new),'duplicates':duplicates,'imported':len(new) if confirmed else 0}

@app.get('/api/commerce/provider-status')
def provider_status(agent:str='',ws=Depends(ident)):
    with db() as c:commerce.access(c,ws,agent,need_enabled=False)
    return {'smartstore_probe':os.getenv('ENABLE_SMARTSTORE_PROBE')=='1','auto_sync':False}

@app.post('/api/commerce/smartstore/probe')
def smartstore_probe(body:dict,agent:str='',ws=Depends(ident)):
    require(os.getenv('ENABLE_SMARTSTORE_PROBE')=='1','스마트스토어 인증 테스트 비활성화',503)
    require(body.get('confirmed') is True,'읽기 전용 인증 확인 동의 필요',422)
    client_id=bounded(body.get('client_id',''),55);secret=bounded(body.get('client_secret',''),100);order_id=bounded(body.get('order_id',''),32)
    with db() as c:commerce.access(c,ws,agent,True)
    limit('smartstore-probe:'+ws,5,60)
    try:n=smartstore.order_probe(client_id,secret,order_id)
    except smartstore.SmartStoreError as e:require(False,str(e),422)
    return {'verified':True,'product_order_count':n,'saved':False,'auto_sync':False}

"""Read-only SmartStore SELF credentials probe, fixed official endpoint."""
import base64,re,time
import bcrypt,httpx
ROOT='https://api.commerce.naver.com/external'

class SmartStoreError(RuntimeError):pass

def signature(client_id,secret,timestamp):
    if not isinstance(client_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,55}',client_id) or not isinstance(secret,str) or not re.fullmatch(r'\$2[aby]\$(?:0[4-9]|1[0-2])\$[./A-Za-z0-9]{22}',secret):raise SmartStoreError('잘못된 앱 인증 정보')
    try:return base64.b64encode(bcrypt.hashpw((client_id+'_'+str(timestamp)).encode(),secret.encode())).decode()
    except ValueError:raise SmartStoreError('잘못된 앱 인증 정보') from None

def order_probe(client_id,secret,order_id):
    if not isinstance(order_id,str) or not re.fullmatch(r'[0-9]{1,32}',order_id):raise SmartStoreError('주문번호 형식 오류')
    timestamp=int(time.time()*1000);sign=signature(client_id,secret,timestamp)
    try:
        # Query parameters follow the documented authentication endpoint.
        resp=httpx.post(ROOT+'/v1/oauth2/token',params={'client_id':client_id,'timestamp':timestamp,'client_secret_sign':sign,'grant_type':'client_credentials','type':'SELF'},timeout=12,follow_redirects=False)
        data=resp.json()
        token=data.get('access_token') if isinstance(data,dict) else None
        if not resp.is_success or not isinstance(token,str) or not token or len(token)>8192:raise SmartStoreError('스마트스토어 인증 실패')
        resp=httpx.get(ROOT+'/v1/pay-order/seller/orders/'+order_id+'/product-order-ids',headers={'Authorization':'Bearer '+token},timeout=12,follow_redirects=False)
        data=resp.json()
        if not resp.is_success:raise SmartStoreError('주문 조회 권한 또는 주문번호 확인 필요')
        ids=data.get('data') if isinstance(data,dict) else None
        if not isinstance(ids,list) or any(not isinstance(i,str) or not re.fullmatch(r'[0-9]{1,32}',i) for i in ids):raise SmartStoreError('주문 조회 응답 확인 필요')
        return len(ids)
    except (httpx.HTTPError,ValueError,TypeError):raise SmartStoreError('스마트스토어 요청 결과 미확인') from None

# Product listing uses the official seller API, never the model.
def access_token(client_id,secret):
    timestamp=int(time.time()*1000);sign=signature(client_id,secret,timestamp)
    try:
        resp=httpx.post(ROOT+'/v1/oauth2/token',params={'client_id':client_id,'timestamp':timestamp,'client_secret_sign':sign,'grant_type':'client_credentials','type':'SELF'},timeout=12,follow_redirects=False)
        data=resp.json();token=data.get('access_token') if isinstance(data,dict) else None
        if not resp.is_success or not isinstance(token,str) or not token or len(token)>8192:raise SmartStoreError('스마트스토어 인증 실패')
        return token
    except (httpx.HTTPError,ValueError,TypeError):raise SmartStoreError('스마트스토어 인증 결과 미확인') from None

def read_json(token,path,payload):
    try:
        resp=httpx.post(ROOT+path,headers={'Authorization':'Bearer '+token},json=payload,timeout=12,follow_redirects=False)
        if not resp.is_success:raise SmartStoreError('스마트스토어 조회 권한 또는 요청 확인 필요')
        data=resp.json()
        if not isinstance(data,dict):raise SmartStoreError('스마트스토어 응답 형식 오류')
        return data
    except (httpx.HTTPError,ValueError,TypeError):raise SmartStoreError('스마트스토어 조회 결과 미확인') from None

def product_catalog(token,max_products=2000):
    items={};page=1;size=100;expected_pages=None;expected_total=None
    while True:
        data=read_json(token,'/v1/products/search',{'page':page,'size':size,'orderType':'NO','productStatusTypes':['SALE','OUTOFSTOCK']})
        contents=data.get('contents');pages=data.get('totalPages');total=data.get('totalElements')
        if not isinstance(contents,list) or type(pages) is not int or type(total) is not int or pages<0 or total<0 or total>max_products or pages>20 or data.get('page')!=page:raise SmartStoreError('상품 목록 형식 또는 2,000개 한도 확인 필요')
        if expected_pages is None:expected_pages,expected_total=pages,total
        if pages!=expected_pages or total!=expected_total:raise SmartStoreError('상품 목록 변경 중 · 다시 동기화하세요.')
        for group in contents:
            if not isinstance(group,dict) or not isinstance(group.get('channelProducts'),list):raise SmartStoreError('채널 상품 응답 형식 오류')
            for x in group['channelProducts']:
                if not isinstance(x,dict):raise SmartStoreError('상품 응답 형식 오류')
                if x.get('channelServiceType')!='STOREFARM' or x.get('channelProductDisplayStatusType')!='ON' or x.get('statusType') not in ('SALE','OUTOFSTOCK'):continue
                pid=x.get('channelProductNo');name=x.get('name');price=x.get('salePrice');stock=x.get('stockQuantity');discount=x.get('discountedPrice')
                if type(pid) is not int or pid<=0 or not isinstance(name,str) or not name.strip() or type(price) is not int or not 0<=price<=999999990 or type(stock) is not int or not 0<=stock<=99999999:raise SmartStoreError('상품 필드 형식 오류')
                if str(pid) in items:raise SmartStoreError('중복 상품 · 목록 변경 후 다시 동기화하세요.')
                if len(items)>=max_products:raise SmartStoreError('상품 최대 2,000개')
                facts={k:x[k] for k in ('deliveryFee','returnFee','exchangeFee') if type(x.get(k)) is int and 0<=x[k]<=100000000}
                items[str(pid)]={'id':str(pid),'name':name.strip()[:200],'price':price,'discount':discount if type(discount) is int and 0<=discount<=price else None,'stock':stock,'status':x['statusType'],'category':str(x.get('wholeCategoryName') or '')[:200],'facts':facts}
        if page>=max(1,pages):break
        page+=1
    return list(items.values())

def order_status(token,product_order_id):
    if not isinstance(product_order_id,str) or not re.fullmatch(r'[0-9]{1,32}',product_order_id):raise SmartStoreError('상품주문번호 형식 오류')
    data=read_json(token,'/v1/pay-order/seller/product-orders/query',{'productOrderIds':[product_order_id]})
    records=data.get('data')
    if not isinstance(records,list) or len(records)!=1:raise SmartStoreError('상품주문 조회 확인 필요')
    record=records[0]
    po=record.get('productOrder') if isinstance(record,dict) else None
    if not isinstance(po,dict) or po.get('productOrderId')!=product_order_id:raise SmartStoreError('상품주문번호 불일치')
    d=record.get('delivery') or {}
    if not isinstance(d,dict):raise SmartStoreError('배송 응답 형식 오류')
    # Never return orderer or shipping address, phone, or raw provider response.
    return {'reference':product_order_id,'product':str(po.get('productName') or '')[:200],'status':str(po.get('productOrderStatus') or '')[:80],'delivery_status':str(d.get('deliveryStatus') or '')[:80],'carrier':str(d.get('deliveryCompany') or '')[:80],'tracking':str(d.get('trackingNumber') or '')[:100],'queried_at':int(time.time())}

def product_detail(token,product_id):
    if not isinstance(product_id,str) or not re.fullmatch(r'[0-9]{1,32}',product_id):raise SmartStoreError('상품번호 형식 오류')
    try:
        resp=httpx.get(ROOT+'/v2/products/channel-products/'+product_id,headers={'Authorization':'Bearer '+token},timeout=12,follow_redirects=False)
        if not resp.is_success:raise SmartStoreError('상품 상세 조회 권한 확인 필요')
        if len(resp.content)>3_000_000:raise SmartStoreError('상품 상세 응답 용량 한도 초과')
        data=resp.json()
        origin=data.get('originProduct') if isinstance(data,dict) else None
        if not isinstance(origin,dict) or not isinstance(origin.get('detailContent'),str):raise SmartStoreError('상품 상세 응답 확인 필요')
        return origin
    except (httpx.HTTPError,ValueError,TypeError):raise SmartStoreError('상품 상세 조회 결과 미확인') from None

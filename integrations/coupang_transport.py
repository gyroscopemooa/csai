"""Fixed read-only Coupang order API, fresh HMAC and TLS verification."""
import hashlib,hmac,re,time
from urllib.parse import urlencode
import httpx
ROOT='https://api-gateway.coupang.com'
STATUSES={'ACCEPT':'결제완료','INSTRUCT':'상품준비중','DEPARTURE':'배송지시','DELIVERING':'배송중','FINAL_DELIVERY':'배송완료','NONE_TRACKING':'직접배송·추적불가'}
class CoupangError(RuntimeError):pass

def authorization(access_key,secret_key,path,stamp=None,method='GET',query=''):
    if not isinstance(access_key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,200}',access_key) or not isinstance(secret_key,str) or not re.fullmatch(r'[A-Za-z0-9_+=/-]{8,200}',secret_key):raise CoupangError('API 키 형식 확인 필요')
    stamp=stamp or time.strftime('%y%m%dT%H%M%SZ',time.gmtime())
    sign=hmac.new(secret_key.encode(),(stamp+method+path+query).encode(),hashlib.sha256).hexdigest()
    return 'CEA algorithm=HmacSHA256, access-key='+access_key+', signed-date='+stamp+', signature='+sign

def text(x,n):
    return x[:n] if isinstance(x,str) else ''

def order_status(vendor,access_key,secret_key,reference):
    if not isinstance(vendor,str) or not re.fullmatch(r'[A-Za-z0-9]{3,30}',vendor) or not isinstance(reference,str) or not re.fullmatch(r'[1-9][0-9]{0,31}',reference):raise CoupangError('판매자 ID 또는 주문번호 형식 오류')
    path='/v2/providers/openapi/apis/api/v5/vendors/'+vendor+'/'+reference+'/ordersheets'
    headers={'Authorization':authorization(access_key,secret_key,path),'Content-Type':'application/json;charset=UTF-8'}
    try:
        resp=httpx.get(ROOT+path,headers=headers,timeout=12,follow_redirects=False)
        if not resp.is_success:raise CoupangError('쿠팡 주문 조회 실패 · API 권한 또는 취소·반품 상태 확인 필요')
        if len(resp.content)>3_000_000:raise CoupangError('주문 응답 용량 초과')
        data=resp.json()
        if not isinstance(data,dict) or str(data.get('code'))!='200' or not isinstance(data.get('data'),list) or not 0<len(data['data'])<=100:raise CoupangError('주문 응답 확인 필요')
        shipments=[]
        for row in data['data']:
            if not isinstance(row,dict) or str(row.get('orderId'))!=reference or type(row.get('shipmentBoxId')) is not int:raise CoupangError('주문번호 불일치')
            items=row.get('orderItems');state=row.get('status')
            if not isinstance(items,list) or not isinstance(state,str):raise CoupangError('배송 응답 형식 오류')
            shipments.append({'shipment_id':str(row['shipmentBoxId']),'state':state[:50],'state_label':STATUSES.get(state,'판매처 확인 필요'),'carrier':text(row.get('deliveryCompanyName'),80),'tracking':text(row.get('invoiceNumber'),100),'products':[text(x.get('vendorItemName'),200) for x in items[:50] if isinstance(x,dict)]})
        return {'reference':reference,'shipments':shipments,'queried_at':int(time.time())}
    except (httpx.HTTPError,ValueError,TypeError):raise CoupangError('쿠팡 연결 결과 미확인') from None

PRODUCT_PATH='/v2/providers/seller_api/apis/api/v1/marketplace/seller-products'
def signed_json(vendor,access,secret,path,params=(),method='GET',body=None):
    if not isinstance(vendor,str) or not re.fullmatch(r'[A-Za-z0-9]{3,30}',vendor):raise CoupangError('판매자 ID 확인 필요')
    query=urlencode(params)
    headers={'Authorization':authorization(access,secret,path,method=method,query=query),'Content-Type':'application/json;charset=UTF-8'}
    url=ROOT+path+('?' + query if query else '')
    try:
        resp=httpx.get(url,headers=headers,timeout=12,follow_redirects=False) if method=='GET' else httpx.post(url,headers=headers,json=body,timeout=12,follow_redirects=False)
        if not resp.is_success or len(resp.content)>3_000_000:raise CoupangError('쿠팡 API 응답 확인 필요')
        data=resp.json()
        if not isinstance(data,dict) or str(data.get('code')) not in ('200','SUCCESS'):raise CoupangError('쿠팡 API 권한 또는 응답 확인 필요')
        return data
    except (httpx.HTTPError,ValueError,TypeError):raise CoupangError('쿠팡 API 연결 결과 미확인') from None

def product_catalog(vendor,access,secret):
    cursor='';seen=set();items={}
    for page in range(20):
        params=[('vendorId',vendor),('maxPerPage',100),('status','APPROVED')]
        if cursor:params.append(('nextToken',cursor))
        data=signed_json(vendor,access,secret,PRODUCT_PATH,params)
        batch=data.get('data');next_token=data.get('nextToken')
        if not isinstance(batch,list) or len(batch)>100 or not isinstance(next_token,str):raise CoupangError('상품 목록 형식 오류')
        for row in batch:
            if not isinstance(row,dict) or row.get('vendorId')!=vendor:raise CoupangError('상품 판매자 불일치')
            pid=row.get('sellerProductId');public_id=row.get('productId');name=row.get('sellerProductName');state=row.get('statusName')
            if type(pid) is not int or pid<=0 or not isinstance(name,str) or not name.strip():raise CoupangError('상품 정보 확인 필요')
            if state not in ('APPROVED','승인완료'):continue
            if str(pid) in items:raise CoupangError('중복 상품 · 목록 갱신 필요')
            if len(items)>=2000:raise CoupangError('상품 최대 2,000개')
            items[str(pid)]={'id':str(pid),'public_id':str(public_id) if type(public_id) is int and public_id>0 else '', 'name':name.strip()[:200]}
        if not next_token:return list(items.values())
        if not re.fullmatch(r'[0-9]{1,30}',next_token) or next_token in seen:raise CoupangError('상품 페이지 확인 필요')
        seen.add(next_token);cursor=next_token
    raise CoupangError('상품 최대 2,000개 · 전체 목록 확인 필요')

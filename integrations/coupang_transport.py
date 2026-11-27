"""Fixed read-only Coupang order API, fresh HMAC and TLS verification."""
import hashlib,hmac,re,time
import httpx
ROOT='https://api-gateway.coupang.com'
STATUSES={'ACCEPT':'결제완료','INSTRUCT':'상품준비중','DEPARTURE':'배송지시','DELIVERING':'배송중','FINAL_DELIVERY':'배송완료','NONE_TRACKING':'직접배송·추적불가'}
class CoupangError(RuntimeError):pass

def authorization(access_key,secret_key,path,stamp=None):
    if not isinstance(access_key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,200}',access_key) or not isinstance(secret_key,str) or not re.fullmatch(r'[A-Za-z0-9_+=/-]{8,200}',secret_key):raise CoupangError('API 키 형식 확인 필요')
    stamp=stamp or time.strftime('%y%m%dT%H%M%SZ',time.gmtime())
    sign=hmac.new(secret_key.encode(),(stamp+'GET'+path).encode(),hashlib.sha256).hexdigest()
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

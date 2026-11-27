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

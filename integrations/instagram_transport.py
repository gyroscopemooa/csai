"""Instagram Login API: verify account identity only, no message send or token refresh."""
import os,re,httpx
class InstagramError(RuntimeError):pass
def profile(token):
    version=os.getenv('INSTAGRAM_GRAPH_VERSION','')
    if not re.fullmatch(r'v[0-9]{1,2}\.0',version):raise InstagramError('Meta API 버전 설정 필요')
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_.\-]{20,4096}',token):raise InstagramError('Instagram 액세스 토큰 형식 오류')
    try:
        response=httpx.get('https://graph.instagram.com/'+version+'/me',params={'fields':'id,username'},headers={'Authorization':'Bearer '+token},timeout=8,follow_redirects=False)
        if not response.is_success or len(response.content)>64000:raise InstagramError('Instagram 계정 권한 확인 실패')
        data=response.json()
        if not isinstance(data,dict) or not isinstance(data.get('id'),str) or not re.fullmatch(r'[0-9]{1,32}',data['id']) or not isinstance(data.get('username'),str) or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}',data['username']):raise InstagramError('Instagram 계정 응답 확인 필요')
        return {'id':data['id'],'username':data['username']}
    except (httpx.HTTPError,ValueError,TypeError):raise InstagramError('Instagram 인증 결과 미확인') from None

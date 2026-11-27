"""LINE official-account verification and one-time reply API. No push or broadcast."""
import re,httpx
from integrations.provider_formats import line_out
ROOT='https://api.line.me/v2/bot'
class LineError(RuntimeError):pass
def headers(token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9+/=_\-.]{20,4096}',token):raise LineError('LINE 액세스 토큰 형식 확인 필요')
    return {'Authorization':'Bearer '+token}
def bot_info(token):
    try:
        r=httpx.get(ROOT+'/info',headers=headers(token),timeout=8,follow_redirects=False)
        if not r.is_success:raise LineError('LINE 공식 계정 인증 실패')
        d=r.json();uid=d.get('userId') if isinstance(d,dict) else None
        if not isinstance(uid,str) or not re.fullmatch(r'U[0-9a-fA-F]{32}',uid):raise LineError('LINE 계정 ID 확인 필요')
        return {'id':uid}
    except (httpx.HTTPError,ValueError,TypeError):raise LineError('LINE 인증 결과 미확인') from None
def reply(token,reply_token,text):
    if not isinstance(reply_token,str) or not re.fullmatch(r'[A-Za-z0-9]{1,256}',reply_token):raise LineError('LINE 답장 토큰 오류')
    try:
        r=httpx.post(ROOT+'/message/reply',headers=headers(token),json=line_out(reply_token,text),timeout=8,follow_redirects=False)
        if r.status_code!=200:raise LineError('LINE 답장 결과 미확인 · 재전송 금지')
    except (httpx.HTTPError,ValueError,TypeError):raise LineError('LINE 답장 결과 미확인 · 재전송 금지') from None

"""Pure channel-format adapters, intentionally NOT registered as public webhooks.
Production requires per-workspace verified credentials, delivery idempotency, callbacks,
provider permission and safe asynchronous dispatch. Never follow arbitrary callback URLs.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Message:
    channel: str
    user: str
    text: str

def naver_in(payload):
    if payload.get('event')!='send':return None
    user=payload.get('user');text=payload.get('textContent',{}).get('text')
    if not isinstance(user,str) or not isinstance(text,str) or not user or not text.strip():return None
    return Message('naver',user,text[:2000])
def naver_out(user,text):
    return {'event':'send','user':user,'textContent':{'text':text[:1000]}}
def kakao_in(payload):
    request=payload.get('userRequest',{});user=request.get('user',{}).get('id');text=request.get('utterance')
    if not isinstance(user,str) or not isinstance(text,str) or not user or not text.strip():return None
    return Message('kakao',user,text[:2000])
def kakao_out(text):
    return {'version':'2.0','template':{'outputs':[{'simpleText':{'text':text[:1000]}}]}}

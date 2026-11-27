"""Telegram Bot API transport for the future opt-in channel connection.
No routes, polling, token persistence, activation, or paid broadcasting.
The caller must verify tenant/brand, webhook secret, chat ownership and entitlement.
"""
import re
import logging
import httpx
# HTTPX INFO request logging includes Telegram bot tokens in URLs.
logging.getLogger('httpx').setLevel(logging.WARNING)
from integrations.provider_formats import telegram_out

_TOKEN=re.compile(r'[0-9]{1,20}:[A-Za-z0-9_-]{20,128}\Z')
_SECRET=re.compile(r'[A-Za-z0-9_-]{32,256}\Z')
_METHODS={'getMe','getWebhookInfo','setWebhook','sendMessage'}

class TelegramError(RuntimeError):
    pass

def request(token,method,payload=None):
    if not isinstance(token,str) or not _TOKEN.fullmatch(token) or method not in _METHODS:
        raise TelegramError('Invalid Telegram connection')
    try:
        resp=httpx.post('https://api.telegram.org/bot'+token+'/'+method,json=payload or {},timeout=10,follow_redirects=False)
        data=resp.json()
        if not resp.is_success or not isinstance(data,dict) or data.get('ok') is not True:
            raise TelegramError('Telegram response not confirmed')
        return data.get('result')
    except (httpx.HTTPError,ValueError):
        # Provider URLs contain credentials; never return or log the original exception.
        raise TelegramError('Telegram request outcome unconfirmed') from None

def verify_bot(token):
    result=request(token,'getMe')
    if not isinstance(result,dict) or result.get('is_bot') is not True or type(result.get('id')) is not int or result['id']<=0:
        raise TelegramError('Bot identity not confirmed')
    if str(result['id'])!=token.split(':',1)[0]:
        raise TelegramError('Bot ID does not match token')
    return str(result['id'])

def webhook_status(token):
    result=request(token,'getWebhookInfo')
    if not isinstance(result,dict) or not isinstance(result.get('url'),str):
        raise TelegramError('Webhook status not confirmed')
    return result['url']

def register_webhook(token, url, secret, canonical_url):
    # Only this application's preconfigured canonical HTTPS endpoint may be registered.
    from urllib.parse import urlsplit
    root=urlsplit(canonical_url)
    target=urlsplit(url)
    if root.scheme!='https' or not root.hostname or root.username or root.password or root.query or root.fragment or root.path not in ('','/') or target.scheme!='https' or target.netloc!=root.netloc or target.query or target.fragment or not re.fullmatch(r'/hooks/telegram/[A-Za-z0-9_-]{32,128}',target.path) or not isinstance(secret,str) or not _SECRET.fullmatch(secret):
        raise TelegramError('Invalid webhook configuration')
    if request(token,'setWebhook',{'url':url,'secret_token':secret,'allowed_updates':['message'],'drop_pending_updates':False}) is not True:
        raise TelegramError('Webhook registration not confirmed')

def send_text(token,customer,text):
    if not isinstance(customer,str) or not re.fullmatch(r'[1-9][0-9]{0,19}',customer):
        raise TelegramError('Verified private chat ID required')
    result=request(token,'sendMessage',telegram_out(customer,text))
    if not isinstance(result,dict) or type(result.get('message_id')) is not int or not isinstance(result.get('chat'),dict) or str(result['chat'].get('id'))!=customer:
        raise TelegramError('Delivery outcome not confirmed')
    return result['message_id']

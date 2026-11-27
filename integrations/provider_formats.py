"""Provider wire-format groundwork; no network calls, routes, or billing.
Call signature verification on the original bytes before parsing.
Use a verified provider account and workspace/brand binding before dispatch.
Text-only; attachments, provider permissions, expiry and dispatch remain separate.
"""
from dataclasses import dataclass
import base64
import hashlib
import hmac

@dataclass(frozen=True)
class Incoming:
    channel: str
    account: str
    user: str
    event_id: str
    text: str
    reply_token: str = ''

def _obj(x):
    return x if isinstance(x, dict) else {}

def _list(x):
    return x if isinstance(x, list) else []

def _id(x):
    if type(x) is int and x >= 0:
        x = str(x)
    return x if isinstance(x, str) and 0 < len(x) <= 256 else ''

def _text(x):
    return x.strip()[:2000] if isinstance(x, str) else ''

def telegram_verify(expected, supplied):
    return bool(expected and isinstance(expected, str) and isinstance(supplied, str)
                and hmac.compare_digest(expected.encode(), supplied.encode()))

def meta_verify(secret, raw, signature):
    if not secret or not isinstance(signature, str):
        return False
    expected = 'sha256=' + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), signature.encode())

def line_verify(secret, raw, signature):
    if not secret or not isinstance(signature, str):
        return False
    expected = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest())
    return hmac.compare_digest(expected, signature.encode())

def telegram_in(payload, account):
    p = _obj(payload)
    m = _obj(p.get('message'))
    sender, chat = _obj(m.get('from')), _obj(m.get('chat'))
    user, event, text, account = _id(chat.get('id')), _id(p.get('update_id')), _text(m.get('text')), _id(account)
    if chat.get('type') != 'private' or sender.get('is_bot') or user != _id(sender.get('id')):
        return []
    return [Incoming('telegram', account, user, event, text)] if all((account,user,event,text)) else []

def meta_in(payload, channel, account):
    if channel not in ('instagram', 'messenger'):
        raise ValueError('invalid Meta channel')
    p, account = _obj(payload), _id(account)
    if not account or p.get('object') != ('instagram' if channel == 'instagram' else 'page'):
        return []
    result = []
    for entry in _list(p.get('entry')):
        e = _obj(entry)
        if _id(e.get('id')) != account:
            continue
        for item in _list(e.get('messaging')):
            item = _obj(item)
            msg = _obj(item.get('message'))
            user = _id(_obj(item.get('sender')).get('id'))
            recipient = _id(_obj(item.get('recipient')).get('id'))
            event, text = _id(msg.get('mid')), _text(msg.get('text'))
            if recipient == account and user != account and not msg.get('is_echo') and all((user,event,text)):
                result.append(Incoming(channel, account, user, event, text))
    return result

def line_in(payload, account):
    p, account = _obj(payload), _id(account)
    if not account or _id(p.get('destination')) != account:
        return []
    result = []
    for event in _list(p.get('events')):
        event = _obj(event)
        src, msg = _obj(event.get('source')), _obj(event.get('message'))
        user, eid, token, text = _id(src.get('userId')), _id(event.get('webhookEventId')), _id(event.get('replyToken')), _text(msg.get('text'))
        if event.get('type') == 'message' and event.get('mode') == 'active' and src.get('type') == 'user' and msg.get('type') == 'text' and all((user,eid,token,text)):
            result.append(Incoming('line', account, user, eid, text, token))
    return result

def telegram_out(user, text):
    if not _id(user) or not _text(text):
        raise ValueError('recipient and text required')
    return {'chat_id': user, 'text': text[:4096]}

def meta_out(user, text, channel):
    if channel not in ('instagram', 'messenger') or not _id(user) or not _text(text):
        raise ValueError('channel, recipient and text required')
    body = {'recipient': {'id': str(user)}, 'message': {'text': text[:1000]}}
    if channel == 'messenger':
        body['messaging_type'] = 'RESPONSE'
    return body

def line_out(reply_token, text):
    if not _id(reply_token) or not _text(text):
        raise ValueError('reply token and text required')
    return {'replyToken': reply_token, 'messages': [{'type': 'text', 'text': text[:5000]}]}

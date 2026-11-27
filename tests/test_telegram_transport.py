import pytest
from integrations import telegram_transport as tg

TOKEN='123456:abcdefghijklmnopqrstuvwxyz_123456'
ROOT='https://example.test'
URL=ROOT+'/hooks/telegram/'+'a'*40
SECRET='b'*40

def test_transport_bot_and_webhook_and_message(monkeypatch):
    calls=[]
    class Response:
        is_success=True
        def __init__(self,result):self.result=result
        def json(self):return {'ok':True,'result':self.result}
    def post(url,**kwargs):
        calls.append((url,kwargs))
        method=url.rsplit('/',1)[-1]
        return Response({'getMe':{'id':123456,'is_bot':True},'getWebhookInfo':{'url':URL},'setWebhook':True,'sendMessage':{'message_id':99,'chat':{'id':42}}}[method])
    monkeypatch.setattr(tg.httpx,'post',post)
    assert tg.verify_bot(TOKEN)=='123456'
    assert tg.webhook_status(TOKEN)==URL
    tg.register_webhook(TOKEN,URL,SECRET,ROOT)
    assert calls[-1][1]['json']['secret_token']==SECRET
    assert calls[-1][1]['json']['drop_pending_updates'] is False
    assert tg.send_text(TOKEN,'42','Hello')==99
    assert all(not x[1]['follow_redirects'] for x in calls)
    assert 'allow_paid_broadcast' not in calls[-1][1]['json']
    with pytest.raises(tg.TelegramError):tg.register_webhook(TOKEN,'https://other.test/hooks/telegram/'+'a'*40,SECRET,ROOT)
    with pytest.raises(tg.TelegramError):tg.send_text(TOKEN,'@channel','hello')
    with pytest.raises(tg.TelegramError):tg.request(TOKEN,'arbitrary')

def test_transport_failure_does_not_expose_token(monkeypatch):
    def post(url,**kwargs):
        raise tg.httpx.ReadTimeout(url)
    monkeypatch.setattr(tg.httpx,'post',post)
    with pytest.raises(tg.TelegramError) as exc:tg.verify_bot(TOKEN)
    assert TOKEN not in str(exc.value)

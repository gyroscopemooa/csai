from test_app import owner,post,patch
from store import db,one
import channel_live as cl
from integrations import telegram_transport as tg
import telegram_connection as tc

def test_telegram_private_webhook_and_outbox(monkeypatch):
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True,'price':'테스트 가격'})
    monkeypatch.setenv('ENABLE_TELEGRAM_CHANNEL','1');monkeypatch.setenv('INTEGRATION_ENCRYPTION_KEY','mock-only')
    monkeypatch.setattr(cl,'enabled',lambda:True)
    monkeypatch.setattr(cl,'lock_text',lambda v:v);monkeypatch.setattr(cl,'unlock',lambda v:v)
    monkeypatch.setattr(tc,'APP_URL','https://example.test')
    remote={'url':'','header':''};sent=[]
    monkeypatch.setattr(tg,'verify_bot',lambda token:'123456')
    monkeypatch.setattr(tg,'webhook_status',lambda token:remote['url'])
    def register(token,url,secret,root):remote.update(url=url,header=secret)
    monkeypatch.setattr(tg,'register_webhook',register)
    monkeypatch.setattr(tg,'send_text',lambda token,user,text:sent.append((user,text)) or 9)
    post(c,'/api/telegram/connect',{'token':'mock-token','confirmed':True})
    url='/hooks/telegram/'+remote['url'].rsplit('/',1)[-1]
    body={'update_id':1,'message':{'text':'가격은?','chat':{'id':42,'type':'private'},'from':{'id':42,'is_bot':False}}}
    assert c.post(url,json=body).status_code==403
    h={'X-Telegram-Bot-Api-Secret-Token':remote['header']}
    assert c.post(url,json=body,headers=h).status_code==200
    assert c.post(url,json=body,headers=h).status_code==200
    with db() as d:ws=one(d,'SELECT id FROM workspace WHERE slug=?',(c.get('/api/me').json()['slug'],))['id']
    assert cl.process_one(ws)
    assert not cl.process_one(ws)
    assert sent==[('42','테스트 가격')]
    tid=c.get('/api/inbox?kind=telegram').json()[0]['id']
    post(c,'/api/inbox/'+tid+'/channel-reply',{'reply':'담당자 답변','client':'tg-reply-1','confirmed':True})
    assert cl.process_staff_one(ws)
    assert sent[-1]==('42','담당자 답변')
    post(c,'/api/telegram/pause',{})
    assert c.post(url,json=body,headers=h).status_code==404

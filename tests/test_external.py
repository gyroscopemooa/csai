from test_app import owner,post,patch,setup_booking,future,public,draft,confirm
from store import db
from cryptography.fernet import Fernet
import google_calendar as gc,channel_live as cl
import httpx

def test_calendar_oauth_mock_and_owned_sync(monkeypatch):
    monkeypatch.setenv('GOOGLE_CLIENT_ID','test');monkeypatch.setenv('GOOGLE_CLIENT_SECRET','test');monkeypatch.setenv('INTEGRATION_ENCRYPTION_KEY',Fernet.generate_key().decode());c=setup_booking();post(c,'/api/demo/billing',{'plan':'lite','addons':['auto_booking','google_calendar']});patch(c,{'enabled':True});u,t=public(c);b=draft(u,t);confirm(u,t,b)
    r=c.get('/auth/calendar/connect',follow_redirects=False);assert r.status_code==307
    from urllib.parse import urlsplit,parse_qs
    state=parse_qs(urlsplit(r.headers['location']).query)['state'][0]
    monkeypatch.setattr(gc,'token_exchange',lambda data:{'refresh_token':'refresh','access_token':'token'})
    assert c.get('/auth/calendar/callback',params={'state':state,'code':'test'},follow_redirects=False).status_code==303
    calls=[]
    def remote(method,path,token,**kw):
        calls.append((method,path,kw));return httpx.Response(404 if method=='GET' else 200,json={})
    monkeypatch.setattr(gc,'api',remote);assert post(c,'/api/integrations/calendar/sync/'+b['id'],{})['status']=='synced';assert calls[-1][0]=='POST';assert calls[-1][2]['json']['summary']=='CS AI 예약';assert '테스트' not in str(calls)
    monkeypatch.setattr(gc,'api',lambda *a,**k:httpx.Response(200,json={'extendedProperties':{'private':{}}}));assert c.post('/api/integrations/calendar/sync/'+b['id'],json={}).status_code==409
    post(c,'/api/integrations/calendar/disconnect',{});assert not c.get('/api/integrations/calendar').json()['connected']

def process_owner_job(client):
    from store import db, one
    slug = client.get('/api/me').json()['slug']
    with db() as connection:
        workspace = one(connection, 'SELECT id FROM workspace WHERE slug=?', (slug,))
    return cl.process_one(workspace['id'])


def test_live_naver_mock_ingress_worker(monkeypatch):
    monkeypatch.setenv('INTEGRATION_ENCRYPTION_KEY',Fernet.generate_key().decode());monkeypatch.setattr(cl,'enabled',lambda:True);c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['naver']});patch(c,{'enabled':True,'price':'123원'});x=post(c,'/api/integrations/channels/naver',{'partner':'p1','credential':'mock-key','active':True});from urllib.parse import urlsplit
    path=urlsplit(x['webhook']).path;payload={'event':'send','user':'u1','partner':'p1','textContent':{'text':'가격은?'}};assert c.post(path+'/bad',json=payload).status_code==404;assert c.post(path,json=payload).status_code==200
    sent=[]
    def send(url,**kw):sent.append((url,kw));return httpx.Response(200,json={'success':True,'resultCode':'00'})
    monkeypatch.setattr(cl.httpx,'post',send);assert process_owner_job(c);assert sent[0][0]=='https://gw.talk.naver.com/chatbot/v1/event' and sent[0][1]['json']['textContent']['text']=='123원';assert c.get('/api/integrations/channels/naver').json()['jobs'][0]['status']=='sent';assert c.get('/api/me').json()['remaining']==299

def test_kakao_callback_allowlist_and_mock(monkeypatch):
    monkeypatch.setenv('INTEGRATION_ENCRYPTION_KEY',Fernet.generate_key().decode());monkeypatch.setenv('KAKAO_CALLBACK_HOSTS','callback.example.com');monkeypatch.setattr(cl,'enabled',lambda:True);c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['kakao']});patch(c,{'enabled':True,'price':'500원'});x=post(c,'/api/integrations/channels/kakao',{'partner':'b1','active':True});from urllib.parse import urlsplit
    path=urlsplit(x['webhook']).path;payload={'bot':{'id':'b1'},'userRequest':{'user':{'id':'u1'},'utterance':'가격','callbackUrl':'https://127.0.0.1/private'}};assert c.post(path,json=payload).status_code==422;payload['userRequest']['callbackUrl']='https://callback.example.com/token';assert post(c,path,payload)['useCallback'];assert post(c,path,payload)['useCallback'];sent=[]
    monkeypatch.setattr(cl.httpx,'post',lambda url,**kw:(sent.append((url,kw)) or httpx.Response(200,json={'status':'SUCCESS'})));assert process_owner_job(c);assert len(sent)==1;assert sent[0][1]['json']['template']['outputs'][0]['simpleText']['text']=='500원';assert c.get('/api/me').json()['remaining']==299

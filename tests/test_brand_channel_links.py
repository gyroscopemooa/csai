from test_app import owner,post,patch
from store import db,one
import channel_live

def test_brand_channel_isolation_and_disconnect(monkeypatch):
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['naver','extra_agent']})
    patch(c,{'enabled':True,'price':'기본 가격'})
    brand=post(c,'/api/agents',{'brand':'추가 브랜드','welcome':'안녕하세요','price':'추가 가격','enabled':True})
    aid=brand['id']
    monkeypatch.setenv('INTEGRATION_ENCRYPTION_KEY','mock-only')
    monkeypatch.setattr(channel_live,'enabled',lambda:True)
    monkeypatch.setattr(channel_live,'lock_text',lambda v:v)
    monkeypatch.setattr(channel_live,'unlock',lambda v:v)
    path='/api/integrations/channels/naver'
    main=post(c,path,{'partner':'main-partner','credential':'main-token','active':True})
    extra=post(c,path,{'agent':aid,'partner':'brand-partner','credential':'brand-token','active':True})
    assert main['webhook']!=extra['webhook']
    assert c.get(path).json()['partner']=='main-partner'
    assert c.get(path+'?agent='+aid).json()['partner']=='brand-partner'
    assert c.post(path,json={'agent':aid,'partner':'main-partner','credential':'token'}).status_code==409
    other=owner()
    post(other,'/api/demo/billing',{'plan':'lite','addons':['naver','extra_agent']})
    assert other.get(path+'?agent='+aid).status_code==403
    sent=[]
    class Resp:
        is_success=True
        def json(self):return {'success':True,'resultCode':'00'}
    def send(*args,**kwargs):
        sent.append((kwargs['headers']['Authorization'],kwargs['json']))
        return Resp()
    monkeypatch.setattr(channel_live.httpx,'post',send)
    def incoming(link,partner,text):
        secret=link['webhook'].rsplit('/',1)[-1]
        return c.post('/hooks/naver/'+secret,json={'event':'send','partner':partner,'user':'same-customer','textContent':{'text':text}})
    assert incoming(main,'main-partner','가격은?').status_code==200
    assert incoming(extra,'brand-partner','가격은?').status_code==200
    slug=c.get('/api/me').json()['slug']
    with db() as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
    assert channel_live.process_one(ws)
    assert channel_live.process_one(ws)
    assert {x[0]:x[1]['textContent']['text'] for x in sent}=={'main-token':'기본 가격','brand-token':'추가 가격'}
    base=c.get('/api/inbox?kind=naver&agent=').json()
    own=c.get('/api/inbox?kind=naver&agent='+aid).json()
    assert len(base)==len(own)==1 and base[0]['id']!=own[0]['id']
    assert c.post(path+'/disconnect?agent='+aid,json={}).status_code==200
    assert c.get(path).json()['saved'] and not c.get(path+'?agent='+aid).json()['saved']
    assert incoming(extra,'brand-partner','다시 문의').status_code==404
    assert incoming(main,'main-partner','다시 문의').status_code==200

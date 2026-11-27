from fastapi.testclient import TestClient
from app import app
from test_app import owner,post

def test_brand_work_and_leads_are_scoped():
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent','tasks','complaints','leads','crm','quote'],'brand_quantity':2})
    a=post(c,'/api/agents',{'create':True,'brand':'A','enabled':True})
    b=post(c,'/api/agents',{'create':True,'brand':'B','enabled':True})
    pa='?agent='+a['id'];pb='?agent='+b['id']
    post(c,'/api/work',{'agent':a['id'],'kind':'tasks','title':'A only'})
    assert c.get('/api/work').json()==[]
    assert c.get('/api/work'+pb).json()==[]
    w=c.get('/api/work'+pa).json()[0]
    assert c.patch('/api/work/'+w['id']+pb,json={'status':'resolved'}).status_code==404
    assert c.patch('/api/work/'+w['id']+pa,json={'status':'resolved'}).status_code==200
    assert owner().get('/api/work'+pa).status_code in (403,404)
    u=TestClient(app);token=post(u,'/api/session',{'slug':a['slug']})['token']
    assert 'quote' not in u.get('/api/customer/requests/'+token).json()
    r=post(u,'/api/customer/requests',{'token':token,'kind':'complaints','title':'문의','details':'확인 요청','confirmed':True})
    assert r['id'] in [x['id'] for x in c.get('/api/work'+pa).json()]
    assert c.get('/api/work'+pb).json()==[]
    post(u,'/api/chat',{'token':token,'clientMessageId':'lead-a','message':'상품 가격 얼마인가요?'})
    assert len(c.get('/api/leads'+pa).json())==1
    assert c.get('/api/leads'+pb).json()==[]
    assert c.get('/api/leads').json()==[]

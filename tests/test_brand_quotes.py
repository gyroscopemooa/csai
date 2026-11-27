from fastapi.testclient import TestClient
from app import app
from test_app import owner,post

def test_brand_quote_catalog_and_delivery_isolation():
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent','quote'],'brand_quantity':2})
    a=post(c,'/api/agents',{'create':True,'brand':'A','enabled':True})
    b=post(c,'/api/agents',{'create':True,'brand':'B','enabled':True})
    pa='?agent='+a['id'];pb='?agent='+b['id']
    main=post(c,'/api/quotes/items',{'name':'촬영','price':1000})
    aa=post(c,'/api/quotes/items'+pa,{'name':'촬영','price':30000})
    bb=post(c,'/api/quotes/items'+pb,{'name':'촬영','price':70000})
    assert [x['id'] for x in c.get('/api/quotes/items'+pa).json()]==[aa['id']]
    assert [x['id'] for x in c.get('/api/quotes/items').json()]==[main['id']]
    assert c.post('/api/quotes/items'+pb,json={'id':aa['id'],'name':'변경','price':1}).status_code==404
    u=TestClient(app);token=post(u,'/api/session',{'slug':a['slug']})['token']
    r=post(u,'/api/chat',{'token':token,'clientMessageId':'quote-a','message':'촬영 2건 견적 요청'})
    work=post(u,'/api/customer/requests',r['workDraft']|{'token':token,'confirmed':True})['id']
    assert c.get('/api/quotes/suggestions/'+work+pa).json()==[{'id':aa['id'],'quantity':2,'name':'촬영','unit_price':30000}]
    assert c.get('/api/quotes/suggestions/'+work+pb).status_code==404
    def body(i):return {'work':work,'items':[{'id':i,'quantity':2}]}
    assert c.post('/api/quotes/offers'+pa,json=body(bb['id'])).status_code==404
    assert c.post('/api/quotes/offers'+pa,json=body(main['id'])).status_code==404
    offer=post(c,'/api/quotes/offers'+pa,body(aa['id']))
    assert offer['amount']==60000
    assert c.get('/api/quotes/offers'+pb).json()==[]
    assert c.get('/api/quotes/offers').json()==[]
    send='/api/quotes/offers/'+offer['id']+'/send'
    assert c.post(send+pb,json={'confirmed':True}).status_code==404
    assert c.post(send+pa,json={}).status_code==422
    assert post(c,send+pa,{'confirmed':True})['status']=='sent'
    assert post(c,send+pa,{'confirmed':True})['status']=='sent'
    assert c.get('/api/work'+pa).json()[0]['status']=='resolved'
    assert owner().get('/api/quotes/items'+pa).status_code==403

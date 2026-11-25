from test_app import owner,post,patch,public
from fastapi.testclient import TestClient
from app import app
from store import db,now
import domains
import message_notifications
import pytest

def setup(*addons):
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':list(addons)})
    patch(c,{'enabled':True,'price':'100원'});return c

def purchase(c,kind,client,**extra):
    o=post(c,'/api/billing/orders',{'kind':kind,'client':client,**extra})
    return post(c,'/api/billing/orders/'+o['id']+'/sandbox-confirm',{})

def test_quote_suggests_only_explicit_catalog_quantity():
    c=setup('quote')
    item=post(c,'/api/quotes/items',{'name':'스냅 촬영','price':30000})
    u,t=public(c)
    r=post(u,'/api/chat',{'token':t,'message':'스냅 촬영 2건 견적 요청','clientMessageId':'suggest'})
    p=r['workDraft']|{'token':t,'confirmed':True}
    w=post(u,'/api/customer/requests',p)
    assert c.get('/api/quotes/suggestions/'+w['id']).json()==[{'id':item['id'],'quantity':2,'name':'스냅 촬영','unit_price':30000}]
    assert owner().get('/api/quotes/suggestions/'+w['id']).status_code==403

def test_paid_history_window_preserves_records():
    c=setup();u,t=public(c)
    r=post(u,'/api/chat',{'token':t,'message':'가격은?','clientMessageId':'archive'})
    tid=c.get('/api/inbox').json()[0]['id']
    old=now()-100*86400
    with db(True) as d:
        d.execute('UPDATE thread SET created=? WHERE id=?',(old,tid))
        d.execute('UPDATE message SET created=? WHERE thread=?',(old,tid))
    assert c.get('/api/inbox').json()==[]
    assert c.get('/api/inbox/'+tid).status_code==404
    post(c,'/api/demo/billing',{'plan':'lite','addons':['retention']})
    assert c.get('/api/inbox/'+tid).status_code==200
    assert c.get('/api/history-policy').json()['deletion_enabled'] is False

def test_sandbox_refund_and_fail_do_not_grant_twice():
    c=owner();o=purchase(c,'education','refund-edu',sku='mini')
    assert c.get('/api/me').json()['credits']==120
    p='/api/billing/orders/'+o['id']+'/sandbox-refund'
    assert post(c,p,{'confirmed':True})['status']=='refunded'
    assert post(c,p,{'confirmed':True})['status']=='refunded'
    assert c.get('/api/me').json()['credits']==20
    s=purchase(c,'subscription','refund-sub',plan='lite',addons=['widget'])
    assert c.get('/api/me').json()['plan']=='lite'
    post(c,'/api/billing/orders/'+s['id']+'/sandbox-refund',{'confirmed':True})
    assert c.get('/api/me').json()['plan']=='free'
    f=post(c,'/api/billing/orders',{'kind':'education','client':'failure','sku':'mini'})
    post(c,'/api/billing/orders/'+f['id']+'/sandbox-fail',{})
    assert c.post('/api/billing/orders/'+f['id']+'/sandbox-confirm',json={}).status_code==409

def test_custom_job_claim_and_completion():
    c=setup('external_api','custom_integration','tasks')
    post(c,'/api/work',{'kind':'tasks','title':'업무','details':'확인'})
    w=c.get('/api/work').json()[0]
    flow=post(c,'/api/custom-workflows',{'name':'업무 처리','description':'서버 연결'})
    job=post(c,'/api/custom-jobs',{'workflow':flow['id'],'work':w['id'],'payload':{'amount':1},'confirmed':True})
    k=post(c,'/api/developer/keys',{'label':'외부 워커','scopes':['custom:jobs']})
    h={'Authorization':'Bearer '+k['key']};u=TestClient(app)
    assert u.get('/v1/custom/jobs',headers=h).json()[0]['id']==job['id']
    claim=u.post('/v1/custom/jobs/'+job['id']+'/claim',headers=h,json={})
    assert claim.status_code==200,claim.text
    token=claim.json()['claim_token']
    assert u.post('/v1/custom/jobs/'+job['id']+'/claim',headers=h,json={}).status_code==409
    p='/v1/custom/jobs/'+job['id']+'/complete'
    body={'claim_token':token,'state':'completed','result':'완료'}
    assert u.post(p,headers=h,json=body).json()['state']=='completed'
    assert u.post(p,headers=h,json=body).json()['state']=='completed'

def test_domain_verification_gate(monkeypatch):
    c=setup('domain')
    d=post(c,'/api/domains',{'hostname':'chat.example.com'})['domain']
    assert d['active'] is False
    assert c.post('/api/domains',json={'hostname':'127.0.0.1'}).status_code==422
    monkeypatch.setattr(domains,'verify_remote',lambda r:True)
    assert post(c,'/api/domains/verify',{})['domain']['active'] is True
    assert owner().get('/api/domains').status_code==403

def test_simulated_messages_reserve_exactly_one():
    c=setup('new_alert')
    purchase(c,'message','sms-credit',name='SMS',quantity=100)
    post(c,'/api/message-notifications',{'phone':'01012345678','kind':'SMS','enabled':True,'consent':True})
    u,t=public(c)
    post(u,'/api/chat',{'token':t,'message':'가격은?','clientMessageId':'notify'})
    with db() as d:
        ws=next(x['ws'] for x in d.execute('SELECT ws FROM message_notify_config WHERE phone=?',('01012345678',)))
    # sqlite Row supports key access; do not use external sends.
    assert message_notifications.dispatch(ws)>=1
    count=c.get('/api/message-notifications').json()['balance']['SMS']
    assert count==99
    message_notifications.dispatch(ws)
    assert c.get('/api/message-notifications').json()['balance']['SMS']==99

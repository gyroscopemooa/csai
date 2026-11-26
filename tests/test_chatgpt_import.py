from test_app import owner,post
from test_billing import order,paid
import ai
import chatgpt_import as migration

TEXT='상담 가격? => 10만원입니다.'
def buy(c):
    return paid(c,order(c,'chatgpt_import',client='migration'))
def quote(c,text=TEXT):
    return post(c,'/api/chatgpt-import/quote',{'text':text,'consent':True})
def analyze(c,q,text=TEXT):
    return post(c,'/api/chatgpt-import/'+q['id']+'/analyze',{'text':text,'consent':True,'maxCredits':q['maxCredits']})

def test_migration_purchase_gate_quote_and_approval():
    c=owner()
    assert c.post('/api/chatgpt-import/quote',json={'text':TEXT,'consent':True}).status_code==403
    assert buy(c)['amount']==19900
    assert c.post('/api/billing/orders',json={'kind':'chatgpt_import','client':'other'}).status_code==409
    q=quote(c)
    assert c.get('/api/me').json()['credits']==20
    path='/api/chatgpt-import/'+q['id']+'/analyze'
    assert c.post(path,json={'text':'changed','consent':True,'maxCredits':q['maxCredits']}).status_code==409
    assert c.post(path,json={'text':TEXT,'maxCredits':q['maxCredits']}).status_code==422
    stranger=owner();buy(stranger)
    assert stranger.post(path,json={'text':TEXT,'consent':True,'maxCredits':q['maxCredits']}).status_code==404
    r=analyze(c,q);balance=c.get('/api/me').json()['credits']
    assert balance==20-r['cost']
    assert analyze(c,q)['duplicate'] is True
    assert c.get('/api/me').json()['published']=={}
    post(c,'/api/training/'+r['id']+'/publish',{})
    assert c.get('/api/me').json()['credits']==balance
    assert c.get('/api/me').json()['published']['faq']
    assert c.post('/api/chatgpt-import/sandbox-refund',json={}).status_code==409

def test_migration_unused_refund_revokes_quote():
    c=owner();buy(c);q=quote(c)
    assert post(c,'/api/chatgpt-import/sandbox-refund',{})['sandbox']
    assert not c.get('/api/chatgpt-import/status').json()['owned']
    assert c.post('/api/chatgpt-import/'+q['id']+'/analyze',json={'text':TEXT,'consent':True,'maxCredits':q['maxCredits']}).status_code==403
    assert c.get('/api/me').json()['credits']==20

def test_migration_analysis_error_returns_credits(monkeypatch):
    c=owner();buy(c);q=quote(c)
    def fail(*args):raise RuntimeError('provider failed')
    monkeypatch.setattr(ai,'train',fail)
    assert c.post('/api/chatgpt-import/'+q['id']+'/analyze',json={'text':TEXT,'consent':True,'maxCredits':q['maxCredits']}).status_code==502
    assert c.get('/api/me').json()['credits']==20
    assert c.get('/api/training').json()==[]

def test_migration_insufficient_credit_and_production_gate(monkeypatch):
    c=owner();buy(c);text='가'*12000;q=quote(c,text)
    assert q['maxCredits']>20
    assert c.post('/api/chatgpt-import/'+q['id']+'/analyze',json={'text':text,'consent':True,'maxCredits':q['maxCredits']}).status_code==402
    monkeypatch.setattr(migration,'DEMO',False)
    assert not c.get('/api/chatgpt-import/status').json()['available']
    assert c.post('/api/chatgpt-import/quote',json={'text':TEXT,'consent':True}).status_code==403

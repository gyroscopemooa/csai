from test_app import owner,post

def test_paid_memory_requires_entitlement_and_reuses_training():
    c=owner()
    body={'order':'missing','text':'배송 => 2일','consent':True}
    assert c.post('/api/memory-import/prepare',json=body).status_code==403
    o=post(c,'/api/billing/orders',{'kind':'memory_import','client':'memory-test','amount':1})
    assert o['amount']==19900
    assert c.post('/api/memory-import/prepare',json=body|{'order':o['id']}).status_code==403
    credits=c.get('/api/me').json()['credits']
    post(c,'/api/billing/orders/'+o['id']+'/sandbox-confirm',{})
    assert c.get('/api/me').json()['credits']==credits
    assert owner().post('/api/memory-import/prepare',json=body|{'order':o['id']}).status_code==403
    body['order']=o['id']
    j=post(c,'/api/memory-import/prepare',body)
    assert post(c,'/api/memory-import/prepare',body)['id']==j['id']
    post(c,'/api/billing/orders',{'kind':'education','sku':'mini','client':'memory-credit'})
    p=post(c,'/api/training/'+j['id']+'/run',{})
    assert p['cost']>0
    assert post(c,'/api/memory-import/prepare',body)['state']=='review'
    assert c.get('/api/me').json()['published']=={}
    post(c,'/api/training/'+j['id']+'/publish',{})
    assert post(c,'/api/memory-import/prepare',body)['state']=='published'

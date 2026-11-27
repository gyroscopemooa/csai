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


def test_unused_memory_pass_refund_revokes_entitlement():
    c = owner()
    credits = c.get('/api/me').json()['credits']
    order = post(c, '/api/billing/orders', {'kind': 'memory_import', 'client': 'unused-pass'})
    path = '/api/billing/orders/' + order['id']
    post(c, path + '/sandbox-confirm', {})
    refund = path + '/sandbox-refund'
    assert owner().post(refund, json={'confirmed': True}).status_code == 404
    assert post(c, refund, {'confirmed': True})['status'] == 'refunded'
    assert post(c, refund, {'confirmed': True})['status'] == 'refunded'
    assert c.get('/api/memory-import/paid-orders').json() == []
    assert c.post('/api/memory-import/prepare', json={
        'consent': True, 'order': order['id'], 'text': 'Business policy',
    }).status_code == 403
    assert c.get('/api/me').json()['credits'] == credits

from test_app import owner,post,patch,public

def test_separate_ratings_and_handoff():
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':[]})
    patch(c,{'enabled':True})
    u,token=public(c)
    before=c.get('/api/me').json()['remaining']
    assert u.post('/api/customer/feedback',json={'token':token,'business_score':5}).status_code==409
    assert post(u,'/api/customer/handoff',{'token':token})['manual']
    assert post(u,'/api/chat',{'token':token,'message':'문의','clientMessageId':'manual-rating'})['manual']
    assert c.get('/api/me').json()['remaining']==before
    tid=c.get('/api/inbox').json()[0]['id']
    post(c,'/api/inbox/'+tid,{'reply':'답변'})
    post(u,'/api/customer/feedback',{'token':token,'score':4,'business_score':5})
    post(u,'/api/customer/feedback',{'token':token,'business_score':3})
    r=c.get('/api/quality/overview').json()
    assert r['ratings']['n']==1 and r['ratings']['average']==4
    assert r['business_ratings']['n']==1 and r['business_ratings']['average']==3
    assert u.post('/api/customer/feedback',json={'token':token,'business_score':6}).status_code==422

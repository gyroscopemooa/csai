from test_app import owner,post,patch,public
from product_progress import compare_knowledge
def test_conflicts_and_private_drafts():
    assert len(compare_knowledge({'faq':[{'q':'배송?','a':'2일'}]},{'faq':[{'q':'배송','a':'3일'}]})['conflicts'])==1
    c=owner()
    assert post(c,'/api/quality/feature-draft/calendar',{'config':{'운영 시간':'09:00-18:00'}})['activated'] is False
    assert c.get('/api/me').json()['addons']==[]
    assert c.get('/api/quality/feature-draft/calendar').json()['config']['운영 시간']=='09:00-18:00'
    note=post(c,'/api/quality/private-notes',{'body':'내부 전용 메모'})
    assert owner().get('/api/quality/private-notes').json()==[]
    assert c.get('/api/training').json()==[]
    assert c.delete('/api/quality/private-notes/'+note['id']).status_code==200
def test_feedback_and_staff_batch():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]})
    patch(c,{'enabled':True,'consultation_mode':'staff'})
    u,t=public(c)
    post(u,'/api/chat',{'token':t,'message':'문의','clientMessageId':'feedback-one'})
    tid=c.get('/api/inbox').json()[0]['id']
    post(c,'/api/inbox/'+tid,{'reply':'답변','manual':True})
    post(u,'/api/customer/feedback',{'token':t,'score':4})
    post(u,'/api/customer/feedback',{'token':t,'score':5})
    r=c.get('/api/quality/overview').json()
    assert r['ratings']['n']==1 and r['ratings']['average']==5
    assert post(c,'/api/quality/staff-source',{'threads':[tid],'consent':True})['pairs']==1
    assert owner().post('/api/quality/staff-source',json={'threads':[tid],'consent':True}).status_code==404

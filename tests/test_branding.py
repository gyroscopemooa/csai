from test_app import owner,post,patch,public,teach
from fastapi.testclient import TestClient
from app import app

def test_free_account_can_save_basic_company_logo():
    import base64, io
    from PIL import Image
    c=owner();image=io.BytesIO();Image.new('RGB',(20,20),'#3182f6').save(image,format='PNG')
    post(c,'/api/appearance',{'logo':base64.b64encode(image.getvalue()).decode()})
    assert c.get('/api/appearance').json()['logo'].startswith('data:image/png;base64,')
    assert c.post('/api/appearance',json={'theme':'toss'}).status_code==403

def test_alias_and_brand_entitlements():
    c=owner();assert c.post('/api/appearance',json={'alias':'snap-test'}).status_code==403;post(c,'/api/demo/billing',{'plan':'lite','addons':['custom_url','design','unbrand']});patch(c,{'enabled':True});post(c,'/api/appearance',{'alias':'snap-test','color':'#123456','unbrand':True});assert c.get('/api/public/snap-test').json()['color']=='#123456';assert c.get('/api/public/snap-test').json()['unbrand'];b=owner();post(b,'/api/demo/billing',{'plan':'lite','addons':['custom_url']});assert b.post('/api/appearance',json={'alias':'snap-test'}).status_code==409;post(c,'/api/demo/billing',{'plan':'lite','addons':[]});assert c.get('/api/public/snap-test').status_code==404

def test_extra_assistant_independent_faq_shared_quota():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent']});patch(c,{'enabled':True});teach(c,'배송','기본 답변');a=post(c,'/api/agents',{'brand':'추가 상담원','tone':'정중','welcome':'안녕하세요','fallback':'확인 필요','enabled':True});post(c,'/api/demo/billing',{'education':'mini'});j=post(c,'/api/training/estimate',{'agent':a['id'],'text':'배송 => 개별 답변'});post(c,'/api/training/'+j['id']+'/run',{});post(c,'/api/training/'+j['id']+'/publish',{});assert c.get('/api/public/'+a['slug']).json()['brand']=='추가 상담원';u=TestClient(app);t=post(u,'/api/session',{'slug':a['slug']})['token'];assert post(u,'/api/chat',{'token':t,'message':'배송','clientMessageId':'a'})['reply']=='개별 답변';v,t2=public(c);assert post(v,'/api/chat',{'token':t2,'message':'배송','clientMessageId':'a'})['reply']=='기본 답변';assert c.get('/api/me').json()['remaining']==298


def test_quantity_and_brand_test_isolation():
    from test_billing import order,paid
    c=owner()
    o=order(c,'subscription',plan='lite',addons=['extra_agent'],brand_quantity=2,client='brand-two')
    assert o['amount']==19700
    paid(c,o)
    assert c.get('/api/me').json()['brand_quantity']==2
    patch(c,{'price':'기본 가격'})
    a=post(c,'/api/agents',{'brand':'A','welcome':'A','price':'A 가격','enabled':False})
    b=post(c,'/api/agents',{'create':True,'brand':'B','welcome':'B','price':'B 가격','enabled':False})
    assert a['id']!=b['id']
    assert c.post('/api/agents',json={'create':True,'brand':'C','welcome':'C'}).status_code==409
    for agent,expected in [(a,'A 가격'),(b,'B 가격')]:
        token=post(c,'/api/session',{'test':True,'agent':agent['id']})['token']
        assert post(c,'/api/chat',{'token':token,'message':'가격은?','clientMessageId':'one'})['reply']==expected
    assert c.get('/api/me').json()['remaining']==298
    assert len(c.get('/api/inbox?agent='+a['id']).json())==1
    assert owner().post('/api/session',json={'test':True,'agent':a['id']}).status_code==403

from test_app import owner,post,patch,public,teach
from fastapi.testclient import TestClient
from app import app

def test_alias_and_brand_entitlements():
    c=owner();assert c.post('/api/appearance',json={'alias':'snap-test'}).status_code==403;post(c,'/api/demo/billing',{'plan':'lite','addons':['custom_url','design','unbrand']});patch(c,{'enabled':True});post(c,'/api/appearance',{'alias':'snap-test','color':'#123456','unbrand':True});assert c.get('/api/public/snap-test').json()['color']=='#123456';assert c.get('/api/public/snap-test').json()['unbrand'];b=owner();post(b,'/api/demo/billing',{'plan':'lite','addons':['custom_url']});assert b.post('/api/appearance',json={'alias':'snap-test'}).status_code==409;post(c,'/api/demo/billing',{'plan':'lite','addons':[]});assert c.get('/api/public/snap-test').status_code==404

def test_extra_assistant_independent_faq_shared_quota():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent']});patch(c,{'enabled':True});teach(c,'배송','기본 답변');a=post(c,'/api/agents',{'brand':'추가 상담원','tone':'정중','welcome':'안녕하세요','fallback':'확인 필요','enabled':True});post(c,'/api/demo/billing',{'education':'mini'});j=post(c,'/api/training/estimate',{'agent':a['id'],'text':'배송 => 개별 답변'});post(c,'/api/training/'+j['id']+'/run',{});post(c,'/api/training/'+j['id']+'/publish',{});assert c.get('/api/public/'+a['slug']).json()['brand']=='추가 상담원';u=TestClient(app);t=post(u,'/api/session',{'slug':a['slug']})['token'];assert post(u,'/api/chat',{'token':t,'message':'배송','clientMessageId':'a'})['reply']=='개별 답변';v,t2=public(c);assert post(v,'/api/chat',{'token':t2,'message':'배송','clientMessageId':'a'})['reply']=='기본 답변';assert c.get('/api/me').json()['remaining']==298

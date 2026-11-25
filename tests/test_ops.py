from test_app import owner,post,patch,public,draft,confirm,setup_booking,future
from datetime import datetime,timedelta
from fastapi.testclient import TestClient
from app import app

def test_resources_and_customer_changes():
    c=setup_booking();patch(c,{'resources':[{'id':'default','name':'기본'},{'id':'a','name':'작가 A'}],'modes':{'change':'manual'}})
    u,t=public(c);b=draft(u,t);assert confirm(u,t,b).json()['status']=='confirmed'
    v,x=public(c);form=v.get('/api/booking/form/'+x).json();b2=post(v,'/api/booking/draft',{'token':x,'version':form['template_version'],'start':future(),'resource':'a','payload':{'name':'고객 A'}});assert confirm(v,x,b2).json()['status']=='confirmed'
    assert u.get('/api/customer/bookings/'+t).json()['bookings'][0]['id']==b['id'];assert len(u.get('/api/customer/bookings/'+t).json()['bookings'])==1
    assert v.post('/api/customer/bookings/'+b['id']+'/change',json={'token':x,'action':'cancel','confirmed':True}).status_code==404
    q=post(u,'/api/customer/bookings/'+b['id']+'/change',{'token':t,'action':'cancel','confirmed':True});assert q['state']=='pending';post(c,'/api/booking-changes/'+q['id'],{'action':'approve'});assert u.get('/api/customer/bookings/'+t).json()['bookings'][0]['status']=='cancelled';assert len(c.get('/api/events').json())>=3

def test_auto_change_and_paid_guard():
    c=setup_booking();patch(c,{'modes':{'change':'auto'}});u,t=public(c);b=draft(u,t);assert confirm(u,t,b).json()['status']=='confirmed'
    start=(datetime.now()+timedelta(days=4)).strftime('%Y-%m-%d')+'T15:00';q=post(u,'/api/customer/bookings/'+b['id']+'/change',{'token':t,'action':'change','start':start,'confirmed':True});assert q['state']=='approved';assert u.get('/api/customer/bookings/'+t).json()['bookings'][0]['start']!=b['start']
    c=setup_booking(payment=True);patch(c,{'modes':{'change':'auto'}});u,t=public(c);b=draft(u,t);confirm(u,t,b);post(c,'/api/bookings/'+b['id'],{'action':'approve','paid':True});assert post(u,'/api/customer/bookings/'+b['id']+'/change',{'token':t,'action':'cancel','confirmed':True})['state']=='pending'

def test_review_and_rollback():
    c=owner();j=post(c,'/api/training/estimate',{'text':'가격 => 100원'});post(c,'/api/training/'+j['id']+'/run',{});r=c.patch('/api/training/'+j['id']+'/review',json={'result':{'style':'친절','rules':['업체 정책'],'faq':[{'q':'가격','a':'200원'}],'conflicts':[]}});assert r.status_code==200;post(c,'/api/training/'+j['id']+'/publish',{});assert c.get('/api/me').json()['published']['faq'][0]['a']=='200원';v=c.get('/api/knowledge/versions').json()[0];assert owner().post('/api/knowledge/versions/'+v['id']+'/restore',json={}).status_code==404;post(c,'/api/knowledge/versions/'+v['id']+'/restore',{});assert c.get('/api/me').json()['published']=={}

def test_channel_simulation_entitlement_and_idempotency():
    c=owner();p={'channel':'naver','event_id':'id','payload':{'event':'send','user':'test','textContent':{'text':'가격은?'}}};assert c.post('/api/channels/simulate',json=p).status_code==403;post(c,'/api/demo/billing',{'plan':'lite','addons':['channels']});patch(c,{'enabled':True,'price':'100원'});r=post(c,'/api/channels/simulate',p);assert r['response']['textContent']['text']=='100원';assert post(c,'/api/channels/simulate',p)['remaining']==299;assert c.get('/api/inbox').json()[0]['kind']=='naver';r=post(c,'/api/channels/simulate',{'channel':'kakao','payload':{'userRequest':{'user':{'id':'tester'},'utterance':'가격'}}});assert r['response']['template']['outputs'][0]['simpleText']['text']=='100원'

def test_work_intake_and_edit():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['quote','tasks']});patch(c,{'enabled':True});u,t=public(c);assert u.get('/api/customer/requests/'+t).json()==['quote','tasks'];p={'token':t,'kind':'quote','title':'촬영 견적','details':'부산 2명','confirmed':True};r=post(u,'/api/customer/requests',p);assert post(u,'/api/customer/requests',p)['duplicate'];assert c.patch('/api/work/'+r['id'],json={'status':'pending'}).status_code==200;tid=c.get('/api/inbox').json()[0]['id'];r2=post(c,'/api/inbox/'+tid+'/work',{'kind':'tasks','title':'견적 검토','details':'확인'});assert len(c.get('/api/work').json())==2;assert owner().delete('/api/work/'+r2['id']).status_code==404;assert c.delete('/api/work/'+r2['id']).status_code==200

def test_notification_outbox_and_read(monkeypatch):
    monkeypatch.delenv('RESEND_API_KEY',raising=False);monkeypatch.delenv('RESEND_FROM',raising=False);c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['email','new_alert','unknown_alert']});patch(c,{'enabled':True});post(c,'/api/notifications',{'email':'test@example.com','enabled':True});u,t=public(c);post(u,'/api/chat',{'token':t,'clientMessageId':'test','message':'새로운 질문'});assert len(c.get('/api/events').json())==2;r=post(c,'/api/notifications/dispatch',{});assert len(r['results'])==2 and all(x['status']=='simulated' for x in r['results']);assert post(c,'/api/notifications/dispatch',{})['results']==[];post(c,'/api/events/read',{});assert all(x['seen'] for x in c.get('/api/events').json())

def test_chat_proposes_structured_work_and_requires_confirmation():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['quote']});patch(c,{'enabled':True});u,t=public(c);r=post(u,'/api/chat',{'token':t,'message':'스냅 견적 부탁합니다','clientMessageId':'work'});assert r['workDraft']['kind']=='quote';assert c.get('/api/work').json()==[];p=r['workDraft']|{'token':t,'confirmed':True};post(u,'/api/customer/requests',p);assert c.get('/api/work').json()[0]['kind']=='quote'

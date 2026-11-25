from test_app import owner,post,patch,public,draft,confirm,setup_booking
from store import db,one,now
import notifications

def test_recovery_transfer_isolated_single_use():
    c=setup_booking();u,t=public(c);b=draft(u,t);assert confirm(u,t,b).json()['status']=='confirmed'
    v,new=public(c);x,other=public(setup_booking());p='/api/customer/bookings/'+b['id']+'/recovery-code';assert v.post(p,json={'token':new}).status_code==404
    code=post(u,p,{'token':t})['code'];withheld=post(u,p,{'token':t})['code'];assert code!=withheld
    with db() as conn:assert one(conn,'SELECT secret_hash FROM booking_recovery WHERE booking=?',(b['id'],))['secret_hash']!=withheld
    endpoint='/api/customer/bookings/recover';assert x.post(endpoint,json={'token':other,'code':withheld}).status_code==404;assert v.post(endpoint,json={'token':new,'code':code}).status_code==404
    assert post(v,endpoint,{'token':new,'code':withheld})['booking']==b['id'];assert v.post(endpoint,json={'token':new,'code':withheld}).status_code==404
    assert not u.get('/api/customer/bookings/'+t).json()['bookings'];assert v.get('/api/customer/bookings/'+new).json()['bookings'][0]['id']==b['id']
    assert u.post('/api/customer/bookings/'+b['id']+'/change',json={'token':t,'action':'cancel','confirmed':True}).status_code==404
    assert v.get('/api/session/'+new+'/messages').json()==[]

def test_recovery_expired():
    c=setup_booking();u,t=public(c);b=draft(u,t);confirm(u,t,b);r=post(u,'/api/customer/bookings/'+b['id']+'/recovery-code',{'token':t});v,new=public(c)
    with db(True) as conn:conn.execute('UPDATE booking_recovery SET expires=? WHERE booking=?',(now()-1,b['id']))
    assert v.post('/api/customer/bookings/recover',json={'token':new,'code':r['code']}).status_code==404

def test_worker_demo_no_real_send_even_with_key(monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY','fake');monkeypatch.setenv('RESEND_FROM','fake@example.com');monkeypatch.setenv('ENABLE_LIVE_EMAIL','1');monkeypatch.setattr(notifications.httpx,'post',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('must not send')))
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['email','new_alert','unknown_alert']});patch(c,{'enabled':True});post(c,'/api/notifications',{'email':'test@example.com','enabled':True});u,t=public(c);post(u,'/api/chat',{'token':t,'clientMessageId':'worker','message':'새로운 질문'})
    notifications.tick();result=c.get('/api/notifications').json();assert len(result['deliveries'])==2;assert all(d['status']=='simulated' for d in result['deliveries']);notifications.tick();assert len(c.get('/api/notifications').json()['deliveries'])==2

def test_worker_respects_optout():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['email','new_alert','unknown_alert']});patch(c,{'enabled':True,'modes':{'email':'off'}});post(c,'/api/notifications',{'email':'test@example.com','enabled':True});u,t=public(c);post(u,'/api/chat',{'token':t,'clientMessageId':'worker','message':'새로운 질문'});notifications.tick();assert not c.get('/api/notifications').json()['deliveries']

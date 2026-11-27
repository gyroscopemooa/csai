from datetime import datetime,timedelta
from test_app import owner,post

def test_brand_calendar_scope_and_settings():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent','calendar','change_booking']})
    a=post(c,'/api/agents',{'create':True,'brand':'별도 브랜드','welcome':'안녕하세요'})['id']
    path='/api/brand-calendar/'+a
    assert owner().get(path).status_code in (403,404)
    s=post(c,path+'/settings',{'open':'08:00','close':'20:00','duration':30})['settings']
    start=(datetime.now()+timedelta(days=3)).replace(hour=13,minute=0,second=0,microsecond=0).isoformat()
    b={'start':start,'version':s['template_version'],'payload':{'title':'브랜드 일정'}}
    item=post(c,path+'/bookings',b)
    assert item['agent']==a
    assert c.post(path+'/bookings',json=b).status_code==409
    assert not any(x['id']==item['id'] for x in c.get('/api/bookings').json())
    assert c.post('/api/bookings/'+item['id'],json={'action':'cancel'}).status_code==404
    assert post(c,path+'/bookings/'+item['id'],{'action':'cancel'})['status']=='cancelled'


def test_brand_calendar_cross_brand_booking_edit_is_denied():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent','calendar','change_booking'],'brand_quantity':2})
    a=post(c,'/api/agents',{'create':True,'brand':'브랜드 A','welcome':'안녕하세요'})['id']
    b=post(c,'/api/agents',{'create':True,'brand':'브랜드 B','welcome':'안녕하세요'})['id']
    start=(datetime.now()+timedelta(days=3)).replace(hour=13,minute=0,second=0,microsecond=0).isoformat()
    pa='/api/brand-calendar/'+a;pb='/api/brand-calendar/'+b
    body={'start':start,'version':1,'payload':{'title':'별도 예약'}}
    x=post(c,pa+'/bookings',body);y=post(c,pb+'/bookings',body)
    assert x['id']!=y['id']
    assert c.post(pb+'/bookings/'+x['id'],json={'action':'cancel'}).status_code==404
    assert c.get(pa).json()['bookings'][0]['status']=='confirmed'
    assert c.get(pb).json()['bookings'][0]['status']=='confirmed'


def test_public_brand_booking_manual_and_isolation():
    from fastapi.testclient import TestClient
    from app import app
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent','calendar'],'brand_quantity':2})
    a=post(c,'/api/agents',{'create':True,'brand':'고객 예약 A','welcome':'안녕하세요','enabled':True})
    b=post(c,'/api/agents',{'create':True,'brand':'고객 예약 B','welcome':'안녕하세요','enabled':True})
    pa='/api/brand-calendar/'+a['id'];pb='/api/brand-calendar/'+b['id']
    assert not c.get('/api/public/'+a['slug']).json()['calendar']
    for path in (pa,pb):
        assert c.post(path+'/settings',json={'booking_mode':'auto'}).status_code==403
        post(c,path+'/settings',{'booking_mode':'manual'})
    u=TestClient(app);v=TestClient(app);another=TestClient(app)
    token=post(u,'/api/session',{'slug':a['slug']})['token']
    other_token=post(v,'/api/session',{'slug':b['slug']})['token']
    same_brand_token=post(another,'/api/session',{'slug':a['slug']})['token']
    assert u.get('/api/public/'+a['slug']).json()['calendar']
    date=(datetime.now()+timedelta(days=3)).strftime('%Y-%m-%d')
    form=u.get('/api/booking/form/'+token).json()
    assert '13:00' in post(u,'/api/booking/availability',{'token':token,'date':date})
    data={'token':token,'start':date+'T13:00','version':form['template_version'],'payload':{'title':'브랜드 예약'}}
    draft=post(u,'/api/booking/draft',data)
    assert not c.get(pa).json()['bookings']
    confirm='/api/booking/'+draft['id']+'/confirm'
    assert v.post(confirm,json={'token':other_token,'confirmation':draft['token']}).status_code==403
    assert another.post(confirm,json={'token':same_brand_token,'confirmation':draft['token']}).status_code==403
    body={'token':token,'confirmation':draft['token']}
    assert post(u,confirm,body)['status']=='pending'
    assert post(u,confirm,body)['status']=='pending'
    assert post(c,pa+'/bookings/'+draft['id'],{'action':'approve'})['status']=='confirmed'
    assert '13:00' not in post(u,'/api/booking/availability',{'token':token,'date':date})
    assert '13:00' in post(v,'/api/booking/availability',{'token':other_token,'date':date})
    assert not c.get(pb).json()['bookings']
    assert not c.get('/api/bookings').json()
    own=u.get('/api/customer/bookings/'+token).json()
    assert len(own['bookings'])==1 and not own['canChange'] and not own['canRecover']
    assert not v.get('/api/customer/bookings/'+other_token).json()['bookings']
    assert not another.get('/api/customer/bookings/'+same_brand_token).json()['bookings']
    test_token=post(c,'/api/session',{'test':True,'agent':a['id']})['token']
    assert c.post('/api/booking/draft',json=data|{'token':test_token}).status_code==409
    post(c,pa+'/settings',{'booking_mode':'off'})
    assert u.post('/api/booking/draft',json=data).status_code==409


def test_brand_customer_change_requires_approval_and_ownership():
    from fastapi.testclient import TestClient
    from app import app
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent','calendar','change_booking'],'brand_quantity':2})
    a=post(c,'/api/agents',{'create':True,'brand':'A','welcome':'안녕하세요','enabled':True})
    b=post(c,'/api/agents',{'create':True,'brand':'B','welcome':'안녕하세요','enabled':True})
    pa='/api/brand-calendar/'+a['id'];pb='/api/brand-calendar/'+b['id']
    for path in (pa,pb):post(c,path+'/settings',{'booking_mode':'manual','allow_customer_change':True})
    u=TestClient(app);v=TestClient(app)
    token=post(u,'/api/session',{'slug':a['slug']})['token']
    other=post(v,'/api/session',{'slug':b['slug']})['token']
    day=(datetime.now()+timedelta(days=3)).strftime('%Y-%m-%d')
    form=u.get('/api/booking/form/'+token).json()
    d=post(u,'/api/booking/draft',{'token':token,'start':day+'T13:00','version':form['template_version'],'payload':{'title':'예약'}})
    post(u,'/api/booking/'+d['id']+'/confirm',{'token':token,'confirmation':d['token']})
    post(c,pa+'/bookings/'+d['id'],{'action':'approve'})
    path='/api/customer/bookings/'+d['id']+'/change'
    req={'token':token,'action':'change','start':day+'T15:00','confirmed':True}
    assert v.post(path,json=req|{'token':other}).status_code==404
    change=post(u,path,req)
    assert change['state']=='pending'
    assert u.post(path,json=req).status_code==409
    assert c.get(pb+'/changes').json()==[]
    assert c.post(pb+'/changes/'+change['id'],json={'action':'approve'}).status_code==404
    assert post(c,pa+'/changes/'+change['id'],{'action':'approve'})['ok']
    mine=u.get('/api/customer/bookings/'+token).json()
    assert mine['canChange'] and mine['requests'][0]['state']=='approved'
    assert mine['bookings'][0]['start']!=d['start']
    cancel=post(u,path,{'token':token,'action':'cancel','confirmed':True})
    assert post(c,pa+'/changes/'+cancel['id'],{'action':'approve'})['ok']
    assert u.get('/api/customer/bookings/'+token).json()['bookings'][0]['status']=='cancelled'

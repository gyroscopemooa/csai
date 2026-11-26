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

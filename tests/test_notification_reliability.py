from test_app import owner,post,patch,setup_booking,future
from datetime import datetime,timedelta

def test_admin_booking_events():
    c=setup_booking()
    b=post(c,'/api/bookings',{'start':future(),'payload':{'name':'테스트'}})
    a=(datetime.now()+timedelta(days=4)).strftime('%Y-%m-%d')+'T14:00'
    post(c,'/api/bookings/'+b['id'],{'action':'change','start':a})
    post(c,'/api/bookings/'+b['id'],{'action':'cancel'})
    titles=[x['title'] for x in c.get('/api/events').json() if x['kind']=='booking']
    assert '관리자 예약 등록' in titles
    assert '관리자 예약 변경' in titles
    assert '관리자 예약 취소' in titles

def test_live_email_requires_verified_address(monkeypatch):
    import ops
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['email']})
    monkeypatch.setattr(ops,'DEMO',False)
    assert c.post('/api/notifications',json={'email':'test@example.com','enabled':True}).status_code==403

def test_worker_continues_after_individual_failure(monkeypatch):
    import worker
    calls=[]
    def broken():raise RuntimeError('simulated')
    monkeypatch.setenv('ENABLE_AUTO_MESSAGES','1')
    monkeypatch.setenv('ENABLE_AUTO_EMAIL','1')
    monkeypatch.setattr(worker.message_notifications,'tick',broken)
    monkeypatch.setattr(worker.notifications,'tick',lambda:calls.append('email'))
    monkeypatch.setattr(worker.channel_live,'enabled',lambda:False)
    for flag in ('ENABLE_AUTO_DOMAINS','ENABLE_AUTO_PUSH','ENABLE_AUTO_REPORTS','ENABLE_AUTO_CALENDAR'):
        monkeypatch.setenv(flag,'0')
    worker.tick_once()
    assert calls==['email']

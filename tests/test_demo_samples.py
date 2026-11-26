from test_app import owner
from test_demo_views import local_client
from app import available
from store import db, one, uid, now

def test_sample_conversations_are_local_read_only_and_removable():
    c = owner()
    ws = c.get('/api/me').json()['slug']
    before = c.get('/api/me').json()['remaining']
    r = c.post('/api/demo/samples')
    assert r.status_code == 200 and r.json() == {'count': 9, 'created': True}
    assert c.post('/api/demo/samples').json() == {'count': 9, 'created': False}
    assert c.get('/api/me').json()['remaining'] == before
    items = c.get('/api/inbox').json()
    assert len(items) == 9 and all(t['sample'] for t in items)
    assert {'public', 'naver', 'kakao', 'test'} == {t['kind'] for t in items}
    assert len(c.get('/api/inbox?kind=public&q=반려견').json()) == 1
    longest = max(items, key=lambda t: len(c.get('/api/inbox/' + t['id']).json()['messages']))
    detail = c.get('/api/inbox/' + longest['id']).json()
    assert detail['sample'] is True and len(detail['messages']) >= 20
    assert c.post('/api/inbox/' + longest['id'], json={'reply': '가짜 답변'}).status_code == 409
    # A real local thread in the same workspace must survive sample cleanup.
    with db(True) as conn:
        workspace_id = one(conn, 'SELECT id FROM workspace WHERE slug=?', (ws,))['id']
        visitor = uid(); real_thread = uid()
        conn.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)', (visitor, workspace_id, now()+3600, 'test'))
        conn.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)', (real_thread, workspace_id, visitor, 'test', now()))
        conn.execute('INSERT INTO message VALUES(?,?,?,?,?,?)', (uid(), workspace_id, real_thread, 'user', '실제 테스트 대화', now()))
    assert c.delete('/api/demo/samples').json()['removed'] == 9
    remaining = c.get('/api/inbox').json()
    assert len(remaining) == 1 and remaining[0]['id'] == real_thread and not remaining[0]['sample']

def test_sample_data_is_isolated_per_local_demo_owner():
    a, b = owner(), owner()
    assert a.post('/api/demo/samples').status_code == 200
    assert b.get('/api/inbox').json() == []

def test_developer_sample_booking_and_work_follow_conversations():
    c=local_client()
    assert c.post('/api/demo/view',json={'mode':'developer'}).status_code==200
    assert c.post('/api/demo/samples').json()['count']==9
    bookings=c.get('/api/bookings').json()
    assert len(bookings)==1 and bookings[0]['sample'] and bookings[0]['status']=='confirmed'
    with db() as connection:
        ws=one(connection,'SELECT id FROM workspace WHERE slug=?',(c.get('/api/me').json()['slug'],))['id']
        assert available(connection,ws,bookings[0]['start'],bookings[0]['end'])
    linked=c.get('/api/inbox/'+bookings[0]['sample_thread']).json()
    assert linked['sample'] and any('예약이 확정되었습니다' in m['body'] for m in linked['messages'])
    works=c.get('/api/work').json()
    assert len(works)==3 and all(x['sample'] for x in works)
    assert all(c.get('/api/inbox/'+x['sample_thread']).json()['sample'] for x in works)
    assert c.get('/api/stats').json()['threads']==0
    events=c.get('/api/events').json()
    assert any(x['sample'] and x['ref']==bookings[0]['id'] for x in events)
    unknown=c.get('/api/unknown').json()
    assert len(unknown)==1 and unknown[0]['sample']
    assert c.post('/api/faq',json={'q':unknown[0]['q'],'a':'가짜 답변','unknown':unknown[0]['id']}).status_code==409
    assert c.post('/api/bookings/'+bookings[0]['id'],json={'action':'cancel'}).status_code==409
    assert c.delete('/api/work/'+works[0]['id']).status_code==409
    assert c.delete('/api/demo/samples').json()['removed']==9
    assert c.get('/api/bookings').json()==[]
    assert c.get('/api/work').json()==[]
    assert c.get('/api/unknown').json()==[]
    assert not any(x['sample'] for x in c.get('/api/events').json())

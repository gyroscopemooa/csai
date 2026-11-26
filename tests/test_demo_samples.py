from test_app import owner
from store import db, one, uid, now

def test_sample_conversations_are_local_read_only_and_removable():
    c = owner()
    ws = c.get('/api/me').json()['slug']
    before = c.get('/api/me').json()['remaining']
    r = c.post('/api/demo/samples')
    assert r.status_code == 200 and r.json() == {'count': 8, 'created': True}
    assert c.post('/api/demo/samples').json() == {'count': 8, 'created': False}
    assert c.get('/api/me').json()['remaining'] == before
    items = c.get('/api/inbox').json()
    assert len(items) == 8 and all(t['sample'] for t in items)
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
    assert c.delete('/api/demo/samples').json()['removed'] == 8
    remaining = c.get('/api/inbox').json()
    assert len(remaining) == 1 and remaining[0]['id'] == real_thread and not remaining[0]['sample']

def test_sample_data_is_isolated_per_local_demo_owner():
    a, b = owner(), owner()
    assert a.post('/api/demo/samples').status_code == 200
    assert b.get('/api/inbox').json() == []

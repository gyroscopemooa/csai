from fastapi.testclient import TestClient
from app import app
from store import db, one, uid, now, workspace


def local_client():
    client=TestClient(app,base_url='http://127.0.0.1:3000')
    assert client.get('/auth/demo').status_code==200
    return client


def switch(client,mode):
    result=client.post('/api/demo/view',json={'mode':mode})
    assert result.status_code==200,result.text
    return client.get('/api/me').json()


def test_local_free_subscriber_and_developer_views_are_separate():
    client=local_client()
    free=client.get('/api/me').json()
    assert free['demo_view']=='free' and free['plan']=='free' and free['remaining']==1
    subscriber=switch(client,'subscriber')
    assert subscriber['plan']=='lite' and subscriber['demo_view']=='subscriber'
    assert subscriber['entitlements']==[] and not subscriber['operator']
    assert subscriber['slug']!=free['slug']
    assert client.patch('/api/settings',json={'brand':'유료 화면 업체'}).status_code==200
    developer=switch(client,'developer')
    assert developer['demo_view']=='developer' and developer['plan']=='lite'
    assert {'extra_agent','widget','design','calendar'} <= set(developer['entitlements'])
    assert 'naver' not in developer['entitlements'] and not developer['operator']
    assert developer['slug'] not in (free['slug'],subscriber['slug'])
    assert switch(client,'free')['settings']['brand']=='나의 업체'
    assert switch(client,'subscriber')['settings']['brand']=='유료 화면 업체'


def test_demo_view_rejects_non_demo_identity_and_bad_mode():
    client=local_client()
    assert client.post('/api/demo/view',json={'mode':'operator'}).status_code==422
    remote=TestClient(app,base_url='https://example.invalid')
    remote.cookies.set('csai_session',client.cookies.get('csai_session'))
    assert remote.post('/api/demo/view',json={'mode':'developer'}).status_code==403
    with db(True) as connection:
        user=workspace(connection,'google:'+uid())
        token=uid()
        connection.execute('INSERT INTO session VALUES(?,?,?)',(token,user['id'],now()+3600))
    other=TestClient(app,base_url='http://127.0.0.1:3000')
    other.cookies.set('csai_session',token)
    assert other.post('/api/demo/view',json={'mode':'developer'}).status_code==403

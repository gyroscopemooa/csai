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
    subscriber_agent=switch(client,'subscriber_agent')
    assert subscriber_agent['plan']=='lite' and subscriber_agent['demo_view']=='subscriber_agent'
    assert subscriber_agent['entitlements']==['extra_agent'] and not subscriber_agent['operator']
    assert subscriber_agent['slug'] not in (free['slug'],subscriber['slug'])
    agent=client.post('/api/agents',json={'brand':'웨딩 상담원','tone':'정중하게','welcome':'웨딩 문의 도와드릴게요.','fallback':'담당자 확인이 필요합니다.','enabled':True})
    assert agent.status_code==200,agent.text
    assert client.get('/api/agents').json()['settings']['brand']=='웨딩 상담원'
    developer=switch(client,'developer')
    assert developer['demo_view']=='developer' and developer['plan']=='lite'
    assert {'extra_agent','widget','design','calendar'} <= set(developer['entitlements'])
    assert 'naver' not in developer['entitlements'] and not developer['operator']
    assert developer['slug'] not in (free['slug'],subscriber['slug'])
    assert switch(client,'free')['settings']['brand']=='나의 업체'
    assert switch(client,'subscriber')['settings']['brand']=='유료 화면 업체'
    assert switch(client,'subscriber_agent')['entitlements']==['extra_agent']
    assert client.get('/api/agents').json()['settings']['brand']=='웨딩 상담원'


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


def test_test_conversation_can_be_removed_without_refunding_usage():
    client=local_client()
    switch(client,'subscriber')
    session=client.post('/api/session',json={'test':True}).json()
    answer=client.post('/api/chat',json={'token':session['token'],'message':'가격이 궁금해요','clientMessageId':'one'})
    assert answer.status_code==200,answer.text
    remaining=client.get('/api/me').json()['remaining']
    assert client.get('/api/inbox?kind=test').json()[0]['id']==session['thread']
    deleted=client.delete('/api/inbox/'+session['thread'])
    assert deleted.status_code==200,deleted.text
    assert client.get('/api/inbox?kind=test').json()==[]
    assert client.get('/api/me').json()['remaining']==remaining
    assert client.delete('/api/inbox/'+session['thread']).status_code==404
    with db(True) as connection:
        ws=one(connection,'SELECT id FROM workspace WHERE slug=?',(client.get('/api/me').json()['slug'],))['id']
        visitor_id=uid()
        customer_thread=uid()
        connection.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(visitor_id,ws,now()+3600,'public'))
        connection.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(customer_thread,ws,visitor_id,'public',now()))
    assert client.delete('/api/inbox/'+customer_thread).status_code==409

from test_app import owner, post, patch, public


def test_response_style_routes_and_notifies_once():
    c = owner()
    post(c, '/api/demo/billing', {'plan':'lite'})
    patch(c, {'enabled':True, 'price':'5000원'})
    notice = '사장님께 확인을 요청했습니다.'
    for level, question, unknown in [(2,'개인정보 유출',False),(1,'수중촬영도 가능한가요?',True),(0,'가격은?',False)]:
        post(c,'/api/response-style',{'level':level,'notify':True,'message':notice})
        visitor,token = public(c)
        body = {'token':token,'message':question,'clientMessageId':'1'}
        reply = post(visitor,'/api/chat',body)
        assert reply['ownerHandoff'] and reply['manual'] and reply['unknown'] is unknown
        assert notice in reply['reply'] and post(visitor,'/api/chat',body)==reply
        assert 'ownerHandoff' not in post(visitor,'/api/chat',dict(body,clientMessageId='2'))
    assert len([x for x in c.get('/api/events').json() if x['kind']=='handoff'])==3

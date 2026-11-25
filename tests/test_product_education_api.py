from test_app import owner, post, patch, TestClient, app, teach
import io, zipfile, socket
import ai
import education_url

def test_paid_prompt_cannot_be_changed_directly():
    c=owner()
    assert c.patch('/api/settings',json={'prompt':'교육 과금 우회'}).status_code==422
    q=post(c,'/api/faq',{'q':'배송','a':'무료 배송'})
    assert q['requires_run']
    before=c.get('/api/me').json()['credits']
    r=post(c,'/api/training/'+q['id']+'/run',{})
    assert c.get('/api/me').json()['credits']==before-r['cost']
    assert c.get('/api/me').json()['published']=={}
    post(c,'/api/training/'+q['id']+'/publish',{})
    assert c.get('/api/me').json()['published']['faq']

def test_additional_agent_teaching_cannot_bypass_credits():
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent']})
    a=post(c,'/api/agents',{'brand':'별도 상담원','welcome':'안녕하세요','enabled':True})
    assert c.post('/api/agents',json={'faq':[{'q':'배송','a':'우회'}]}).status_code==422
    j=post(c,'/api/training/estimate',{'agent':a['id'],'text':'배송 => 별도 답변'})
    before=c.get('/api/me').json()['credits']
    r=post(c,'/api/training/'+j['id']+'/run',{})
    assert c.get('/api/me').json()['credits']==before-r['cost']
    post(c,'/api/training/'+j['id']+'/publish',{})
    assert c.get('/api/me').json()['published']=={}
    assert c.get('/api/agents').json()['published']['faq'][0]['a']=='별도 답변'

def test_api_access_and_revocation():
    c=owner()
    assert c.get('/api/developer/keys').status_code==403
    post(c,'/api/demo/billing',{'plan':'lite','addons':['external_api']})
    patch(c,{'enabled':True,'price':'100원'})
    assert c.post('/api/developer/keys',json={'label':'금지','scopes':['bookings:read']}).status_code==403
    key=post(c,'/api/developer/keys',{'label':'테스트','scopes':['chat']})
    assert 'key' not in c.get('/api/developer/keys').json()['keys'][0]
    assert 'digest' not in c.get('/api/developer/keys').json()['keys'][0]
    client=TestClient(app);h={'Authorization':'Bearer '+key['key']}
    assert client.get('/v1/bookings',headers=h).status_code==403
    session=client.post('/v1/chat/sessions',headers=h)
    assert session.status_code==200,session.text
    body={'session':session.json()['session'],'message':'가격은?','clientMessageId':'1'}
    r=client.post('/v1/chat',headers=h,json=body)
    assert r.status_code==200 and r.json()['reply']=='100원'
    assert c.get('/api/me').json()['remaining']==299
    assert client.post('/v1/chat',headers=h,json=body).json()==r.json()
    post(c,'/api/developer/keys/'+key['id']+'/revoke',{})
    assert client.post('/v1/chat',headers=h,json=body).status_code==401

def test_hwpx_and_url_import(monkeypatch):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('Contents/section0.xml','<section><p><t>교육 자료</t></p></section>')
    assert ai.extract('test.hwpx',b.getvalue())[0]=='교육 자료'
    monkeypatch.setattr(education_url,'fetch_text',lambda url:('웹페이지 교육 자료','example.com'))
    c=owner();r=post(c,'/api/files/url',{'url':'https://example.com'})
    assert post(c,'/api/files/url',{'url':'https://example.com'})['duplicate']
    assert c.get('/api/files').json()[0]['id']==r['id']

def test_public_url_ssrf_validation(monkeypatch):
    import pytest
    for url in ['http://example.com','https://127.0.0.1','https://example.com:8080','https://user:pass@example.com']:
        with pytest.raises(ValueError):education_url.validate_url(url)
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError):education_url.resolve_public('example.com')

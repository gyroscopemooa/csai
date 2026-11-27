import io,base64
from PIL import Image
from fastapi.testclient import TestClient
from test_app import owner,post,patch,app

def test_chat_profile_default_off_and_no_usage():
    c=owner()
    p=c.get('/api/chat-profile').json()
    assert not p['show_at_start'] and not p['links'] and not p['photo']
    before=c.get('/api/me').json()
    buf=io.BytesIO();Image.new('RGB',(600,400),'blue').save(buf,format='PNG')
    p=post(c,'/api/chat-profile',{'show_at_start':True,'title':'스튜디오','message':'촬영 안내','photo':base64.b64encode(buf.getvalue()).decode(),'links':[{'name':'홈페이지','url':'https://example.com/'},{'name':'예약','url':'https://example.com/reserve'}]})
    with Image.open(io.BytesIO(base64.b64decode(p['photo'].split(',')[1]))) as im:
        assert max(im.size)<=320 and im.format=='PNG'
    after=c.get('/api/me').json()
    assert after['remaining']==before['remaining'] and after['credits']==before['credits']
    assert c.post('/api/chat-profile',json={'links':[{'name':'잘못된 링크','url':'javascript:alert(1)'}]}).status_code==422
    assert c.post('/api/chat-profile',json={'links':[{'name':'잘못된 링크','url':'https://example.com@other.example/'}]}).status_code==422
    assert c.post('/api/chat-profile',json={'photo':'not-an-image'}).status_code==422
    assert c.get('/api/chat-profile').json()==p
    post(c,'/api/demo/billing',{'plan':'lite'})
    patch(c,{'enabled':True,'brand':'업체명 수정'})
    slug=c.get('/api/me').json()['slug']
    u=TestClient(app)
    assert u.get('/api/public/'+slug).json()['chat_profile']==p
    assert u.get('/api/chat-profile').status_code==401
    off=post(c,'/api/chat-profile',{'show_at_start':False,'photo':''})
    assert not off['show_at_start'] and not off['photo'] and len(off['links'])==2

def test_chat_profile_brand_isolation_and_persistence():
    c=owner();other=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent']})
    post(other,'/api/demo/billing',{'plan':'lite','addons':['extra_agent']})
    a=post(c,'/api/agents',{'create':True,'brand':'추가 브랜드','welcome':'안녕하세요','enabled':True})
    aid=a['id']
    post(c,'/api/chat-profile',{'title':'기본 업체','show_at_start':True})
    p=post(c,'/api/chat-profile',{'agent':aid,'title':'별도 브랜드 소개','message':'독립 설정','show_at_start':True})
    assert c.get('/api/chat-profile').json()['title']=='기본 업체'
    assert other.get('/api/chat-profile?agent='+aid).status_code==403
    assert other.post('/api/chat-profile',json={'agent':aid,'title':'변조'}).status_code==403
    post(c,'/api/agents',{'id':aid,'brand':'브랜드 이름 수정'})
    assert c.get('/api/chat-profile?agent='+aid).json()==p
    assert TestClient(app).get('/api/public/'+a['slug']).json()['chat_profile']==p

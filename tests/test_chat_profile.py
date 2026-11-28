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
        assert im.size==(600,400) and im.format=='WEBP'
    assert p['photo'].startswith('data:image/webp;base64,')
    after=c.get('/api/me').json()
    assert after['remaining']==before['remaining'] and after['credits']==before['credits']
    assert c.post('/api/chat-profile',json={'links':[{'name':'잘못된 링크','url':'javascript:alert(1)'}]}).status_code==422
    assert c.post('/api/chat-profile',json={'links':[{'name':'잘못된 링크','url':'https://example.com@other.example/'}]}).status_code==422
    assert c.post('/api/chat-profile',json={'photo':'not-an-image'}).status_code==422
    assert c.get('/api/chat-profile').json()==p
    post(c,'/api/demo/billing',{'plan':'lite'})
    patch(c,{'enabled':True,'brand':'업체명 수정','hours':'평일 09:00–18:00'})
    slug=c.get('/api/me').json()['slug']
    u=TestClient(app)
    public_profile=u.get('/api/public/'+slug).json()
    assert public_profile['chat_profile']==p
    assert public_profile['hours']=='평일 09:00–18:00'
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


def test_profile_contacts_and_notice_modes_are_independent():
    c=owner()
    data={'show_at_start':False,'notice_mode':'profile','manual_notice':'휴무 안내','contacts':[{'kind':'phone','name':'고객센터','value':'+82 52-123-4567'},{'kind':'email','name':'이메일 문의','value':'help@example.com'},{'kind':'other','name':'메신저 ID','value':'studio-support'}]}
    p=post(c,'/api/chat-profile',data)
    assert p['contacts']==data['contacts'] and not p['show_at_start']
    assert p['manual_notice']=='휴무 안내' and p['notice_mode']=='profile'
    assert c.get('/api/me').json()['settings']['notice']=='휴무 안내'
    for invalid in [{'kind':'phone','name':'전화','value':'123;456'},{'kind':'email','name':'메일','value':'help@example.com?subject=x'},{'kind':'other','name':'기타','value':'a\nb'}]:
        assert c.post('/api/chat-profile',json={'contacts':[invalid]}).status_code==422
    assert c.post('/api/chat-profile',json={'notice_mode':'invalid'}).status_code==422
    assert c.get('/api/chat-profile').json()==p
    post(c,'/api/demo/billing',{'plan':'lite'})
    patch(c,{'enabled':True})
    slug=c.get('/api/me').json()['slug']
    assert TestClient(app).get('/api/public/'+slug).json()['chat_profile']==p
    patch(c,{'notice':'새로운 공지'})
    q=c.get('/api/chat-profile').json()
    assert q['manual_notice']=='새로운 공지' and q['contacts']==data['contacts']
    for mode in ('manual','both','off'):
        q=post(c,'/api/chat-profile',{'notice_mode':mode})
        assert q['notice_mode']==mode and q['contacts']==data['contacts'] and not q['show_at_start']


def test_profile_cover_optimized_without_stretching():
    c=owner()
    buf=io.BytesIO();Image.new('RGB',(2400,1800),'green').save(buf,format='JPEG')
    p=post(c,'/api/chat-profile',{'photo':base64.b64encode(buf.getvalue()).decode()})
    raw=base64.b64decode(p['photo'].split(',')[1])
    assert len(raw)<=400000
    with Image.open(io.BytesIO(raw)) as im:
        assert im.size==(1200,900) and im.format=='WEBP'
    assert c.get('/api/chat-profile').json()==p

from test_app import owner,post,patch,public
from store import db

def test_multiple_business_choices_and_staff_mode():
    c=owner()
    patch(c,{'industries':['사진','IT','사진'],'desired_work':['상담','예약'],'consultation_mode':'staff'})
    settings=c.get('/api/me').json()['settings']
    assert settings['industries']==['사진','IT']
    assert settings['desired_work']==['상담','예약']
    assert c.get('/api/me').json()['addons']==[]
    post(c,'/api/demo/billing',{'plan':'lite','addons':[]})
    patch(c,{'enabled':True})
    u,token=public(c)
    before=c.get('/api/me').json()['remaining']
    r=post(u,'/api/chat',{'token':token,'message':'예약 가능한가요?','clientMessageId':'manual-1'})
    assert r['manual'] and c.get('/api/me').json()['remaining']==before
    thread=c.get('/api/inbox').json()[0]['id']
    post(c,'/api/inbox/'+thread,{'reply':'내일 가능합니다. 연락처 test@example.com','manual':True})
    result=c.get('/api/inbox/'+thread+'/education-source').json()
    assert result['pairs']==1 and '내일 가능합니다' in result['text']
    assert 'test@example.com' not in result['text']
    assert owner().get('/api/inbox/'+thread+'/education-source').status_code==404
    assert c.get('/api/me').json()['remaining']==before

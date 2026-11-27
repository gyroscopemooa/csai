from test_app import owner,post,patch,public
from store import db,one,uid,now,dump
import push_notifications as push

def test_device_preferences_scope_and_privacy(monkeypatch):
    c=owner();other=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['push','new_alert']})
    post(other,'/api/demo/billing',{'plan':'lite','addons':['push']})
    slug=c.get('/api/me').json()['slug'];sub=uid()
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        conn.execute('INSERT INTO push_subscription VALUES(?,?,?,?,?)',(sub,ws,'https://fcm.googleapis.com/fcm/send/'+sub,dump({}),now()-60))
        for kind in ('manual_message','handoff_urgent','unknown','new'):
            conn.execute('INSERT INTO event_log VALUES(?,?,?,?,?,0,?)',(uid(),ws,kind,'개인 정보 예시','private-ref',now()))
    path='/api/push/'+sub
    assert other.patch(path,json={'kinds':['new'],'silent':True}).status_code==404
    assert c.patch(path,json={'kinds':['invalid'],'silent':False}).status_code==422
    assert c.patch(path,json={'kinds':['manual_message','handoff_urgent','unknown'],'silent':True}).status_code==200
    sent=[]
    monkeypatch.setenv('ENABLE_AUTO_PUSH','1')
    monkeypatch.setattr(push,'send',lambda s,e,silent=False:sent.append(push.payload(e,silent)) or 'simulated')
    push.tick()
    assert [x['kind'] for x in sent]==['handoff_urgent','manual_message']
    assert all(x['silent'] and x['route']=='inbox' and '개인 정보' not in str(x) and 'private-ref' not in str(x) for x in sent)
    push.tick()
    assert len(sent)==2
    assert c.delete(path).status_code==200
    assert all(x['id']!=sub for x in c.get('/api/push').json()['devices'])

def test_manual_followup_notification_and_staff_education():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['new_alert']})
    patch(c,{'enabled':True,'price':'10000원'})
    u,t=public(c)
    post(u,'/api/chat',{'token':t,'message':'가격은?','clientMessageId':'a'})
    tid=c.get('/api/inbox').json()[0]['id']
    post(c,'/api/inbox/'+tid,{'manual':True,'reply':'정정 가격 20000원'})
    post(c,'/api/inbox/'+tid,{'manual':True,'reply':'배송비 별도입니다'})
    src=c.get('/api/inbox/'+tid+'/education-source').json()
    assert src['pairs']==1 and '정정 가격 20000원' in src['text'] and '배송비 별도입니다' in src['text']
    for client in ('b','c'):
        post(u,'/api/chat',{'token':t,'message':'추가 문의','clientMessageId':client})
    assert sum(x['kind']=='manual_message' and x['ref']==tid for x in c.get('/api/events').json())==1

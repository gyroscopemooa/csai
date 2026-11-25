from test_app import owner,post,patch,public
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
import base64
import store
import push_notifications

def b64(b):return base64.urlsafe_b64encode(b).decode().rstrip('=')

def sample():
    pub=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(Encoding.X962,PublicFormat.UncompressedPoint)
    return {'endpoint':'https://fcm.googleapis.com/fcm/send/csai-test-'+store.uid(),'keys':{'p256dh':b64(pub),'auth':b64(b'0123456789abcdef')}}

def test_push_registration_and_purchase(monkeypatch):
    monkeypatch.setattr(push_notifications,'configured',lambda:True)
    c=owner();other=owner()
    assert c.get('/api/push').status_code==403
    post(c,'/api/demo/billing',{'plan':'lite','addons':['push','new_alert']})
    post(other,'/api/demo/billing',{'plan':'lite','addons':['push']})
    s=sample()
    assert c.post('/api/push',json=dict(s,endpoint='https://127.0.0.1/test')).status_code==422
    x=post(c,'/api/push',s)
    assert post(c,'/api/push',s)['id']==x['id']
    assert other.post('/api/push',json=s).status_code==409
    assert other.delete('/api/push/'+x['id']).status_code==200
    assert len(c.get('/api/push').json()['devices'])==1
    assert c.delete('/api/push/'+x['id']).status_code==200
    assert c.get('/api/push').json()['devices']==[]

def test_push_dispatch_entitlement_and_duplicate(monkeypatch):
    monkeypatch.setattr(push_notifications,'configured',lambda:True)
    monkeypatch.setattr(push_notifications,'live_enabled',lambda:False)
    monkeypatch.setenv('ENABLE_AUTO_PUSH','1')
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['push','new_alert']})
    patch(c,{'enabled':True,'price':'100원'})
    post(c,'/api/push',sample())
    u,t=public(c)
    post(u,'/api/chat',{'token':t,'message':'가격은?','clientMessageId':'push-test'})
    assert push_notifications.tick()>=1
    assert len(c.get('/api/push').json()['deliveries'])==1
    push_notifications.tick()
    assert len(c.get('/api/push').json()['deliveries'])==1

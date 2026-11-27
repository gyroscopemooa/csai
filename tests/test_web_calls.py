from test_app import owner,post,patch,public
import os

def test_call_signaling_scope_and_expiry(monkeypatch):
    monkeypatch.setenv('ENABLE_WEB_CALLS','1')
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True})
    post(c,'/api/web-calls/settings',{'enabled':True})
    u,t=public(c);v,other=public(c)
    offer='v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n'
    r=post(u,'/api/customer/web-calls',{'action':'start','token':t,'kind':'audio','confirmed':True,'offer':offer})
    i=r['id'];tid=next(x['id'] for x in c.get('/api/inbox').json() if x['manual'])
    assert v.post('/api/customer/web-calls',json={'action':'status','token':other,'id':i}).status_code==404
    path='/api/inbox/'+tid+'/web-call'
    assert post(c,path,{'action':'list'})['call']['state']=='ringing'
    key='test-claim-key-1234567890'
    assert owner().post(path,json={'action':'claim','id':i,'key':key,'confirmed':True}).status_code==404
    assert post(c,path,{'action':'claim','id':i,'key':key,'confirmed':True})['offer']==offer
    assert c.post(path,json={'action':'claim','id':i,'key':'different-claim-key-1234','confirmed':True}).status_code==409
    assert post(c,path,{'action':'answer','id':i,'key':key,'answer':offer})['state']=='answered'
    assert post(u,'/api/customer/web-calls',{'action':'status','token':t,'id':i})['answer']==offer
    assert post(u,'/api/customer/web-calls',{'action':'end','token':t,'id':i})['state']=='ended'
    assert post(c,path,{'action':'list'})['call'] is None

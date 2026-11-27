from test_app import owner,post,patch,public
import base64

def test_file_opt_in_scope_and_type():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True})
    u,t=public(c);v,other=public(c)
    body={'token':t,'client':'file-client-123','kind':'file','name':'notes.txt','data':base64.b64encode('test document'.encode()).decode()}
    assert u.post('/api/customer/photos',json=body).status_code==403
    post(c,'/api/chat-photos/settings',{'enabled':False,'files_enabled':True})
    p=post(u,'/api/customer/photos',body);assert post(u,'/api/customer/photos',body)['duplicate']
    assert u.get('/api/session/'+t+'/messages').json()[0]['attachment']['name']=='notes.txt'
    assert post(u,'/api/customer/photos/read',{'token':t,'id':p['id']})['mime']=='text/plain'
    assert v.post('/api/customer/photos/read',json={'token':other,'id':p['id']}).status_code==404
    assert u.post('/api/customer/photos',json=body|{'client':'bad-file-123','name':'bad.exe'}).status_code==422
    assert u.post('/api/customer/photos',json=body|{'client':'bad-file-456','name':'bad.mp4'}).status_code==422
    assert v.post('/api/customer/photos',json=body|{'token':other,'client':'bad-file-789','name':'../notes.txt'}).status_code==422
    assert u.post('/api/customer/photos',json=body).status_code==429

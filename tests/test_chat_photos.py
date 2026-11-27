from test_app import owner,post,patch,public
from PIL import Image
import io,base64

def photo():
    b=io.BytesIO();Image.new('RGB',(32,32),'red').save(b,format='PNG')
    return base64.b64encode(b.getvalue()).decode()

def test_customer_photo_private_and_manual():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True})
    post(c,'/api/chat-photos/settings',{'enabled':True})
    u,t=public(c);v,other=public(c)
    body={'token':t,'client':'photo-client-1','data':photo()}
    p=post(u,'/api/customer/photos',body);assert post(u,'/api/customer/photos',body)['duplicate']
    assert len(u.get('/api/session/'+t+'/messages').json())==1
    thread=next(x for x in c.get('/api/inbox').json() if x['manual'])
    tid=thread['id'];assert thread['status']=='pending'
    assert post(u,'/api/customer/photos/read',{'token':t,'id':p['id']})['mime']=='image/jpeg'
    assert v.post('/api/customer/photos/read',json={'token':other,'id':p['id']}).status_code==404
    assert c.get('/api/inbox/'+tid+'/photos/'+p['id']).status_code==200
    assert owner().get('/api/inbox/'+tid+'/photos/'+p['id']).status_code==404
    assert u.post('/api/customer/photos',json=body|{'client':'photo-invalid-2','data':'not image'}).status_code==422

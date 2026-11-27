from test_app import owner,post,patch,public
from fastapi.testclient import TestClient
from app import app,session_response
from store import db,one

def google_client(sub,email):
    c=TestClient(app)
    r=session_response('google:'+sub,email)
    cookie=r.headers['set-cookie'].split(';',1)[0].split('=',1)[1]
    c.cookies.set('csai_session',cookie)
    return c

def test_staff_invite_scoped_access_and_revoke():
    import uuid
    suffix=uuid.uuid4().hex
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True})
    email=suffix+'@example.com'
    invite=post(c,'/api/team/invite',{'email':email,'name':'직원','role':'agent','assigned_only':True})
    other=google_client('other-'+suffix,'other-'+email)
    assert other.post('/api/staff/accept',json={'code':invite['code']}).status_code==403
    staff=google_client(suffix,email)
    mid=post(staff,'/api/staff/accept',{'code':invite['code']})['id']
    assert staff.post('/api/staff/accept',json={'code':invite['code']}).status_code==403
    u,token=public(c);post(u,'/api/chat',{'token':token,'message':'문의','clientMessageId':'staff-test'})
    tid=c.get('/api/inbox').json()[0]['id']
    base='/api/staff/'+mid+'/threads'
    assert staff.get(base).json()==[]
    assert staff.get(base+'/'+tid).status_code==404
    post(c,'/api/team/threads/'+tid,{'member':mid})
    assert [x['id'] for x in staff.get(base).json()]==[tid]
    assert other.get(base).status_code==403
    body={'action':'reply','reply':'직접 답변','client':'staff-reply-test'}
    assert post(staff,base+'/'+tid,body)['duplicate'] is False
    assert post(staff,base+'/'+tid,body)['duplicate'] is True
    assert len([x for x in staff.get(base+'/'+tid).json()['messages'] if x['role']=='staff'])==1
    assert staff.get('/api/inbox/'+tid).status_code==404
    post(c,'/api/team/'+mid+'/permissions',{'role':'viewer','agent':'','assigned_only':True})
    assert staff.post(base+'/'+tid,json={'action':'resolve','client':'staff-resolve-test'}).status_code==403
    post(c,'/api/team/'+mid+'/revoke',{})
    assert staff.get(base).status_code==403

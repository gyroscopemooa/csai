from test_app import owner,post,patch
from store import db,one,uid,now
import channel_live

def test_staff_outbound_success_and_idempotency(monkeypatch):
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':['naver']})
    patch(c,{'enabled':True})
    slug=c.get('/api/me').json()['slug']
    monkeypatch.setattr(channel_live,'staff_enabled',lambda:True)
    monkeypatch.setattr(channel_live,'lock_text',lambda v:v)
    monkeypatch.setattr(channel_live,'unlock',lambda v:v)
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        token,tid=uid(),uid()
        conn.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'))
        conn.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(tid,ws,token,'naver',now()))
        conn.execute('INSERT INTO channel_link VALUES(?,?,?,?,?,?,?)',(ws,'naver',uid(),'secret','credential','partner',1))
        link=one(conn,"SELECT secret_hash FROM channel_link WHERE ws=? AND channel='naver'",(ws,))
        conn.execute('INSERT INTO channel_destination VALUES(?,?,?,?,?,?,?)',(ws,tid,'naver',link['secret_hash'],'partner','customer',now()))
        conn.execute('INSERT INTO channel_session VALUES(?,?,?,?)',(ws,'naver',channel_live.digest('customer'),token))
    sent=[]
    class Resp:
        is_success=True
        def json(self):return {'success':True,'resultCode':'00'}
    def send(*args,**kwargs):
        sent.append(kwargs['json'])
        return Resp()
    monkeypatch.setattr(channel_live.httpx,'post',send)
    other=owner()
    body={'reply':'직접 답변','client':'test1','confirmed':True}
    path='/api/inbox/'+tid+'/channel-reply'
    assert other.post(path,json=body).status_code==404
    r=post(c,path,body);assert r['status']=='queued'
    assert post(c,path,body)['id']==r['id']
    assert channel_live.process_staff_one(ws)
    assert not channel_live.process_staff_one(ws)
    assert len(sent)==1 and sent[0]['user']=='customer'
    detail=c.get('/api/inbox/'+tid).json()
    assert detail['manual'] and detail['messages'][-1]['role']=='staff'
    assert detail['channel_reply']['jobs'][0]['status']=='sent'
    assert post(c,path,body)['status']=='sent'
    monkeypatch.setattr(channel_live.httpx,'post',lambda *a,**k:(_ for _ in ()).throw(TimeoutError()))
    post(c,path,body|{'client':'test2'})
    assert channel_live.process_staff_one(ws)
    jobs=c.get('/api/inbox/'+tid).json()['channel_reply']['jobs']
    assert {x['status'] for x in jobs}=={'unknown','sent'}
    assert not channel_live.process_staff_one(ws)
    assert len(c.get('/api/inbox/'+tid).json()['messages'])==1

def test_naver_success_requires_documented_result():
    class Resp:
        is_success=True
        def json(self):return {'success':True}
    assert not channel_live.naver_success(Resp())

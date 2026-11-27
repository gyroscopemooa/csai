from test_app import owner,post
from store import db,one,uid,now

def test_inbox_read_annotations_snippets():
    c=owner();other=owner()
    slug=c.get('/api/me').json()['slug']
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        tid,token,m1,m2=uid(),uid(),uid(),uid()
        conn.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'))
        conn.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(tid,ws,token,'public',now()))
        for m in (m1,m2):conn.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(m,ws,tid,'user','question',now()))
    def unread():return next(x for x in c.get('/api/inbox').json() if x['id']==tid)['unread']
    assert unread()==2
    assert other.post('/api/inbox/'+tid+'/read',json={'message':m2}).status_code==404
    post(c,'/api/inbox/'+tid+'/read',{'message':m1});assert unread()==1
    post(c,'/api/inbox/'+tid+'/read',{'message':m2});assert unread()==0
    post(c,'/api/inbox/'+tid+'/read',{'message':m1});assert unread()==0
    post(c,'/api/inbox/'+tid+'/annotation',{'note':'internal','tags':['VIP','VIP']})
    assert c.get('/api/inbox/'+tid+'/annotation').json()=={'note':'internal','tags':['VIP']}
    assert other.get('/api/inbox/'+tid+'/annotation').status_code==404
    i=post(c,'/api/inbox-snippets',{'title':'hello','body':'welcome'})['id']
    assert not any(x['id']==i for x in other.get('/api/inbox-snippets').json())
    assert other.delete('/api/inbox-snippets/'+i).status_code==404
    assert c.delete('/api/inbox-snippets/'+i).status_code==200

from test_app import owner,post
from store import db,one,uid,now

def test_related_and_metrics_and_resume():
    c=owner();other=owner()
    slug=c.get('/api/me').json()['slug']
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        a,b,z=uid(),uid(),uid()
        for i,connection in ((a,'link1'),(b,'link1'),(z,'link2')):
            token=uid()
            conn.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'))
            conn.execute('INSERT INTO thread(id,ws,visitor,kind,created,manual) VALUES(?,?,?,?,?,?)',(i,ws,token,'naver',now(),1))
            conn.execute('INSERT INTO channel_customer_thread VALUES(?,?,?,?,?)',(ws,i,'naver',connection,'same-user'))
            conn.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,i,'user','question',now()))
    assert {x['id'] for x in c.get('/api/inbox/'+a+'/related').json()['threads']}=={b}
    assert other.get('/api/inbox/'+a+'/related').status_code==404
    assert next(x for x in c.get('/api/inbox-channel-metrics').json()['channels'] if x['channel']=='naver')['inbound']==3
    post(c,'/api/inbox/'+a,{'status':'resolved','resume_on_close':True})
    detail=c.get('/api/inbox/'+a).json()
    assert detail['status']=='resolved' and not detail['manual']

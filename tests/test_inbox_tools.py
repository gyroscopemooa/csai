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

def test_delivery_issue_scope():
    c=owner();other=owner()
    slug=c.get('/api/me').json()['slug']
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        i=uid();conn.execute('INSERT INTO channel_job VALUES(?,?,?,?,?,?,?,?,?)',(i,ws,'naver',uid(),'','failed','provider failure',now(),now()))
    assert any(x['id']==i for x in c.get('/api/channel-delivery-issues').json())
    assert not any(x['id']==i for x in other.get('/api/channel-delivery-issues').json())


def test_brief_uses_visible_records_and_is_tenant_scoped():
    c=owner();other=owner()
    slug=c.get('/api/me').json()['slug']
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        tid,token=uid(),uid()
        conn.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'))
        conn.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(tid,ws,token,'public',now()))
        for role,body in [('user','old secret'),('user','배송 문의'),('assistant','안내 내용'),('staff','확인 중'),('user','추가 질문')]:
            created=now()-365*86400 if body=='old secret' else now()
            conn.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,tid,role,body,created))
    post(c,'/api/inbox/'+tid+'/annotation',{'note':'담당자 확인','tags':['배송']})
    before=c.get('/api/me').json()['remaining']
    path='/api/inbox/'+tid+'/brief'
    assert other.get(path).status_code==404
    result=c.get(path).json()
    assert result['mode']=='extractive' and result['latest_is_customer']
    assert result['note']=='담당자 확인' and result['tags']==['배송']
    assert [m['body'] for m in result['recent']]==['배송 문의','안내 내용','확인 중','추가 질문']
    assert c.get('/api/me').json()['remaining']==before


def test_inbox_assignment_is_internal_and_workspace_scoped():
    c=owner();other=owner()
    slug=c.get('/api/me').json()['slug']
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        tid,token=uid(),uid()
        conn.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,ws,now()+86400,'public'))
        conn.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(tid,ws,token,'public',now()))
    path='/api/inbox/'+tid+'/assignment'
    data={'assignee':'담당자 A','priority':'urgent','due_date':'2026-12-01'}
    assert other.get(path).status_code==404
    assert other.post(path,json=data).status_code==404
    assert c.post(path,json=data|{'due_date':'2026-02-30'}).status_code==422
    assert post(c,path,data)['ok']
    assert c.get(path).json()['assignee']=='담당자 A'
    assert next(x for x in c.get('/api/inbox').json() if x['id']==tid)['assignment']==data

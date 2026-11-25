"""Scoped server-to-server API for purchased capabilities. No live provider setup required."""
import hashlib
from fastapi import Depends, Request
from app import app, ident, require, bounded, limit, chat, manual_booking, bookings, work_list, work_add, estimate, train, publish, stats
from store import *

SCOPES={"chat":None,"bookings:read":"calendar","bookings:write":"calendar","bookings:change":"change_booking","work:read":None,"work:write":None,"education":None,"stats":"stats","crm:read":"crm","crm:write":"crm","leads:read":"leads","leads:write":"leads","quotes:read":"quote","quotes:write":"quote","quotes:send":"quote","reports:read":"report","export":"export","custom:jobs":"custom_integration"}

def init_api():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS developer_key(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),label TEXT NOT NULL,digest TEXT UNIQUE NOT NULL,scopes TEXT NOT NULL,created INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,last_used INTEGER);
        CREATE TABLE IF NOT EXISTS developer_session(id TEXT PRIMARY KEY,key_id TEXT NOT NULL REFERENCES developer_key(id),ws TEXT NOT NULL REFERENCES workspace(id),visitor TEXT NOT NULL,expires INTEGER NOT NULL);
        """)
init_api()

def access(c,ws):
    w=getw(c,ws)
    require(w and 'external_api' in entitlements(w),'외부 API 이용권 구매 필요',403)
    return w

def allowed(w,scope):
    a=entitlements(w)
    if scope.startswith('work:'):return bool(a & {'crm','quote','tasks','leads','complaints'})
    return scope in SCOPES and (SCOPES[scope] is None or SCOPES[scope] in a)

def authorize(req,scope):
    h=req.headers.get('authorization','')
    require(h.startswith('Bearer ') and 16<len(h)<256,'API 키 필요',401)
    digest=hashlib.sha256(h[7:].encode()).hexdigest()
    with db(True) as c:
        k=one(c,'SELECT * FROM developer_key WHERE digest=? AND revoked=0',(digest,))
        require(k,'유효하지 않은 API 키',401)
        w=access(c,k['ws'])
        require(scope in loads(k['scopes']) and allowed(w,scope),'API 범위 또는 구매 권한 부족',403)
        limit('developer:'+k['id'],60)
        c.execute('UPDATE developer_key SET last_used=? WHERE id=?',(now(),k['id']))
        return k

@app.get('/api/developer/keys')
def keys(ws=Depends(ident)):
    with db() as c:
        w=access(c,ws)
        return {'scopes':[x for x in SCOPES if allowed(w,x)],'keys':[dict(r,scopes=loads(r['scopes'])) for r in rows(c,'SELECT id,label,scopes,created,revoked,last_used FROM developer_key WHERE ws=? ORDER BY created DESC',(ws,))]}

@app.post('/api/developer/keys')
def key_create(body:dict,ws=Depends(ident)):
    name=bounded(body.get('label',''),100);scopes=body.get('scopes',[])
    require(name and isinstance(scopes,list) and scopes and len(scopes)<=len(SCOPES) and all(isinstance(s,str) and s in SCOPES for s in scopes),'키 이름과 유효한 권한 필요',422)
    with db(True) as c:
        w=access(c,ws);require(all(allowed(w,s) for s in scopes),'구매하지 않은 기능의 API 권한',403)
        require(one(c,'SELECT count(*) n FROM developer_key WHERE ws=? AND revoked=0',(ws,))['n']<10,'활성 API 키는 최대 10개',409)
        token='csai_'+secrets.token_urlsafe(32);i=uid();c.execute('INSERT INTO developer_key(id,ws,label,digest,scopes,created) VALUES(?,?,?,?,?,?)',(i,ws,name,hashlib.sha256(token.encode()).hexdigest(),dump(sorted(set(scopes))),now()))
    return {'id':i,'key':token,'scopes':sorted(set(scopes)),'notice':'키는 지금 한 번만 표시됩니다.'}

@app.post('/api/developer/keys/{i}/revoke')
def key_revoke(i:str,ws=Depends(ident)):
    with db(True) as c:
        require(one(c,'SELECT id FROM developer_key WHERE id=? AND ws=?',(i,ws)),'키 없음',404)
        c.execute('UPDATE developer_key SET revoked=1 WHERE id=? AND ws=?',(i,ws))
    return {'ok':True}

@app.post('/v1/chat/sessions')
def api_session(req:Request):
    k=authorize(req,'chat')
    with db(True) as c:
        w=access(c,k['ws']);require(public_access(w) and w['enabled'],'공개 상담을 먼저 활성화하세요.',409)
        token=uid();thread=uid();i=uid();expires=now()+86400
        c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(token,w['id'],expires,'public'))
        c.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(thread,w['id'],token,'public',now()))
        c.execute('INSERT INTO developer_session VALUES(?,?,?,?,?)',(i,k['id'],w['id'],token,expires))
    return {'session':i,'expires':expires}

@app.post('/v1/chat')
def api_chat(body:dict,req:Request):
    k=authorize(req,'chat');i=bounded(body.get('session',''),100)
    with db() as c:
        s=one(c,'SELECT * FROM developer_session WHERE id=? AND ws=? AND key_id=? AND expires>?',(i,k['ws'],k['id'],now()))
        require(s,'API 상담 세션 없음 또는 만료',404)
    return chat({'token':s['visitor'],'message':body.get('message',''),'clientMessageId':body.get('clientMessageId','')})

@app.get('/v1/bookings')
def api_bookings(req:Request):return bookings(ws=authorize(req,'bookings:read')['ws'])
@app.post('/v1/bookings')
def api_create_booking(body:dict,req:Request):return manual_booking(body,ws=authorize(req,'bookings:write')['ws'])
@app.get('/v1/work')
def api_work(req:Request):return work_list(ws=authorize(req,'work:read')['ws'])
@app.post('/v1/work')
def api_create_work(body:dict,req:Request):return work_add(body,ws=authorize(req,'work:write')['ws'])
@app.post('/v1/education/estimate')
def api_education_estimate(body:dict,req:Request):return estimate(body,ws=authorize(req,'education')['ws'])
@app.post('/v1/education/{i}/run')
def api_education_run(i:str,req:Request):return train(i,ws=authorize(req,'education')['ws'])
@app.post('/v1/education/{i}/publish')
def api_education_publish(i:str,body:dict,req:Request):return publish(i,body,ws=authorize(req,'education')['ws'])
@app.get('/v1/stats')
def api_stats(req:Request):return stats(ws=authorize(req,'stats')['ws'])


# Import lazily: these feature modules register their routes after this module.
@app.get('/v1/crm/contacts')
def api_contacts(req:Request):
    import customer_ops
    return customer_ops.contacts(ws=authorize(req,'crm:read')['ws'])

@app.post('/v1/crm/contacts')
def api_contact_create(body:dict,req:Request):
    import customer_ops
    return customer_ops.contact_create(body,ws=authorize(req,'crm:write')['ws'])

@app.patch('/v1/crm/contacts/{i}')
def api_contact_edit(i:str,body:dict,req:Request):
    import customer_ops
    return customer_ops.contact_edit(i,body,ws=authorize(req,'crm:write')['ws'])

@app.get('/v1/leads')
def api_leads(req:Request):
    import customer_ops
    return customer_ops.leads(ws=authorize(req,'leads:read')['ws'])

@app.patch('/v1/leads/{thread}')
def api_lead_edit(thread:str,body:dict,req:Request):
    import customer_ops
    return customer_ops.lead_edit(thread,body,ws=authorize(req,'leads:write')['ws'])

@app.get('/v1/quotes/items')
def api_quote_items(req:Request):
    import customer_ops
    return customer_ops.quote_items(ws=authorize(req,'quotes:read')['ws'])

@app.get('/v1/quotes/offers')
def api_quote_offers(req:Request):
    import customer_ops
    return customer_ops.offers(ws=authorize(req,'quotes:read')['ws'])

@app.post('/v1/quotes/offers')
def api_quote_create(body:dict,req:Request):
    import customer_ops
    return customer_ops.quote_create(body,ws=authorize(req,'quotes:write')['ws'])

@app.post('/v1/quotes/offers/{i}/send')
def api_quote_send(i:str,body:dict,req:Request):
    import customer_ops
    return customer_ops.quote_send(i,body,ws=authorize(req,'quotes:send')['ws'])

@app.patch('/v1/work/{i}')
def api_edit_work(i:str,body:dict,req:Request):
    import ops
    return ops.edit_work(i,body,ws=authorize(req,'work:write')['ws'])

@app.get('/v1/bookings/changes')
def api_booking_changes(req:Request):
    import ops
    return ops.changes(ws=authorize(req,'bookings:change')['ws'])

@app.post('/v1/bookings/changes/{i}')
def api_booking_change(i:str,body:dict,req:Request):
    import ops
    return ops.decide(i,body,ws=authorize(req,'bookings:change')['ws'])

@app.get('/v1/analytics')
def api_analytics(req:Request,days:int=30):
    import reporting
    return reporting.analytics(days=days,ws=authorize(req,'stats')['ws'])

@app.get('/v1/reports')
def api_reports(req:Request):
    import reporting
    return reporting.reports(ws=authorize(req,'reports:read')['ws'])

@app.get('/v1/export')
def api_export(req:Request):
    from app import export
    return export(ws=authorize(req,'export')['ws'])

"""Owner-verified, short-lived web customer order lookup. No automatic identity inference."""
import hashlib,hmac,re,secrets
from fastapi import Depends
from app import app,ident,require,bounded,visitor,limit
from store import *
import commerce,ops,smartstore_sync as sync
from google_calendar import encryption
from integrations import smartstore_transport as ss

TTL=900
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS order_access(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,reference TEXT NOT NULL,connection TEXT NOT NULL,code_hash TEXT NOT NULL,state TEXT NOT NULL,expires INTEGER NOT NULL,attempts INTEGER NOT NULL,created INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS order_access_scope ON order_access(ws,agent,thread,state);
        """)
init()

def connection(c,ws,agent):
    r=one(c,'SELECT client_id,credential FROM smartstore_connection WHERE ws=? AND agent=? AND active=1',(ws,agent))
    require(sync.configured() and r,'주문 조회 연결 비활성화',409)
    return r
def fingerprint(r):return hashlib.sha256(dump([r['client_id'],r['credential']]).encode()).hexdigest()
def code_hash(s):return hashlib.sha256(s.encode()).hexdigest()

def customer_scope(c,token):
    v=visitor(c,token,kind='public');w=getw(c,v['ws']);a=ops.public_work_scope(c,w,v)
    require(commerce.enabled(c,w['id'],a),'판매 관리 비활성화',403)
    t=one(c,"SELECT id FROM thread WHERE ws=? AND visitor=? AND kind='public'",(w['id'],token))
    require(t and ops.thread_brand(c,w,t['id'],True)==a,'상담 없음',404)
    return w,a,t['id']

def owner_scope(c,ws,tid):
    w=getw(c,ws);a=ops.thread_brand(c,w,tid,True);commerce.access(c,ws,a,True)
    require(one(c,"SELECT id FROM thread WHERE ws=? AND id=? AND kind='public'",(ws,tid)),'자체 웹 상담만 지원합니다.',409)
    return a

@app.get('/api/inbox/{tid}/order-access')
def status(tid:str,ws=Depends(ident)):
    with db() as c:
        a=owner_scope(c,ws,tid)
        return {'grants':rows(c,'SELECT id,reference,state,expires,created FROM order_access WHERE ws=? AND agent=? AND thread=? ORDER BY created DESC LIMIT 20',(ws,a,tid)),'available':sync.configured()}

@app.post('/api/inbox/{tid}/order-access')
def issue(tid:str,body:dict,ws=Depends(ident)):
    ref=bounded(body.get('reference',''),32)
    require(re.fullmatch(r'[0-9]{1,32}',ref) and body.get('verified_outside_chat') is True and body.get('confirmed') is True,'구매자 신원과 주문 소유권을 별도 신뢰 채널에서 확인해야 합니다.',422)
    limit('order-grant:'+ws,10,60)
    with db(True) as c:
        a=owner_scope(c,ws,tid);conn=connection(c,ws,a)
        c.execute("UPDATE order_access SET state='revoked',code_hash='' WHERE ws=? AND agent=? AND thread=? AND state IN ('issued','checking')",(ws,a,tid))
        code=secrets.token_urlsafe(18);i=uid();t=now()
        c.execute('INSERT INTO order_access VALUES(?,?,?,?,?,?,?,?,?,?,?)',(i,ws,a,tid,ref,fingerprint(conn),code_hash(code),'issued',t+TTL,0,t))
        return {'id':i,'code':code,'expires':t+TTL}

@app.post('/api/inbox/{tid}/order-access/revoke')
def revoke(tid:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        a=owner_scope(c,ws,tid)
        c.execute("UPDATE order_access SET state='revoked',code_hash='' WHERE ws=? AND agent=? AND thread=? AND state IN ('issued','checking')",(ws,a,tid))
    return {'ok':True}

@app.post('/api/customer/order-access')
def redeem(body:dict):
    token=bounded(body.get('token',''),100);code=bounded(body.get('code',''),100)
    require(re.fullmatch(r'[A-Za-z0-9_-]{24}',code),'인증 코드 형식 오류',422)
    limit('order-redeem:'+token,5,60)
    invalid=False
    with db(True) as c:
        w,a,tid=customer_scope(c,token);ws=w['id'];conn=connection(c,ws,a)
        row=one(c,"SELECT * FROM order_access WHERE ws=? AND agent=? AND thread=? AND state='issued' AND expires>? ORDER BY created DESC LIMIT 1",(ws,a,tid,now()))
        require(row and row['connection']==fingerprint(conn),'유효한 조회 승인 없음',403)
        if not hmac.compare_digest(row['code_hash'],code_hash(code)):
            n=row['attempts']+1
            c.execute("UPDATE order_access SET attempts=?,state=?,code_hash=? WHERE id=?",(n,'revoked' if n>=5 else 'issued','' if n>=5 else row['code_hash'],row['id']))
            invalid=True
        else:c.execute("UPDATE order_access SET state='checking',code_hash='' WHERE id=?",(row['id'],))
    require(not invalid,'인증 코드가 일치하지 않습니다.',403)
    try:
        provider_token=ss.access_token(conn['client_id'],encryption().decrypt(conn['credential'].encode()).decode())
        result=ss.order_status(provider_token,row['reference'])
    except Exception:
        with db(True) as c:c.execute("UPDATE order_access SET state='failed' WHERE id=? AND state='checking'",(row['id'],))
        require(False,'주문 조회 실패 · 담당자에게 새 인증 코드를 요청하세요.',502)
    with db(True) as c:
        w,agent,thread=customer_scope(c,token)
        current=one(c,'SELECT state,expires,connection FROM order_access WHERE ws=? AND agent=? AND thread=? AND id=?',(ws,a,tid,row['id']))
        require(w['id']==ws and agent==a and thread==tid and current and current['state']=='checking' and current['expires']>now() and current['connection']==fingerprint(connection(c,ws,a)),'조회 승인 만료 또는 취소',403)
        c.execute("UPDATE order_access SET state='used' WHERE id=?",(row['id'],))
    # No order details in chat history or LLM context. Single-use lookup only.
    return {k:result[k] for k in ('reference','product','status','delivery_status','carrier','tracking','queried_at')}

def clear(c,ws,agent):
    c.execute("UPDATE order_access SET state='revoked',code_hash='' WHERE ws=? AND agent=? AND state IN ('issued','checking')",(ws,agent))

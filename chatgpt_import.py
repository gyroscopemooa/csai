"""ChatGPT migration: separate one-time sandbox entitlement, server quote, paid analysis."""
import hashlib
import ai
from fastapi import Depends
from app import app, ident, require, fail, limit, record_usage
from store import *

def init_import():
    with db(True) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS chatgpt_import_quote(
            id TEXT PRIMARY KEY, ws TEXT NOT NULL, order_id TEXT NOT NULL,
            digest TEXT NOT NULL, max_credits INTEGER NOT NULL, state TEXT NOT NULL,
            created INTEGER NOT NULL, job_id TEXT, cost INTEGER)""")
        c.execute("CREATE INDEX IF NOT EXISTS chatgpt_import_ws ON chatgpt_import_quote(ws,order_id,state)")
init_import()

def paid_order(c,ws):
    # Sandbox orders never grant production access. Real verified PG fulfillment is a separate integration.
    if not DEMO or SHARED_TEST:
        return None
    return one(c,"SELECT * FROM checkout_order WHERE ws=? AND kind='chatgpt_import' AND status='paid' ORDER BY paid_at DESC LIMIT 1",(ws,))

def credits(c,w):
    t=trial(c,w)
    return max(0,10000-operator_wallet(c,w)['credit_used'] if is_operator(w) else t['credit_limit']-t['credit_used'] if t else w['credits'])

def prepared(body):
    raw=body.get('text')
    require(isinstance(raw,str) and 0<len(raw)<=60000,'한 회차에 60,000자 이하의 업무 대화만 선택하세요.',422)
    text=ai.clean(raw.strip())
    require(bool(text),'이전할 내용이 없습니다.',422)
    return text,hashlib.sha256(text.encode('utf-8')).hexdigest()

@app.get('/api/chatgpt-import/status')
def import_status(ws=Depends(ident)):
    with db(True) as c:
        o=paid_order(c,ws)
        return {'available':DEMO and not SHARED_TEST,'owned':bool(o),'price':CAT['chatgpt_import']['price'],
                'sandbox':True,'credits':credits(c,getw(c,ws)),
                'used':bool(o and one(c,"SELECT id FROM chatgpt_import_quote WHERE ws=? AND order_id=? AND state IN ('running','complete')",(ws,o['id'])))}

@app.post('/api/chatgpt-import/quote')
def import_quote(body:dict,ws=Depends(ident)):
    limit('chatgpt-import-quote:'+ws,12)
    require(body.get('consent') is True,'선택한 업무 대화 전송에 동의해 주세요.',422)
    with db(True) as c:
        o=paid_order(c,ws);require(o,'이전 이용권 구매 필요',403)
        text,digest=prepared(body);n=ai.estimate(text,[]);i=uid()
        c.execute("DELETE FROM chatgpt_import_quote WHERE ws=? AND state='quoted' AND created<?",(ws,now()-1800))
        c.execute("INSERT INTO chatgpt_import_quote VALUES(?,?,?,?,?,'quoted',?,NULL,NULL)",(i,ws,o['id'],digest,n,now()))
        return {'id':i,'maxCredits':n,'credits':credits(c,getw(c,ws)),'chars':len(text),'expires':now()+1800}

@app.post('/api/chatgpt-import/{i}/analyze')
def import_analyze(i:str,body:dict,ws=Depends(ident)):
    require(body.get('consent') is True,'정밀 분석 및 크레딧 차감 동의 필요',422)
    with db(True) as c:
        o=paid_order(c,ws);require(o,'이전 이용권 구매 필요',403)
        q=one(c,"SELECT * FROM chatgpt_import_quote WHERE id=? AND ws=? AND order_id=?",(i,ws,o['id']))
        require(q,'견적 없음',404)
        if q['state']=='complete':
            return {'id':q['job_id'],'cost':q['cost'],'duplicate':True}
        require(q['state']=='quoted' and q['created']>now()-1800,'견적 만료 또는 이미 처리 중',409)
        text,digest=prepared(body)
        require(digest==q['digest'] and body.get('maxCredits')==q['max_credits'],'자료 또는 견적이 변경되었습니다. 다시 확인하세요.',409)
        require(not one(c,"SELECT id FROM chatgpt_import_quote WHERE ws=? AND state='running'",(ws,)),'이전 분석 처리 중',409)
        w=getw(c,ws);n=q['max_credits'];j=uid();settings=loads(w['settings'])
        try:charge_credit(c,w,n,i)
        except ValueError as ex:fail(402,str(ex))
        c.execute("UPDATE chatgpt_import_quote SET state='running',job_id=? WHERE id=?",(j,i))
    try:
        # Original text is not saved to the database; existing engine treats source as untrusted.
        result,used=ai.train(text,[],settings)
        require(type(used)==int and 0<=used<=n,'교육 상한 초과',409)
        with db(True) as c:
            charge_credit(c,getw(c,ws),used-n,i)
            record_usage(c,ws,'chatgpt_import',ai.TRAIN,result)
            c.execute("INSERT INTO training VALUES(?,?,?,?,?,?,?,?)",(j,ws,'review',n,used,dump({'origin':'chatgpt_import'}),dump(result),now()))
            c.execute("UPDATE chatgpt_import_quote SET state='complete',cost=? WHERE id=?",(used,i))
    except Exception:
        with db(True) as c:
            charge_credit(c,getw(c,ws),-n,i)
            c.execute("UPDATE chatgpt_import_quote SET state='failed' WHERE id=?",(i,))
        fail(502,'정밀 분석 실패. 예약 크레딧이 복구되었습니다.')
    return {'id':j,'cost':used,'duplicate':False}

@app.post('/api/chatgpt-import/sandbox-refund')
def unused_refund(ws=Depends(ident)):
    # Test refund only. Never claims to refund money; used/failed production cases require review.
    with db(True) as c:
        o=paid_order(c,ws);require(o,'환불 가능한 테스트 이용권 없음',404)
        require(not one(c,"SELECT id FROM chatgpt_import_quote WHERE ws=? AND order_id=? AND state IN ('running','complete')",(ws,o['id'])),'분석이 시작되었거나 제공된 이용권은 별도 검토가 필요합니다.',409)
        c.execute("UPDATE checkout_order SET status='refunded' WHERE id=?",(o['id'],))
        c.execute("DELETE FROM chatgpt_import_quote WHERE ws=? AND order_id=? AND state='quoted'",(ws,o['id']))
    return {'ok':True,'sandbox':True}

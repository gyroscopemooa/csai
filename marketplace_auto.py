"""Conservative product Q&A automation: exact owner-approved static FAQ, dry-run first.
No model inference, personal/order queries, dynamic pricing or unattended AI generation.
"""
import os,re,hashlib,unicodedata
from fastapi import Depends,HTTPException
from app import app,ident,require,bounded,limit
from store import *
import marketplace_qna as q,commerce,ai,branding,workflow_controls as workflow,policies
from integrations import smartstore_transport as ss,coupang_transport as cp

INTERVAL=600
MAX_SEND=10
BLOCK=re.compile(r'배송|운송장|송장|택배|배달|주문|결제|환불|반품|교환|취소|가격|할인|쿠폰|재고|품절|입고|주소|전화|연락처|계좌|보상|불만|고장|부작용|치료|인증번호|비밀번호|개인정보|배송비|보증|약속|언제|얼마|금액|refund|return|cancel|order|shipping|delivery|tracking|price|stock|discount|payment|address|phone|medical|password|guarantee|warranty|complaint',re.I)
def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS marketplace_auto_setting(ws TEXT NOT NULL,agent TEXT NOT NULL,provider TEXT NOT NULL,connection TEXT NOT NULL,mode TEXT NOT NULL,wing TEXT NOT NULL,daily_limit INTEGER NOT NULL,next_sync INTEGER NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,provider));
        CREATE TABLE IF NOT EXISTS marketplace_auto_rule(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,provider TEXT NOT NULL,connection TEXT NOT NULL,product_id TEXT NOT NULL,question TEXT NOT NULL,answer TEXT NOT NULL,normalized TEXT NOT NULL,product_hash TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,agent,provider,connection,product_id,normalized));
        CREATE TABLE IF NOT EXISTS marketplace_auto_attempt(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,provider TEXT NOT NULL,remote_id TEXT NOT NULL,connection TEXT NOT NULL,question_hash TEXT NOT NULL,rule TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,agent,provider,remote_id,connection,question_hash,rule));
        CREATE INDEX IF NOT EXISTS marketplace_auto_due ON marketplace_auto_setting(next_sync,mode);
        CREATE INDEX IF NOT EXISTS marketplace_auto_budget ON marketplace_auto_attempt(ws,agent,provider,created,state);
        """)
init()

def normalize(s):
    # Retain punctuation (including negation) and words. Never fuzzy-match.
    return ' '.join(unicodedata.normalize('NFC',s).strip().split()).casefold()
def safe(s):
    return isinstance(s,str) and 1<=len(s)<=600 and ai.clean(s)==s and not BLOCK.search(s) and not re.search(r'\d{3,}|https?://|www\.|@|[\x00-\x1f]',s,re.I)

def configured():return os.getenv('ENABLE_MARKETPLACE_QNA_AUTO')=='1'
def live(provider):return configured() and q.send_available(provider) and os.getenv('ENABLE_MARKETPLACE_QNA_UNATTENDED_SEND')=='1'

def product_hash(p):
    if not p or not p.get('detail_as_of'):return ''
    # Bind to public detail facts, excluding temporary inventory, price, timestamps.
    base={k:p.get(k) for k in ('source','product_id','name','display_name','description','detail_fees','approved_product_facts','approved_product_faq')}
    base['options']=[{'id':x.get('id'),'name':x.get('name'),'attributes':x.get('attributes')} for x in p.get('options',[])]
    return hashlib.sha256(dump(base).encode()).hexdigest()

def setting(c,ws,a,p):
    return one(c,'SELECT * FROM marketplace_auto_setting WHERE ws=? AND agent=? AND provider=?',(ws,a,p))

def allowed(c,w,a,text):
    if ('*','*') in workflow.pause_scopes(c,w['id']) or (a,'*') in workflow.pause_scopes(c,w['id']):return False
    brand=branding.owned_agent(c,w,a)
    if not (brand['enabled'] if brand else w['enabled']):return False
    s=branding.brand_settings(w,brand)
    return s['modes'].get('general')=='auto' and workflow.decision(workflow.get_policy(c,w['id'],a),text,s)[0]=='auto'

def clear(c,ws,a,provider):
    # Preserve attempt ledger for duplicate-send safety across reconnect.
    c.execute('DELETE FROM marketplace_auto_setting WHERE ws=? AND agent=? AND provider=?',(ws,a,provider))
    c.execute('DELETE FROM marketplace_auto_rule WHERE ws=? AND agent=? AND provider=?',(ws,a,provider))

def status_data(c,ws,a,p):
    conn=q.connection(c,ws,a,p,False);fp=q.conn_hash(conn) if conn else ''
    r=setting(c,ws,a,p)
    rules=rows(c,'SELECT id,product_id,question,answer,created FROM marketplace_auto_rule WHERE ws=? AND agent=? AND provider=? AND connection=? ORDER BY created DESC LIMIT 100',(ws,a,p,fp))
    logs=rows(c,'SELECT remote_id,state,created FROM marketplace_auto_attempt WHERE ws=? AND agent=? AND provider=? ORDER BY created DESC LIMIT 50',(ws,a,p))
    return {'available':configured() and q.available(p),'live_available':live(p),'connected':bool(conn),'mode':r['mode'] if r and r['connection']==fp else 'off','daily_limit':r['daily_limit'] if r and r['connection']==fp else MAX_SEND,'rules':rules,'logs':logs}

@app.get('/api/commerce/qna/automation')
def status(provider:str,agent:str='',ws=Depends(ident)):
    with db() as c:
        commerce.access(c,ws,agent,need_enabled=False);return status_data(c,ws,agent,provider)

@app.post('/api/commerce/qna/automation')
def configure(body:dict,agent:str='',ws=Depends(ident)):
    p=body.get('provider');mode=body.get('mode');n=body.get('daily_limit',MAX_SEND)
    require(p in q.PROVIDERS and mode in ('off','preview','send') and type(n) is int and 1<=n<=MAX_SEND,'자동화 설정 오류',422)
    require(mode=='off' or configured() and body.get('confirmed') is True,'자동화 기능 및 승인 확인 필요',403)
    require(mode!='send' or live(p),'실제 무인 발송 비활성화',503)
    wing=bounded(body.get('wing',''),100) if p=='coupang' else ''
    if mode=='send' and p=='coupang':require(re.fullmatch(r'[A-Za-z0-9_@.\-]{1,100}',wing),'응답 WING ID 필요',422)
    limit('market-auto-setting:'+ws,5,60)
    with db(True) as c:
        commerce.access(c,ws,agent,True)
        if mode=='off':
            c.execute('DELETE FROM marketplace_auto_setting WHERE ws=? AND agent=? AND provider=?',(ws,agent,p))
            return status_data(c,ws,agent,p)
        conn=q.connection(c,ws,agent,p);fp=q.conn_hash(conn)
        if mode=='send':require(policies.status(c,ws)['automation_accepted'],'자동화 위험 확인 및 동의 필요',403)
        c.execute('INSERT INTO marketplace_auto_setting VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(ws,agent,provider) DO UPDATE SET connection=excluded.connection,mode=excluded.mode,wing=excluded.wing,daily_limit=excluded.daily_limit,next_sync=excluded.next_sync,updated=excluded.updated',(ws,agent,p,fp,mode,wing,n,now(),now()))
        return status_data(c,ws,agent,p)

@app.post('/api/commerce/qna/automation/rules')
def add_rule(body:dict,agent:str='',ws=Depends(ident)):
    p=body.get('provider');pid=bounded(body.get('product_id',''),32)
    question=bounded(body.get('question',''),300);answer=bounded(body.get('answer',''),600)
    require(p in q.PROVIDERS and re.fullmatch(r'[1-9][0-9]{0,31}',pid) and body.get('confirmed') is True and safe(question) and safe(answer),'고정 상품 FAQ만 허용 · 가격·배송·환불·개인정보 등 제외',422)
    limit('market-auto-rule:'+ws,10,60)
    with db(True) as c:
        commerce.access(c,ws,agent,True);conn=q.connection(c,ws,agent,p);fp=q.conn_hash(conn)
        ph=product_hash(q.snapshot(c,ws,agent,p,pid));require(ph,'상품 상세정보를 먼저 수집하세요.',409)
        old=one(c,'SELECT id FROM marketplace_auto_rule WHERE ws=? AND agent=? AND provider=? AND connection=? AND product_id=? AND normalized=?',(ws,agent,p,fp,pid,normalize(question)))
        require(old or one(c,'SELECT COUNT(*) n FROM marketplace_auto_rule WHERE ws=? AND agent=? AND provider=? AND connection=?',(ws,agent,p,fp))['n']<100,'판매처별 최대 100개 승인 답변',409)
        if old:c.execute('DELETE FROM marketplace_auto_rule WHERE id=?',(old['id'],))
        i=uid()
        c.execute('INSERT INTO marketplace_auto_rule VALUES(?,?,?,?,?,?,?,?,?,?,?)',(i,ws,agent,p,fp,pid,question,answer,normalize(question),ph,now()))
        return {'id':i}

@app.delete('/api/commerce/qna/automation/rules/{i}')
def delete_rule(i:str,agent:str='',ws=Depends(ident)):
    with db(True) as c:
        commerce.access(c,ws,agent,True)
        c.execute('DELETE FROM marketplace_auto_rule WHERE ws=? AND agent=? AND id=?',(ws,agent,i))
    return {'ok':True}

def match(c,w,a,p,fp,x):
    if not safe(x['question']) or not allowed(c,w,a,x['question']):return None
    r=one(c,'SELECT * FROM marketplace_auto_rule WHERE ws=? AND agent=? AND provider=? AND connection=? AND product_id=? AND normalized=?',(w['id'],a,p,fp,x['product_id'],normalize(x['question'])))
    if not r or not safe(r['answer']) or not allowed(c,w,a,r['answer']):return None
    if product_hash(q.snapshot(c,w['id'],a,p,x['product_id']))!=r['product_hash']:return None
    return r

def tick():
    if not configured():return False
    with db(True) as c:
        j=one(c,"SELECT * FROM marketplace_auto_setting WHERE mode IN ('preview','send') AND next_sync<=? ORDER BY next_sync LIMIT 1",(now(),))
        if not j:return False
        ws,a,p=j['ws'],j['agent'],j['provider']
        c.execute('UPDATE marketplace_auto_setting SET next_sync=? WHERE ws=? AND agent=? AND provider=?',(now()+INTERVAL,ws,a,p))
        try:
            w=commerce.access(c,ws,a,True);conn=q.connection(c,ws,a,p)
        except HTTPException:
            c.execute('DELETE FROM marketplace_auto_setting WHERE ws=? AND agent=? AND provider=?',(ws,a,p));return True
        if q.conn_hash(conn)!=j['connection']:clear(c,ws,a,p);return True
        if j['mode']=='send' and (not live(p) or not policies.status(c,ws)['automation_accepted']):return True
    try:items,partial=q.fetch_pending(p,conn)
    except Exception:return True
    if partial:return True
    # Bound work to a single live send per poll; do not scan with AI or send on incomplete lists.
    sent=False
    for x in items.values():
        with db(True) as c:
            current=setting(c,ws,a,p)
            if not current or current['updated']!=j['updated'] or current['connection']!=j['connection'] or current['mode']!=j['mode']:return True
            try:
                w=commerce.access(c,ws,a,True);q.checked_connection(c,ws,a,p,conn)
            except HTTPException:return True
            r=match(c,w,a,p,j['connection'],x)
            if not r:continue
            h=q.question_hash(x)
            # Across credential changes, never automatically repeat uncertain or completed sends.
            if q.blocked_send(c,ws,a,p,x['id']):continue
            previous=one(c,'SELECT id,state FROM marketplace_auto_attempt WHERE ws=? AND agent=? AND provider=? AND remote_id=? AND connection=? AND question_hash=? AND rule=?',(ws,a,p,x['id'],j['connection'],h,r['id']))
            if previous and previous['state']!='preview':continue
            if j['mode']=='preview':
                if not previous:c.execute('INSERT INTO marketplace_auto_attempt VALUES(?,?,?,?,?,?,?,?,?,?)',(uid(),ws,a,p,x['id'],j['connection'],h,r['id'],'preview',now()))
                continue
            if sent or not live(p) or not policies.status(c,ws)['automation_accepted']:continue
            # UTC rolling 24h, conservative: unknown attempts count too.
            used=one(c,"SELECT COUNT(*) n FROM marketplace_auto_attempt WHERE ws=? AND agent=? AND provider=? AND created>=? AND state IN ('sending','sent','unknown')",(ws,a,p,now()-86400))['n']
            if used>=j['daily_limit']:return True
            ticket=one(c,'SELECT * FROM marketplace_qna WHERE ws=? AND agent=? AND provider=? AND remote_id=? AND connection=?',(ws,a,p,x['id'],j['connection']))
            if ticket and ticket['state']!='pending':continue
            attempt=uid();stamp=now()
            if previous:
                attempt=previous['id'];c.execute("UPDATE marketplace_auto_attempt SET state='sending',created=? WHERE id=?",(stamp,attempt))
            else:c.execute('INSERT INTO marketplace_auto_attempt VALUES(?,?,?,?,?,?,?,?,?,?)',(attempt,ws,a,p,x['id'],j['connection'],h,r['id'],'sending',stamp))
            if ticket:c.execute("UPDATE marketplace_qna SET state='sending',attempt=?,seen=? WHERE ws=? AND agent=? AND provider=? AND remote_id=? AND connection=?",(attempt,stamp,ws,a,p,x['id'],j['connection']))
            else:c.execute('INSERT INTO marketplace_qna VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(ws,a,p,x['id'],j['connection'],x['product_id'],'',ai.clean(x['question'])[:2000],h,x['created'],stamp,'sending','',attempt))
            answer=r['answer']
        # Remote re-read immediately before dispatch. On ambiguity do not retry automatically.
        state='unknown'
        try:
            latest,partial=q.fetch_pending(p,conn)
            if not partial and x['id'] in latest and q.question_hash(latest[x['id']])==h:
                with db() as c:
                    current=setting(c,ws,a,p);w=commerce.access(c,ws,a,True);q.checked_connection(c,ws,a,p,conn)
                    current_rule=match(c,w,a,p,j['connection'],x)
                    ok=bool(current and current['mode']=='send' and current['updated']==j['updated'] and current_rule and current_rule['id']==r['id'] and live(p) and policies.status(c,ws)['automation_accepted'])
                if ok:
                    args=q.credentials(p,conn)
                    if p=='smartstore':ss.reply_inquiry(*args,x['id'],answer)
                    else:cp.reply_inquiry(*args,x['id'],answer,j['wing'])
                    state='sent'
        except Exception:pass
        with db(True) as c:
            c.execute("UPDATE marketplace_auto_attempt SET state=? WHERE id=? AND state='sending'",(state,attempt))
            c.execute("UPDATE marketplace_qna SET state=?,seen=? WHERE ws=? AND agent=? AND provider=? AND remote_id=? AND connection=? AND attempt=? AND state='sending'",(state,now(),ws,a,p,x['id'],j['connection'],attempt))
        sent=True
        break
    return True

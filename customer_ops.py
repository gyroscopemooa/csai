"""Purchased CRM, lead classification and deterministic quote workflows.
No additional AI call is needed: use the consultation result plus explicit intent fallback.
Never invent prices, infer sensitive traits, or create a payment.
"""
import re
from fastapi import Depends
from app import app, ident, require, bounded
from store import *

WORK={'crm','quote','tasks','leads','complaints'}
LEAD_STAGES={'inquiry','interested','ready'}
LEAD_REASONS={'inquiry':'일반 문의','interested':'상품·가격·가능 여부 문의','ready':'구체적인 예약·구매 의사'}

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS crm_contact(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),name TEXT NOT NULL,email TEXT NOT NULL DEFAULT '',phone TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL,updated INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS crm_thread(ws TEXT NOT NULL,contact TEXT NOT NULL REFERENCES crm_contact(id) ON DELETE CASCADE,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,PRIMARY KEY(ws,thread));
        CREATE TABLE IF NOT EXISTS lead_profile(ws TEXT NOT NULL,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,work TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,stage TEXT NOT NULL,source TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,thread));
        CREATE TABLE IF NOT EXISTS quote_item(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),name TEXT NOT NULL,price INTEGER NOT NULL CHECK(price>=0),active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS quote_suggestion(ws TEXT NOT NULL,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,items TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,thread));
        CREATE TABLE IF NOT EXISTS quote_offer(id TEXT PRIMARY KEY,ws TEXT NOT NULL,work TEXT NOT NULL REFERENCES work(id) ON DELETE CASCADE,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,items TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>=0),note TEXT NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL,sent INTEGER);
        """)
init()

def access(c,ws,key):require(key in entitlements(getw(c,ws)))

def signal(msg,result):
    stage=result.get('leadStage')
    if isinstance(stage,str) and stage in LEAD_STAGES:return stage,'ai'
    # Explicit commercial intent only; deterministic fallback for fixed/local replies.
    if re.search(r'환불|취소|불만|민원|안\s*살|구매\s*안|예약\s*안',msg):return 'inquiry','rules'
    if re.search(r'예약\s*(하고|하겠|할게|해주)|결제\s*(하고|할게|하겠)|구매\s*(하고|할게|하겠)|신청\s*(하고|할게)',msg):return 'ready','rules'
    if re.search(r'가격|비용|견적|얼마|가능|예약|구매|상품|price|book|quote|purchase',msg,re.I):return 'interested','rules'
    return 'inquiry','rules'

def capture_lead(c,ws,thread,msg,result):
    if 'leads' not in entitlements(getw(c,ws)):return
    stage,source=signal(msg,result)
    if stage=='inquiry':return
    old=one(c,'SELECT * FROM lead_profile WHERE ws=? AND thread=?',(ws,thread))
    if old:
        # Never downgrade by a later generic question; administrators can edit status.
        if old['stage']=='ready' and stage!='ready':return
        c.execute('UPDATE lead_profile SET stage=?,source=?,updated=? WHERE ws=? AND thread=?',(stage,source,now(),ws,thread))
        c.execute('UPDATE work SET details=? WHERE ws=? AND id=?',(LEAD_REASONS[stage],ws,old['work']))
        return
    existing=one(c,"SELECT work FROM work_link WHERE ws=? AND thread=? AND kind='leads'",(ws,thread))
    i=existing['work'] if existing else uid()
    if not existing:
        c.execute('INSERT INTO work VALUES(?,?,?,?,?,?,?)',(i,ws,'leads','잠재 고객',LEAD_REASONS[stage],'open',now()))
        c.execute('INSERT INTO work_link VALUES(?,?,?,?)',(ws,thread,'leads',i))
    c.execute('INSERT INTO lead_profile VALUES(?,?,?,?,?,?)',(ws,thread,i,stage,source,now()))

@app.get('/api/leads')
def leads(ws=Depends(ident)):
    with db() as c:
        access(c,ws,'leads')
        return rows(c,'SELECT l.*,w.status,w.title FROM lead_profile l JOIN work w ON w.id=l.work WHERE l.ws=? ORDER BY l.updated DESC',(ws,))

@app.patch('/api/leads/{thread}')
def lead_edit(thread:str,body:dict,ws=Depends(ident)):
    stage=body.get('stage');require(isinstance(stage,str) and stage in LEAD_STAGES,'분류 오류',422)
    with db(True) as c:
        access(c,ws,'leads');old=one(c,'SELECT work FROM lead_profile WHERE ws=? AND thread=?',(ws,thread));require(old,'잠재 고객 없음',404)
        c.execute("UPDATE lead_profile SET stage=?,source='staff',updated=? WHERE ws=? AND thread=?",(stage,now(),ws,thread))
        c.execute('UPDATE work SET details=? WHERE ws=? AND id=?',(LEAD_REASONS[stage],ws,old['work']))
    return {'ok':True}

def contact_fields(body,old=None):
    old=old or {};out={k:bounded(body.get(k,old.get(k,'')),n) for k,n in [('name',100),('email',254),('phone',40),('notes',2000)]}
    require(out['name'],'고객 이름 필요',422)
    require(not out['email'] or bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',out['email'])),'이메일 형식 오류',422)
    require(not out['phone'] or bool(re.fullmatch(r'[+\d ()-]{7,40}',out['phone'])),'전화번호 형식 오류',422)
    return out

def link_contact(c,ws,i,thread):
    require(one(c,"SELECT id FROM thread WHERE id=? AND ws=? AND kind<>'test'",(thread,ws)),'고객 상담 없음',404)
    c.execute('INSERT INTO crm_thread VALUES(?,?,?) ON CONFLICT(ws,thread) DO UPDATE SET contact=excluded.contact',(ws,i,thread))

@app.get('/api/crm/contacts')
def contacts(ws=Depends(ident)):
    with db() as c:
        access(c,ws,'crm');result=rows(c,'SELECT * FROM crm_contact WHERE ws=? ORDER BY updated DESC LIMIT 500',(ws,))
        for r in result:r['threads']=rows(c,'SELECT thread FROM crm_thread WHERE ws=? AND contact=?',(ws,r['id']))
        return result

@app.post('/api/crm/contacts')
def contact_create(body:dict,ws=Depends(ident)):
    f=contact_fields(body);i=uid()
    with db(True) as c:
        access(c,ws,'crm');c.execute('INSERT INTO crm_contact VALUES(?,?,?,?,?,?,?,?)',(i,ws,f['name'],f['email'],f['phone'],f['notes'],now(),now()))
        if body.get('thread'):link_contact(c,ws,i,bounded(body['thread'],100))
    return {'id':i}

@app.patch('/api/crm/contacts/{i}')
def contact_edit(i:str,body:dict,ws=Depends(ident)):
    with db(True) as c:
        access(c,ws,'crm');r=one(c,'SELECT * FROM crm_contact WHERE id=? AND ws=?',(i,ws));require(r,'고객 없음',404);f=contact_fields(body,r)
        c.execute('UPDATE crm_contact SET name=?,email=?,phone=?,notes=?,updated=? WHERE id=? AND ws=?',(f['name'],f['email'],f['phone'],f['notes'],now(),i,ws))
        if body.get('thread'):link_contact(c,ws,i,bounded(body['thread'],100))
    return {'ok':True}

@app.delete('/api/crm/contacts/{i}')
def contact_delete(i:str,ws=Depends(ident)):
    with db(True) as c:
        access(c,ws,'crm');require(one(c,'SELECT id FROM crm_contact WHERE id=? AND ws=?',(i,ws)),'고객 없음',404);c.execute('DELETE FROM crm_contact WHERE id=? AND ws=?',(i,ws))
    return {'ok':True}

@app.get('/api/quotes/items')
def quote_items(ws=Depends(ident)):
    with db() as c:access(c,ws,'quote');return rows(c,'SELECT * FROM quote_item WHERE ws=? ORDER BY name',(ws,))

@app.post('/api/quotes/items')
def quote_item_save(body:dict,ws=Depends(ident)):
    name=bounded(body.get('name',''),120);price=body.get('price');require(name and type(price)==int and 0<=price<=100000000,'상품명 및 원화 단가 필요',422)
    i=body.get('id') or uid();require(isinstance(i,str),'항목 오류',422)
    with db(True) as c:
        access(c,ws,'quote');old=one(c,'SELECT id FROM quote_item WHERE ws=? AND id=?',(ws,i))
        if body.get('id'):require(old,'견적 항목 없음',404);c.execute('UPDATE quote_item SET name=?,price=?,active=? WHERE ws=? AND id=?',(name,price,int(body.get('active',True) is True),ws,i))
        else:require(one(c,'SELECT count(*) n FROM quote_item WHERE ws=?',(ws,))['n']<100,'견적 항목 최대 100개',409);c.execute('INSERT INTO quote_item VALUES(?,?,?,?,1)',(i,ws,name,price))
    return {'id':i}

def quote_view(r):return dict(r,items=loads(r['items']))

@app.get('/api/quotes/offers')
def offers(ws=Depends(ident)):
    with db() as c:access(c,ws,'quote');return [quote_view(r) for r in rows(c,'SELECT * FROM quote_offer WHERE ws=? ORDER BY created DESC LIMIT 200',(ws,))]

@app.post('/api/quotes/offers')
def quote_create(body:dict,ws=Depends(ident)):
    work=bounded(body.get('work',''),100);items=body.get('items');note=bounded(body.get('note',''),1000)
    require(isinstance(items,list) and 1<=len(items)<=30,'견적 항목 필요',422)
    with db(True) as c:
        access(c,ws,'quote');r=one(c,"SELECT t.thread FROM work_link t JOIN work w ON w.id=t.work AND w.ws=t.ws JOIN thread th ON th.id=t.thread AND th.ws=t.ws WHERE t.ws=? AND t.work=? AND t.kind='quote' AND w.kind='quote' AND th.kind='public'",(ws,work));require(r,'고객 상담에서 접수한 견적 요청만 전송 가능합니다.',404)
        out=[];seen=set()
        for x in items:
            require(isinstance(x,dict),'항목 오류',422);i=x.get('id');q=x.get('quantity');require(isinstance(i,str) and i not in seen and type(q)==int and 1<=q<=1000,'항목 또는 수량 오류',422);seen.add(i)
            item=one(c,'SELECT * FROM quote_item WHERE ws=? AND id=? AND active=1',(ws,i));require(item,'판매 중인 견적 항목 없음',404)
            out.append({'name':item['name'],'unit_price':item['price'],'quantity':q,'total':item['price']*q})
        amount=sum(x['total'] for x in out);require(amount<=1_000_000_000,'견적 금액 한도 초과',422)
        j=uid();c.execute('INSERT INTO quote_offer VALUES(?,?,?,?,?,?,?,?,?,NULL)',(j,ws,work,r['thread'],dump(out),amount,note,'draft',now()))
        return quote_view(one(c,'SELECT * FROM quote_offer WHERE id=?',(j,)))

@app.post('/api/quotes/offers/{i}/send')
def quote_send(i:str,body:dict,ws=Depends(ident)):
    require(body.get('confirmed') is True,'최종 견적 전송 확인 필요',422)
    with db(True) as c:
        access(c,ws,'quote');r=one(c,'SELECT * FROM quote_offer WHERE ws=? AND id=?',(ws,i));require(r,'견적 없음',404)
        if r['status']=='sent':return quote_view(r)
        require(r['status']=='draft','전송 불가',409)
        text='업체에서 확인한 견적입니다.\n'+'\n'.join(x['name']+' × '+str(x['quantity'])+' = '+format(x['total'],',')+'원' for x in loads(r['items']))+'\n합계: '+format(r['amount'],',')+'원'
        if r['note']:text+='\n'+r['note']
        text+='\n결제 및 예약 확정은 별도 안내를 확인해 주세요.'
        c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,r['thread'],'staff',text,now()));c.execute("UPDATE quote_offer SET status='sent',sent=? WHERE id=?",(now(),i));c.execute("UPDATE work SET status='resolved' WHERE ws=? AND id=?",(ws,r['work']))
        return quote_view(one(c,'SELECT * FROM quote_offer WHERE id=?',(i,)))

def capture_quote_suggestion(c,ws,thread,msg,result):
    draft=result.get('workDraft')
    if not isinstance(draft,dict) or draft.get('kind')!='quote':return
    raw=draft.pop('quoteItems',[])
    active={x['id']:x for x in rows(c,'SELECT id,name,price FROM quote_item WHERE ws=? AND active=1',(ws,))}
    out=[];seen=set()
    if isinstance(raw,list):
        for x in raw[:30]:
            if isinstance(x,dict) and isinstance(x.get('id'),str) and x['id'] in active and x['id'] not in seen and type(x.get('quantity')) is int and 1<=x['quantity']<=1000:
                seen.add(x['id']);out.append({'id':x['id'],'quantity':x['quantity']})
    # Local demo and fixed-answer paths may match only a named item with explicit quantity.
    if not out:
        for item in active.values():
            m=re.search(re.escape(item['name'])+r'\s*(?:[x×]\s*)?([1-9][0-9]{0,3})\s*(?:개|건|회|명|세트)',msg,re.I)
            if m and int(m.group(1))<=1000:out.append({'id':item['id'],'quantity':int(m.group(1))})
    c.execute('INSERT INTO quote_suggestion VALUES(?,?,?,?) ON CONFLICT(ws,thread) DO UPDATE SET items=excluded.items,updated=excluded.updated',(ws,thread,dump(out),now()))

@app.get('/api/quotes/suggestions/{work}')
def quote_suggestions(work:str,ws=Depends(ident)):
    with db() as c:
        access(c,ws,'quote')
        link=one(c,"SELECT thread FROM work_link WHERE ws=? AND work=? AND kind='quote'",(ws,work));require(link,'견적 요청 없음',404)
        row=one(c,'SELECT items FROM quote_suggestion WHERE ws=? AND thread=?',(ws,link['thread']))
        active={x['id']:x for x in rows(c,'SELECT id,name,price FROM quote_item WHERE ws=? AND active=1',(ws,))}
        out=[]
        for item in loads(row['items']) if row else []:
            if item['id'] in active:out.append({'id':item['id'],'quantity':item['quantity'],'name':active[item['id']]['name'],'unit_price':active[item['id']]['price']})
        return out

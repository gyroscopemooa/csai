"""Server-authoritative sandbox checkout. No real provider or payment claims."""
from datetime import datetime,timezone
from calendar import monthrange
from fastapi import Depends, Request
from app import app,ident,require,fail,bounded,require_operator
from store import *

def init_billing():
    with db(True) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS setup_consultation(id TEXT PRIMARY KEY,ws TEXT NOT NULL,phone TEXT NOT NULL,needs TEXT NOT NULL,created INTEGER NOT NULL,client TEXT NOT NULL,UNIQUE(ws,client));
        CREATE TABLE IF NOT EXISTS checkout_order(id TEXT PRIMARY KEY,ws TEXT NOT NULL,kind TEXT NOT NULL,items TEXT NOT NULL,amount INTEGER NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL,paid_at INTEGER,client TEXT NOT NULL,UNIQUE(ws,client));
        CREATE TABLE IF NOT EXISTS subscription(ws TEXT PRIMARY KEY,period_start INTEGER NOT NULL,period_end INTEGER NOT NULL,cancel_at_end INTEGER NOT NULL DEFAULT 0,order_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS message_balance(ws TEXT NOT NULL,kind TEXT NOT NULL,n INTEGER NOT NULL CHECK(n>=0),PRIMARY KEY(ws,kind));
        ''')
init_billing()

def normalize_addons(a):
    require(isinstance(a,list) and all(isinstance(x,str) and (x in ADD or x in PACK) for x in a),'추가 상품 오류',422);a=set(a)
    packs=[PACK[k] for k in a if k in PACK];covered=set()
    for p in sorted(packs,key=lambda x:-len(x['includes'])):
        inc=set(p['includes'])
        if inc<=covered:a.discard(p['id']);continue
        require(not inc&covered,'중복 포함된 패키지는 하나씩 선택하세요.',422);covered|=inc
    a-=covered
    if {'naver','kakao'}<=covered:a.discard('channels')
    elif 'channels' in a:
        require(not {'naver','kakao'}&covered,'채널 옵션이 패키지와 중복됩니다.',422);a-={'naver','kakao'}
    for k in list(a):
        if k in ADD:a.update(x for x in ADD[k]['requires'] if x not in covered)
    price=sum((ADD.get(k) or PACK[k])['price'] for k in a)
    if {'naver','kakao'}<=a:price-=1900
    return sorted(a),price

ASSIST_FEES = CAT['assistance']['fees']
ASSIST_DISCOUNTS = CAT['assistance']['discounts']

def assist_active(c, ws):
    return bool(one(c, "SELECT s.ws FROM subscription s JOIN checkout_order o ON o.id=s.order_id AND o.ws=s.ws WHERE s.ws=? AND s.period_end>? AND o.status='paid'", (ws, now())))

@app.get('/api/billing/assistance')
def assist_options(ws=Depends(ident)):
    with db() as c:
        return {'fees': ASSIST_FEES, 'discounts': ASSIST_DISCOUNTS, 'active': assist_active(c, ws)}

@app.post('/api/billing/setup-consultations')
def request_setup_consultation(body: dict, ws=Depends(ident)):
    import re
    phone = bounded(body.get('phone',''), 32)
    needs = bounded(body.get('needs',''), 1200).strip()
    client = bounded(body.get('client',''), 100)
    require(re.fullmatch(r'[+]?[0-9 ()-]+',phone) and 8 <= sum(ch.isdigit() for ch in phone) <= 15, '연락 가능한 전화번호를 확인하세요.', 422)
    require(client, '신청 식별자가 필요합니다.', 422)
    with db(True) as c:
        previous = one(c,'SELECT id,phone,needs FROM setup_consultation WHERE ws=? AND client=?',(ws,client))
        if previous:
            require(previous['phone']==phone and previous['needs']==needs,'신청 내용이 달라졌습니다.',409)
            return {'id':previous['id']}
        ref = uid()
        c.execute('INSERT INTO setup_consultation VALUES(?,?,?,?,?,?)',(ref,ws,phone,needs,now(),client))
        notify_assistance(c,ref,'전체 세팅 대행 전화 상담 신청')
        return {'id':ref}

@app.get('/api/billing/setup-consultations/queue')
def setup_consultation_queue(req: Request):
    require_operator(req)
    with db() as c:
        return rows(c,'SELECT w.slug,s.phone,s.needs,s.created FROM setup_consultation s JOIN workspace w ON w.id=s.ws ORDER BY s.created DESC')

@app.get('/api/billing/assistance/queue')
def assist_queue(req: Request):
    require_operator(req)
    with db() as c:
        from demo_samples import assistance_examples
        return [order_view(r) for r in rows(c, "SELECT * FROM checkout_order WHERE kind='assistance' AND status IN ('review','paid') ORDER BY created DESC")] + assistance_examples()

@app.post('/api/billing/assistance/{order_id}/approve')
def approve_assistance(order_id: str, req: Request):
    require_operator(req)
    with db(True) as c:
        order = one(c, "SELECT status FROM checkout_order WHERE kind='assistance' AND id=?", (order_id,))
        require(order and order['status']=='review', '확인 대기 신청이 없습니다.', 409)
        c.execute("UPDATE checkout_order SET status='pending',created=? WHERE id=?", (now(), order_id))
        from ops import event
        event(c, one(c,'SELECT ws FROM checkout_order WHERE id=?',(order_id,))['ws'], 'assistance', '연동 대행 확인 완료 · 주문 내역에서 결제하세요.', order_id)
    return {'ok': True}

def notify_assistance(c, order_id, title):
    from ops import event
    for workspace in rows(c, 'SELECT id,owner,owner_email FROM workspace'):
        if is_operator(workspace):
            event(c, workspace['id'], 'assistance', title, order_id)

def assist_quote(body):
    details = body.get('details')
    require(isinstance(details, dict) and 1 <= len(details) <= 3 and set(details) <= ASSIST_FEES.keys(), '대행 항목을 선택하세요.', 422)
    clean = {}
    for channel in sorted(details):
        fields = details[channel]
        require(isinstance(fields, dict), '신청 정보 오류', 422)
        clean[channel] = {}
        for key in ('reference', 'access', 'platform' if channel == 'web' else 'existing'):
            value = fields.get(key)
            require(isinstance(value, str) and 0 < len(value.strip()) <= 300, '채널별 필수 정보를 확인하세요.', 422)
            clean[channel][key] = value.strip()
    email = body.get('email')
    require(isinstance(email, str) and len(email) <= 200 and '@' in email, '연락 이메일을 확인하세요.', 422)
    total = sum(ASSIST_FEES[k] for k in clean) - ASSIST_DISCOUNTS[len(clean)]
    return 'assistance', {'details': clean, 'email': email.strip()}, total

def quote(body):
    kind=body.get('kind')
    if kind=='assistance':return assist_quote(body)
    require(kind in ['subscription','education','message','memory_import'],'상품 유형 오류',422)
    if kind=='subscription':
        plan=body.get('plan');require(plan in PLAN and plan!='free','유료 요금제 선택 필요',422);a,n=normalize_addons(body.get('addons',[]))
        count=body.get('brand_quantity',1 if 'extra_agent' in a else 0)
        require(type(count) is int and 0<=count<=MAX_EXTRA_BRANDS and bool(count)==('extra_agent' in a),'추가 브랜드 수량 오류',422)
        items={'plan':plan,'addons':a}
        if count>1:items['brand_quantity']=count
        return kind,items,PLAN[plan]['price']+n+max(0,count-1)*ADD['extra_agent']['price']
    if kind=='memory_import':
        agent=bounded(body.get('agent',''),100);return kind,{'agent':agent},CAT['memory_import']['price']
    if kind=='education':
        q=next((x for x in CAT['education'] if x['id']==body.get('sku') and x['price']>0),None);require(q,'교육 상품 오류',422);return kind,{'sku':q['id'],'quantity':q['quantity']},q['price']
    q=next((x for x in CAT['messages'] if x['name']==body.get('name') and x['quantity']==body.get('quantity')),None);require(q,'메시지 상품 오류',422);return kind,{'name':q['name'],'quantity':q['quantity']},q['price']

def next_month(t):
    d=datetime.fromtimestamp(t,timezone.utc);m=d.month%12+1;y=d.year+(d.month==12);return int(d.replace(year=y,month=m,day=min(d.day,monthrange(y,m)[1])).timestamp())

def order_view(r):return dict(r,items=loads(r['items']))
@app.post('/api/billing/quote')
def checkout_quote(body:dict,ws=Depends(ident)):
    k,i,n=quote(body);result={'kind':k,'items':i,'amount':n,'currency':'KRW','sandbox':True}
    if k=='subscription':
        with db() as c:
            w=getw(c,ws);sub=one(c,'SELECT * FROM subscription WHERE ws=? AND period_end>?',(ws,now()))
            previous=one(c,"SELECT amount FROM checkout_order WHERE id=? AND ws=? AND status='paid'",(sub['order_id'],ws)) if sub else None
            old=previous['amount'] if previous else (PLAN[w['plan']]['price']+normalize_addons(loads(w['addons']))[1]+max(0,brand_quantity(w)-1)*ADD['extra_agent']['price'] if w['plan']!='free' else 0)
            delta=n-old
            remaining=max(0,sub['period_end']-now()) if sub else 0
            duration=max(1,sub['period_end']-sub['period_start']) if sub else 1
            estimate=(max(0,delta)*remaining+duration-1)//duration if sub and previous else None
            result['change']={'current_monthly':old,'next_monthly':n,'monthly_delta':delta,'period_end':sub['period_end'] if sub else None,'estimated_upgrade_proration':estimate,'actual_charge_verified':False,'sandbox_only':True}
    return result
@app.post('/api/billing/orders')
def checkout_create(body:dict,ws=Depends(ident)):
    require(DEMO,'실제 PG 미연결',503);k,i,n=quote(body);client=bounded(body.get('client',''),100);require(client,'요청 ID 필요',422)
    with db(True) as c:
        require(sandbox_allowed(c,getw(c,ws)),'공유 환경에서는 운영자만 테스트 구매할 수 있습니다.',403)
        if k=='assistance':require(assist_active(c,ws),'월 구독 결제 후 신청할 수 있습니다.',403)
        if k=='memory_import':
            from branding import owned_agent
            owned_agent(c,getw(c,ws),i['agent'])
        old=one(c,'SELECT * FROM checkout_order WHERE ws=? AND client=?',(ws,client))
        if old:
            require(old['kind']==k and old['items']==dump(i),'동일 요청 ID에 다른 상품',409);return order_view(old)
        status='pending'
        if k=='assistance' and any(f['access']!='가능' or f.get('existing','없음')!='없음' or f.get('platform')=='모름' for f in i['details'].values()):
            status='review'
        j=uid()
        if status=='review':notify_assistance(c,j,'연동 대행 사전 확인 요청')
        c.execute('INSERT INTO checkout_order VALUES(?,?,?,?,?,?,?,?,?)',(j,ws,k,dump(i),n,status,now(),None,client));return order_view(one(c,'SELECT * FROM checkout_order WHERE id=?',(j,)))
@app.post('/api/billing/orders/{i}/sandbox-confirm')
def checkout_confirm(i:str,ws=Depends(ident)):
    require(DEMO,'실결제 승인 불가',403)
    with db(True) as c:
        require(sandbox_allowed(c,getw(c,ws)),'공유 환경에서는 운영자만 테스트 구매할 수 있습니다.',403)
        r=one(c,'SELECT * FROM checkout_order WHERE ws=? AND id=?',(ws,i));require(r,'주문 없음',404)
        if r['status']=='paid':return order_view(r)
        require(r['status']=='pending' and (r['kind']=='assistance' or r['created']>now()-1800),'주문 만료 또는 취소',409);x=loads(r['items']);w=getw(c,ws)
        if r['kind']=='subscription':
            sub=one(c,'SELECT * FROM subscription WHERE ws=?',(ws,));start=now();end=next_month(start)
            if sub and sub['period_end']>start:
                # same-cycle upgrades retain used quota; no real proration in sandbox.
                start,end=sub['period_start'],sub['period_end']
            else:
                # Preserve current UTC-month usage for first migration from legacy local test plan.
                u=one(c,'SELECT n FROM usage WHERE ws=? AND period=?',(ws,month()))
                if not sub and u:c.execute('INSERT OR IGNORE INTO usage VALUES(?,?,?)',(ws,'sub:'+str(start),u['n']))
            c.execute('INSERT INTO subscription VALUES(?,?,?,?,?) ON CONFLICT(ws) DO UPDATE SET period_start=excluded.period_start,period_end=excluded.period_end,cancel_at_end=0,order_id=excluded.order_id',(ws,start,end,0,i));settings=loads(w['settings']);settings['_extra_brand_quantity']=x.get('brand_quantity',1 if 'extra_agent' in x['addons'] else 0);c.execute('UPDATE workspace SET plan=?,addons=?,settings=? WHERE id=?',(x['plan'],dump(x['addons']),dump(settings),ws))
        elif r['kind']=='assistance':
            notify_assistance(c,i,'연동 대행 결제 접수')
            require(assist_active(c,ws),'월 구독 결제 후 신청할 수 있습니다.',403)
        elif r['kind']=='education':
            # Purchased packs credit the ordinary wallet; operator/trial safety caps are separate.
            c.execute('UPDATE workspace SET credits=credits+? WHERE id=?',(x['quantity'],ws));c.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uid(),ws,'education',x['quantity'],i,now()))
        elif r['kind']=='memory_import':
            from branding import owned_agent
            owned_agent(c,w,x['agent'])  # fee entitlement only; never credit the education wallet
        else:c.execute('INSERT INTO message_balance VALUES(?,?,?) ON CONFLICT(ws,kind) DO UPDATE SET n=message_balance.n+excluded.n',(ws,x['name'],x['quantity']))
        c.execute("UPDATE checkout_order SET status='paid',paid_at=? WHERE id=?",(now(),i));return order_view(one(c,'SELECT * FROM checkout_order WHERE id=?',(i,)))
@app.post('/api/billing/orders/{i}/cancel')
def checkout_cancel(i:str,ws=Depends(ident)):
    with db(True) as c:
        r=one(c,'SELECT * FROM checkout_order WHERE id=? AND ws=?',(i,ws));require(r and r['status']=='pending','취소 가능한 미결제 주문 없음',409);c.execute("UPDATE checkout_order SET status='cancelled' WHERE id=?",(i,))
    return {'ok':True}
@app.post('/api/billing/subscription/cancel')
def subscription_cancel(ws=Depends(ident)):
    require(DEMO,'실제 구독 서비스 미연결');
    with db(True) as c:
        require(one(c,'SELECT ws FROM subscription WHERE ws=? AND period_end>?',(ws,now())),'활성 테스트 구독 없음',409);c.execute('UPDATE subscription SET cancel_at_end=1 WHERE ws=?',(ws,))
    return {'ok':True}
@app.get('/api/billing/history')
def history(ws=Depends(ident)):
    with db() as c:return {'orders':[order_view(x) for x in rows(c,'SELECT * FROM checkout_order WHERE ws=? ORDER BY rowid DESC LIMIT 100',(ws,))],'subscription':one(c,'SELECT * FROM subscription WHERE ws=?',(ws,)),'messages':rows(c,'SELECT kind,n FROM message_balance WHERE ws=?',(ws,))}

@app.post('/api/billing/orders/{i}/sandbox-fail')
def sandbox_fail(i:str,ws=Depends(ident)):
    require(DEMO,'테스트 전용',403)
    with db(True) as c:
        require(sandbox_allowed(c,getw(c,ws)),'테스트 권한 필요',403)
        row=one(c,'SELECT * FROM checkout_order WHERE ws=? AND id=?',(ws,i));require(row,'주문 없음',404)
        if row['status']=='failed':return order_view(row)
        require(row['status']=='pending','대기 주문만 실패 처리 가능',409)
        c.execute("UPDATE checkout_order SET status='failed' WHERE ws=? AND id=?",(ws,i))
        return order_view(one(c,'SELECT * FROM checkout_order WHERE ws=? AND id=?',(ws,i)))

@app.post('/api/billing/orders/{i}/sandbox-refund')
def sandbox_refund(i:str,body:dict,ws=Depends(ident)):
    require(DEMO and body.get('confirmed') is True,'테스트 환불 확인 필요',403)
    with db(True) as c:
        w=getw(c,ws);require(sandbox_allowed(c,w),'테스트 권한 필요',403)
        row=one(c,'SELECT * FROM checkout_order WHERE ws=? AND id=?',(ws,i));require(row,'주문 없음',404)
        if row['status']=='refunded':return order_view(row)
        require(row['status']=='paid','승인된 테스트 주문만 환불 가능',409)
        items=loads(row['items'])
        if row['kind']=='subscription':
            sub=one(c,'SELECT * FROM subscription WHERE ws=?',(ws,))
            require(sub and sub['order_id']==i,'현재 구독의 최신 주문만 자동 테스트 환불할 수 있습니다.',409)
            c.execute('UPDATE subscription SET period_end=?,cancel_at_end=1 WHERE ws=?',(now(),ws))
            c.execute("UPDATE workspace SET plan='free',addons='[]',enabled=0,free_used=1 WHERE id=?",(ws,))
        elif row['kind']=='education':
            n=items['quantity']
            require(w['credits']>=n,'잔여 크레딧이 부족하여 자동 전액 환불 불가',409)
            c.execute('UPDATE workspace SET credits=credits-? WHERE id=?',(n,ws));c.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uid(),ws,'education_refund',-n,i,now()))
        elif row['kind']=='memory_import':
            require(not one(c,'SELECT job FROM memory_import_batch WHERE ws=? AND order_id=?',(ws,i)),'교육 견적을 생성한 이전 이용권은 자동 테스트 환불 대상이 아닙니다.',409)
        elif row['kind']=='message':
            n=items['quantity'];kind=items['name'];balance=one(c,'SELECT n FROM message_balance WHERE ws=? AND kind=?',(ws,kind))
            require(balance and balance['n']>=n,'잔여 메시지 잔액 부족',409)
            c.execute('UPDATE message_balance SET n=n-? WHERE ws=? AND kind=?',(n,ws,kind))
        c.execute("UPDATE checkout_order SET status='refunded' WHERE ws=? AND id=?",(ws,i))
        return order_view(one(c,'SELECT * FROM checkout_order WHERE ws=? AND id=?',(ws,i)))

import os, sqlite3, json, secrets, time
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv
ROOT=Path(__file__).parent
load_dotenv(ROOT/'.env')
DATA=Path(os.getenv('DATA_DIR',str(ROOT/'data'))).resolve(); DATA.mkdir(parents=True,exist_ok=True)
CAT=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
DEMO=os.getenv('DEMO_MODE','1')=='1'
SHARED_TEST=os.getenv('SHARED_TEST_MODE','0')=='1'
OPERATOR_OWNERS={x.strip() for x in os.getenv('OPERATOR_OWNERS','').split(',') if x.strip()}
OPERATOR_EMAILS={x.strip().lower() for x in os.getenv('OPERATOR_EMAILS','').split(',') if x.strip()}
APP_URL=os.getenv('APP_URL','http://127.0.0.1:3000').rstrip('/')
PLAN={x['id']:x for x in CAT['plans']}; ADD={x['id']:x for x in CAT['addons']}; PACK={x['id']:x for x in CAT['packages']}
def uid(): return secrets.token_urlsafe(18)
def now(): return int(time.time())
def dump(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def loads(x): return json.loads(x)
def month(): return time.strftime('%Y-%m',time.gmtime())
DEFAULT_FIELDS=[{'key':k,'label':n,'type':t,'required':r} for k,n,t,r in [('name','고객명','text',True),('contact','연락처','phone',True),('location','촬영 장소','text',True),('people','촬영 인원','number',True),('product','촬영 상품','text',True),('source','구매처','text',True),('note','추가 요청사항','text',False)]]
DEFAULT={'brand':'나의 업체','tone':'자연스럽고 정중하게','emoji':False,'prompt':'등록된 정보로만 답하고 확인되지 않은 사항은 담당자에게 전달하세요.','notice':'','links':[],'price':'','location':'','hours':'','welcome':'안녕하세요. 무엇을 도와드릴까요?','fallback':'해당 내용은 담당자 확인이 필요합니다. 확인 요청을 남기겠습니다.','timezone':'Asia/Seoul','open':'09:00','close':'18:00','closed_days':[],'duration':60,'buffer':0,'payment_required':False,'resources':[{'id':'default','name':'기본 담당자'}],'modes':{k:('auto' if k in ['general','price','location','purchase'] else 'manual') for k in ['general','price','location','purchase','unknown','booking','change','complaint','email']},'fields':DEFAULT_FIELDS,'template_version':1}
DB_BACKEND=os.getenv('CSAI_DB_BACKEND','sqlite').lower()
if DB_BACKEND not in ('sqlite','postgres'):raise RuntimeError('Invalid CSAI_DB_BACKEND')
if DB_BACKEND=='sqlite' and not DEMO:raise RuntimeError('Production requires persistent PostgreSQL storage')
if DB_BACKEND=='postgres':
    from postgres_store import connect as postgres_connect

@contextmanager
def db(write=False):
    if DB_BACKEND=='postgres':
        with postgres_connect(os.environ.get('DATABASE_URL',''),write=write) as c:yield c
        return
    c=sqlite3.connect(DATA/'csai.sqlite3',timeout=30); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=30000')
    try:
        if write:c.execute('BEGIN IMMEDIATE')
        yield c
        if write:c.commit()
    except BaseException:
        c.rollback();raise
    finally:c.close()
def one(c,q,args=()):
    r=c.execute(q,args).fetchone(); return {k:v for k,v in dict(r).items() if k!='rowid'} if r else None
def rows(c,q,args=()):return [{k:v for k,v in dict(r).items() if k!='rowid'} for r in c.execute(q,args)]
def init():
    with db(True) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS workspace(id TEXT PRIMARY KEY,owner TEXT UNIQUE NOT NULL,slug TEXT UNIQUE NOT NULL,settings TEXT NOT NULL,plan TEXT NOT NULL DEFAULT 'free',credits INTEGER NOT NULL DEFAULT 20 CHECK(credits>=0),free_used INTEGER NOT NULL DEFAULT 0,addons TEXT NOT NULL DEFAULT '[]',published TEXT NOT NULL DEFAULT '{}',enabled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS session(token TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS visitor(token TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),expires INTEGER NOT NULL,kind TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS thread(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),visitor TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',manual INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL, UNIQUE(ws,visitor));
        CREATE TABLE IF NOT EXISTS message(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),thread TEXT NOT NULL REFERENCES thread(id),role TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS message_history ON message(ws,thread,created);
        CREATE INDEX IF NOT EXISTS thread_history ON thread(ws,created);
        CREATE TABLE IF NOT EXISTS usage(ws TEXT NOT NULL REFERENCES workspace(id),period TEXT NOT NULL,n INTEGER NOT NULL DEFAULT 0 CHECK(n>=0),PRIMARY KEY(ws,period));
        CREATE TABLE IF NOT EXISTS request(ws TEXT NOT NULL,thread TEXT NOT NULL,client TEXT NOT NULL,state TEXT NOT NULL,result TEXT,period TEXT,charge TEXT,created INTEGER,PRIMARY KEY(ws,thread,client));
        CREATE TABLE IF NOT EXISTS faq(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),q TEXT NOT NULL,a TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS unknown(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),thread TEXT NOT NULL,q TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS file(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),name TEXT NOT NULL,sha TEXT NOT NULL,content TEXT NOT NULL,images TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,sha));
        CREATE TABLE IF NOT EXISTS training(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),state TEXT NOT NULL,estimate INTEGER NOT NULL,cost INTEGER NOT NULL DEFAULT 0,source TEXT NOT NULL,result TEXT,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS education_reservation(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),wallet TEXT NOT NULL,wallet_ref TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>=0),state TEXT NOT NULL,cost INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL,delta INTEGER NOT NULL,ref TEXT,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS booking(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),visitor TEXT NOT NULL,start TEXT NOT NULL,end TEXT NOT NULL,resource TEXT NOT NULL,payload TEXT NOT NULL,version INTEGER NOT NULL,fields TEXT NOT NULL,status TEXT NOT NULL,customer_ok INTEGER NOT NULL DEFAULT 0,paid INTEGER NOT NULL DEFAULT 0,token TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS booking_range ON booking(ws,resource,status,start,end);
        CREATE TABLE IF NOT EXISTS work(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL,title TEXT NOT NULL,details TEXT NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS oauth_state(state TEXT PRIMARY KEY,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS trial_invite(id TEXT PRIMARY KEY,code_hash TEXT UNIQUE NOT NULL,chat_limit INTEGER NOT NULL,credit_limit INTEGER NOT NULL,booking_limit INTEGER NOT NULL DEFAULT 10,expires INTEGER NOT NULL,days INTEGER NOT NULL DEFAULT 14,created INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,used_by TEXT UNIQUE,used_at INTEGER);
        CREATE TABLE IF NOT EXISTS trial_access(ws TEXT PRIMARY KEY REFERENCES workspace(id),invite_id TEXT UNIQUE REFERENCES trial_invite(id),chat_limit INTEGER NOT NULL,chat_used INTEGER NOT NULL DEFAULT 0,credit_limit INTEGER NOT NULL,credit_used INTEGER NOT NULL DEFAULT 0,booking_limit INTEGER NOT NULL DEFAULT 10,expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS operator_wallet(ws TEXT PRIMARY KEY REFERENCES workspace(id),period TEXT NOT NULL,chat_used INTEGER NOT NULL DEFAULT 0,credit_used INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS model_usage(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),kind TEXT NOT NULL,model TEXT NOT NULL,mode TEXT NOT NULL,input_tokens INTEGER NOT NULL DEFAULT 0,cached_input_tokens INTEGER NOT NULL DEFAULT 0,output_tokens INTEGER NOT NULL DEFAULT 0,estimated_cost_usd REAL NOT NULL DEFAULT 0,created INTEGER NOT NULL);
        ''')
        if 'booking_context' not in [r[1] for r in c.execute('PRAGMA table_info(thread)')]:c.execute("ALTER TABLE thread ADD COLUMN booking_context TEXT NOT NULL DEFAULT '{}'")
        if 'days' not in [r[1] for r in c.execute('PRAGMA table_info(trial_invite)')]:c.execute('ALTER TABLE trial_invite ADD COLUMN days INTEGER NOT NULL DEFAULT 14')
        if 'owner_email' not in [r[1] for r in c.execute('PRAGMA table_info(workspace)')]:c.execute('ALTER TABLE workspace ADD COLUMN owner_email TEXT')
def workspace(c,owner):
    w=one(c,'SELECT * FROM workspace WHERE owner=?',(owner,))
    if not w:
        i=uid(); c.execute('INSERT INTO workspace(id,owner,slug,settings) VALUES(?,?,?,?)',(i,owner,secrets.token_urlsafe(7),dump(DEFAULT)));w=one(c,'SELECT * FROM workspace WHERE id=?',(i,))
    return w
def is_operator(w): return bool(w and (w['owner'] in OPERATOR_OWNERS or (w.get('owner_email') or '').lower() in OPERATOR_EMAILS and w['owner'].startswith('google:')))
def trial(c,w):
    r=one(c,'SELECT * FROM trial_access WHERE ws=? AND expires>?',(w['id'],now()))
    return r
def trial_bookings_remaining(c,w):
    t=trial(c,w)
    if not t:return None
    x=one(c,'SELECT used_at FROM trial_invite WHERE id=?',(t['invite_id'],))
    used=one(c,"SELECT count(*) n FROM booking WHERE ws=? AND created>=? AND status NOT IN ('draft','superseded')",(w['id'],x['used_at'] or 0 if x else 0))['n']
    return max(0,t['booking_limit']-used)
def sandbox_allowed(c,w):
    # Shared public demo must not grant arbitrary paid access. Local sandbox is for regression tests.
    return bool(DEMO and (is_operator(w) or (not SHARED_TEST and not one(c,'SELECT id FROM trial_invite WHERE used_by=?',(w['owner'],)))))
def operator_wallet(c,w):
    p=month();r=one(c,'SELECT * FROM operator_wallet WHERE ws=?',(w['id'],))
    if not r or r['period']!=p:
        c.execute('INSERT INTO operator_wallet(ws,period,chat_used,credit_used) VALUES(?,?,0,0) ON CONFLICT(ws) DO UPDATE SET period=excluded.period,chat_used=0,credit_used=0',(w['id'],p));r=one(c,'SELECT * FROM operator_wallet WHERE ws=?',(w['id'],))
    return r
def getw(c,i):
    w=one(c,'SELECT * FROM workspace WHERE id=?',(i,))
    if w and one(c,"SELECT name FROM sqlite_master WHERE type='table' AND name='subscription'"):
        sub=one(c,'SELECT * FROM subscription WHERE ws=?',(i,))
        if sub:
            w['subscription']=sub
            if sub['period_end']<=now():w['plan']='free';w['enabled']=0;w['free_used']=1
    if w:
        w['trial_active']=bool(trial(c,w))
    return w
def public_access(w):
    return bool(w and (is_operator(w) or w['plan']!='free' or w.get('trial_active')))
def usage_period(w):
    sub=w.get('subscription')
    return 'sub:'+str(sub['period_start']) if sub and sub['period_end']>now() else month()
def entitlements(w):
    if is_operator(w): return set(ADD)
    if w.get('trial_active') and w['plan']=='free': return {'calendar','auto_booking','change_booking'}
    a=set(loads(w['addons']))
    for i in list(a):
        if i in PACK:a.update(PACK[i]['includes'])
    if 'channels' in a:a.update(['naver','kakao'])
    return a if w['plan']!='free' else set()
# Provisional access windows only. No automatic deletion before the retention policy is approved.
BASE_HISTORY_DAYS=max(1,int(os.getenv('BASE_HISTORY_DAYS','90')))
EXTENDED_HISTORY_DAYS=max(BASE_HISTORY_DAYS,int(os.getenv('EXTENDED_HISTORY_DAYS','1825')))
def history_days(w):
    return EXTENDED_HISTORY_DAYS if 'retention' in entitlements(w) else BASE_HISTORY_DAYS
def history_cutoff(w):
    return now()-history_days(w)*86400
def thread_accessible(c,w,i):
    cutoff=history_cutoff(w)
    return bool(one(c,'SELECT t.id FROM thread t WHERE t.ws=? AND t.id=? AND (t.created>=? OR EXISTS(SELECT 1 FROM message m WHERE m.ws=t.ws AND m.thread=t.id AND m.created>=?))',(w['id'],i,cutoff,cutoff)))
def remaining(c,w):
    if is_operator(w):
        return max(0,10000-operator_wallet(c,w)['chat_used'])
    t=trial(c,w)
    if t:return max(0,t['chat_limit']-t['chat_used'])
    if w['plan']=='free':return max(0,1-w['free_used'])
    r=one(c,'SELECT n FROM usage WHERE ws=? AND period=?',(w['id'],usage_period(w)));return max(0,PLAN[w['plan']]['quantity']-(r['n'] if r else 0))
def charge_credit(c,w,n,ref):
    if is_operator(w):
        x=operator_wallet(c,w);require_limit=x['credit_used']+n<=10000
        if not require_limit: raise ValueError('운영자 교육 안전 한도(월 10,000C)를 초과했습니다.')
        c.execute('UPDATE operator_wallet SET credit_used=credit_used+? WHERE ws=?',(n,w['id']));return
    t=trial(c,w)
    if t:
        if n>0 and t['credit_used']+n>t['credit_limit']:raise ValueError('초청 체험 교육 크레딧이 부족합니다.')
        c.execute('UPDATE trial_access SET credit_used=credit_used+? WHERE ws=?',(n,w['id']));return
    if n>0 and w['credits']<n:raise ValueError('교육 크레딧 부족')
    c.execute('UPDATE workspace SET credits=credits-? WHERE id=?',(n,w['id']));c.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uid(),w['id'],'education',-n,ref,now()))
def reserve_education(c,w,n,ref):
    """Reserve against the original wallet; later entitlement changes cannot redirect a refund."""
    if type(n)!=int or n<0:raise ValueError('교육 비용 오류')
    if one(c,'SELECT id FROM education_reservation WHERE id=?',(ref,)):raise ValueError('이미 예약된 교육 비용')
    t=trial(c,w)
    if is_operator(w):
        x=operator_wallet(c,w)
        if x['credit_used']+n>10000:raise ValueError('운영자 교육 안전 한도(월 10,000C)를 초과했습니다.')
        wallet,wallet_ref='operator',x['period']
        c.execute('UPDATE operator_wallet SET credit_used=credit_used+? WHERE ws=? AND period=?',(n,w['id'],wallet_ref))
    elif t:
        if t['credit_used']+n>t['credit_limit']:raise ValueError('초청 체험 교육 크레딧이 부족합니다.')
        wallet,wallet_ref='trial',t['invite_id']
        c.execute('UPDATE trial_access SET credit_used=credit_used+? WHERE ws=? AND invite_id=?',(n,w['id'],wallet_ref))
    else:
        if w['credits']<n:raise ValueError('교육 크레딧 부족')
        wallet,wallet_ref='ordinary',''
        c.execute('UPDATE workspace SET credits=credits-? WHERE id=?',(n,w['id']))
        c.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uid(),w['id'],'education',-n,ref,now()))
    c.execute('INSERT INTO education_reservation VALUES(?,?,?,?,?,?,?,?)',(ref,w['id'],wallet,wallet_ref,n,'reserved',0,now()))

def settle_education(c,ws,ref,cost):
    r=one(c,'SELECT * FROM education_reservation WHERE ws=? AND id=?',(ws,ref))
    if not r or type(cost)!=int or not 0<=cost<=r['amount']:raise ValueError('교육 정산 오류')
    if r['state']=='settled':
        if r['cost']!=cost:raise ValueError('이미 다른 비용으로 정산됨')
        return
    if r['state']!='reserved':raise ValueError('교육 정산 상태 오류')
    refund=r['amount']-cost
    if refund:
        if r['wallet']=='operator':
            c.execute('UPDATE operator_wallet SET credit_used=MAX(0,credit_used-?) WHERE ws=? AND period=?',(refund,ws,r['wallet_ref']))
        elif r['wallet']=='trial':
            c.execute('UPDATE trial_access SET credit_used=MAX(0,credit_used-?) WHERE ws=? AND invite_id=?',(refund,ws,r['wallet_ref']))
        elif r['wallet']=='ordinary':
            c.execute('UPDATE workspace SET credits=credits+? WHERE id=?',(refund,ws))
            c.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uid(),ws,'education',refund,ref,now()))
        else:raise ValueError('교육 잔액 유형 오류')
    c.execute("UPDATE education_reservation SET state='settled',cost=? WHERE ws=? AND id=?",(cost,ws,ref))

def charge_chat(c,w,period):
    if is_operator(w):
        x=operator_wallet(c,w); 
        if x['chat_used']>=10000:raise ValueError('운영자 상담 안전 한도(월 10,000회)를 초과했습니다.')
        c.execute('UPDATE operator_wallet SET chat_used=chat_used+1 WHERE ws=?',(w['id'],));return 'operator'
    t=trial(c,w)
    if t:
        if t['chat_used']>=t['chat_limit']:raise ValueError('초청 체험 상담량을 모두 사용했습니다. 요금제를 확인하세요.')
        c.execute('UPDATE trial_access SET chat_used=chat_used+1 WHERE ws=?',(w['id'],));return 'trial'
    if w['plan']=='free':
        if w['free_used']>=1:raise ValueError('무료 테스트를 모두 사용했습니다. 요금제를 확인하세요.')
        c.execute('UPDATE workspace SET free_used=free_used+1 WHERE id=?',(w['id'],));return 'free'
    if remaining(c,w)<=0:raise ValueError('이번 구독 기간의 상담량을 모두 사용했습니다. 요금제를 확인하세요.')
    c.execute('INSERT INTO usage VALUES(?,?,1) ON CONFLICT(ws,period) DO UPDATE SET n=usage.n+1',(w['id'],period));return 'paid'
def refund_chat(c,w,period,kind):
    if kind=='operator':c.execute('UPDATE operator_wallet SET chat_used=MAX(0,chat_used-1) WHERE ws=? AND period=?',(w['id'],period))
    elif kind=='trial':c.execute('UPDATE trial_access SET chat_used=MAX(0,chat_used-1) WHERE ws=?',(w['id'],))
    elif kind=='free':c.execute('UPDATE workspace SET free_used=MAX(0,free_used-1) WHERE id=?',(w['id'],))
    else:c.execute('UPDATE usage SET n=MAX(0,n-1) WHERE ws=? AND period=?',(w['id'],period))
init()

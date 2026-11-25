"""Custom-domain control plane. External DNS/TLS setup is explicit, not a paid API action."""
import re,os,secrets,hmac
from contextvars import ContextVar
from urllib.parse import urlsplit
import httpx
from fastapi import Depends
from app import app,ident,require,bounded,fail
from store import *

current_ws=ContextVar('custom_domain_workspace',default=None)
HOST=re.compile(r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$')
MAX_AGE=86400*7

def init_domains():
    with db(True) as c:
        c.execute("CREATE TABLE IF NOT EXISTS custom_domain(ws TEXT PRIMARY KEY REFERENCES workspace(id),hostname TEXT UNIQUE NOT NULL,verification TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 0,checked INTEGER NOT NULL DEFAULT 0,detail TEXT NOT NULL DEFAULT '')")
init_domains()

def hostname(value):
    require(isinstance(value,str),'도메인 형식 오류',422)
    value=value.strip().lower().rstrip('.')
    try:value=value.encode('idna').decode('ascii')
    except UnicodeError:fail(422,'도메인 형식 오류')
    require(bool(HOST.fullmatch(value)) and value!=urlsplit(APP_URL).hostname and not value.endswith(('.workers.dev','.pages.dev','.localhost','.local','.internal','.test')),'보유한 공개 도메인 이름을 입력하세요.',422)
    return value

def target():
    return os.getenv('CUSTOM_DOMAIN_TARGET','').strip().lower().rstrip('.')

def configured():
    return bool(target() and re.fullmatch(r'[a-fA-F0-9]{32}',os.getenv('CLOUDFLARE_ZONE_ID','')) and os.getenv('CLOUDFLARE_API_TOKEN'))

def dns(name,kind):
    try:
        r=httpx.get('https://cloudflare-dns.com/dns-query',params={'name':name,'type':kind},headers={'Accept':'application/dns-json'},timeout=10,follow_redirects=False)
        r.raise_for_status();data=r.json()
        return [x['data'].strip('"').lower().rstrip('.') if kind=='CNAME' else x['data'].strip('"') for x in data.get('Answer',[]) if x.get('type')=={'TXT':16,'CNAME':5}[kind]]
    except Exception:fail(502,'DNS 조회 실패')

def verify_remote(row):
    require(configured(),'운영자의 Cloudflare for SaaS 설정이 필요합니다.',503)
    h=row['hostname']
    require(any(hmac.compare_digest(v,row['verification']) for v in dns('_csai-verify.'+h,'TXT')),'DNS TXT 소유권 인증이 아직 확인되지 않습니다.',409)
    require(target() in dns(h,'CNAME'),'CNAME 연결이 아직 확인되지 않습니다.',409)
    try:
        r=httpx.get('https://api.cloudflare.com/client/v4/zones/'+os.environ['CLOUDFLARE_ZONE_ID']+'/custom_hostnames',params={'hostname':h},headers={'Authorization':'Bearer '+os.environ['CLOUDFLARE_API_TOKEN']},timeout=10,follow_redirects=False)
        r.raise_for_status();data=r.json()
    except Exception:fail(502,'Cloudflare 도메인 상태 조회 실패')
    require(data.get('success') is True,'Cloudflare 조회 실패',502)
    found=next((x for x in data.get('result',[]) if x.get('hostname')==h),None)
    require(found and found.get('status')=='active' and found.get('ssl',{}).get('status')=='active','Cloudflare Custom Hostname 및 HTTPS 인증서가 아직 활성 상태가 아닙니다.',409)
    return True

def resolve_host(c,h):
    row=one(c,'SELECT * FROM custom_domain WHERE hostname=? AND active=1 AND checked>?',(h,now()-MAX_AGE))
    if not row:return None
    w=getw(c,row['ws'])
    if not public_access(w) or not w['enabled'] or 'domain' not in entitlements(w):return None
    return w

def view(row):
    if not row:return {'configured':configured(),'target':target(),'domain':None}
    return {'configured':configured(),'target':target(),'domain':{'hostname':row['hostname'],'txt_name':'_csai-verify.'+row['hostname'],'txt_value':row['verification'],'active':bool(row['active'] and row['checked']>now()-MAX_AGE),'checked':row['checked'],'detail':row['detail']}}

@app.get('/api/domains')
def status(ws=Depends(ident)):
    with db() as c:
        require('domain' in entitlements(getw(c,ws)));return view(one(c,'SELECT * FROM custom_domain WHERE ws=?',(ws,)))

@app.post('/api/domains')
def save(body:dict,ws=Depends(ident)):
    h=hostname(body.get('hostname'))
    with db(True) as c:
        require('domain' in entitlements(getw(c,ws)))
        old=one(c,'SELECT * FROM custom_domain WHERE ws=?',(ws,))
        if old and old['hostname']==h:return view(old)
        require(not one(c,'SELECT ws FROM custom_domain WHERE hostname=?',(h,)),'이미 등록된 도메인입니다.',409)
        token='csai-'+secrets.token_urlsafe(24)
        c.execute("INSERT INTO custom_domain(ws,hostname,verification,active,checked,detail) VALUES(?,?,?,0,0,'DNS 및 HTTPS 확인 필요') ON CONFLICT(ws) DO UPDATE SET hostname=excluded.hostname,verification=excluded.verification,active=0,checked=0,detail=excluded.detail",(ws,h,token))
        return view(one(c,'SELECT * FROM custom_domain WHERE ws=?',(ws,)))

@app.post('/api/domains/verify')
def verify(ws=Depends(ident)):
    from app import limit
    limit('domain-verify:'+ws,5,300)
    with db() as c:
        require('domain' in entitlements(getw(c,ws)));row=one(c,'SELECT * FROM custom_domain WHERE ws=?',(ws,))
        require(row,'도메인부터 등록하세요.',404)
    verify_remote(row)
    with db(True) as c:
        require('domain' in entitlements(getw(c,ws)))
        latest=one(c,'SELECT * FROM custom_domain WHERE ws=?',(ws,));require(latest and latest['hostname']==row['hostname'] and latest['verification']==row['verification'],'도메인 설정 변경됨',409)
        c.execute("UPDATE custom_domain SET active=1,checked=?,detail='DNS 및 HTTPS 검증 완료' WHERE ws=?",(now(),ws))
        return view(one(c,'SELECT * FROM custom_domain WHERE ws=?',(ws,)))

@app.delete('/api/domains')
def remove(ws=Depends(ident)):
    # Revokes app routing even after downgrade. Operator removes the external Cloudflare hostname.
    with db(True) as c:c.execute('DELETE FROM custom_domain WHERE ws=?',(ws,))
    return {'ok':True}

def tick():
    if not configured() or os.getenv('ENABLE_AUTO_DOMAINS')!='1':return
    with db() as c:pending=rows(c,'SELECT * FROM custom_domain WHERE active=1 AND checked<?',(now()-86400,))
    for row in pending[:10]:
        try:verify_remote(row)
        except Exception:continue # stale mappings stop resolving after MAX_AGE
        with db(True) as c:c.execute('UPDATE custom_domain SET checked=? WHERE ws=? AND hostname=? AND verification=?',(now(),row['ws'],row['hostname'],row['verification']))

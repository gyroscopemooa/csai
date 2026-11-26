"""Basic company logo, paid appearance/alias, and one extra assistant.
Shared workspace credits, bookings, and main knowledge; extra assistant has its own FAQ/voice.
"""
from fastapi import Depends,HTTPException
from app import app,ident,require,bounded
from store import *
import re,base64,io
from PIL import Image

def init_branding():
    with db(True) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS brand_alias(alias TEXT PRIMARY KEY,ws TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS agent_profile(id TEXT PRIMARY KEY,ws TEXT NOT NULL UNIQUE,slug TEXT NOT NULL UNIQUE,settings TEXT NOT NULL,faq TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0);
        ''')
        if 'published' not in [r[1] for r in c.execute('PRAGMA table_info(agent_profile)')]:c.execute("ALTER TABLE agent_profile ADD COLUMN published TEXT NOT NULL DEFAULT '{}'")
        # Rebuild only the legacy SQLite table, inside the existing transaction.
        if 'slot' not in [r[1] for r in c.execute('PRAGMA table_info(agent_profile)')]:
            if DB_BACKEND=='postgres':
                c.execute('ALTER TABLE agent_profile DROP CONSTRAINT IF EXISTS agent_profile_ws_key')
                c.execute('ALTER TABLE agent_profile ADD COLUMN slot INTEGER NOT NULL DEFAULT 1')
            else:
                c.execute('ALTER TABLE agent_profile RENAME TO agent_profile_legacy')
                c.execute("CREATE TABLE IF NOT EXISTS agent_profile(id TEXT PRIMARY KEY,ws TEXT NOT NULL,slug TEXT NOT NULL UNIQUE,settings TEXT NOT NULL,faq TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,published TEXT NOT NULL DEFAULT '{}',slot INTEGER NOT NULL DEFAULT 1)")
                c.execute('INSERT INTO agent_profile(id,ws,slug,settings,faq,enabled,published,slot) SELECT id,ws,slug,settings,faq,enabled,published,1 FROM agent_profile_legacy')
                c.execute('DROP TABLE agent_profile_legacy')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS agent_profile_slot_unique ON agent_profile(ws,slot)')
        c.execute('CREATE TABLE IF NOT EXISTS file_brand(file TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS agent_knowledge_version(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,content TEXT NOT NULL,created INTEGER NOT NULL)')
        if 'agent' not in [r[1] for r in c.execute('PRAGMA table_info(visitor)')]:c.execute("ALTER TABLE visitor ADD COLUMN agent TEXT NOT NULL DEFAULT ''")
init_branding()

def agent_allowed(w,a):
    return bool(w and a and 1<=a.get('slot',1)<=brand_quantity(w))

def owned_agent(c,w,agent_id):
    if not agent_id:return None
    require(isinstance(agent_id,str),'브랜드 형식 오류',422)
    a=one(c,'SELECT * FROM agent_profile WHERE id=? AND ws=?',(agent_id,w['id']))
    require(agent_allowed(w,a),'브랜드 권한 또는 정보 없음',403)
    return a

def brand_settings(w,a):
    if not a:return loads(w['settings'])
    # Never inherit another brand's price, links, location or branding.
    s=loads(dump(DEFAULT));s.update(loads(a['settings']))
    # Brand-specific operational data is not yet migrated. Fail closed.
    s['modes']=dict(s['modes'],booking='off',change='off')
    return s

def brand_view(w,a):
    s=brand_settings(w,a);s.update(appearance(w,s));return dict(a,settings=s,faq=loads(a['faq']),published=loads(a['published']),available=agent_allowed(w,a))

def resolve(c,slug):
    w=one(c,'SELECT * FROM workspace WHERE slug=?',(slug,))
    if w:return getw(c,w['id']),None
    a=one(c,'SELECT * FROM brand_alias WHERE alias=?',(slug,))
    if a:
        w=getw(c,a['ws']);return (w,None) if 'custom_url' in entitlements(w) else (None,None)
    a=one(c,'SELECT * FROM agent_profile WHERE slug=? AND enabled=1',(slug,))
    if a:
        w=getw(c,a['ws']);return (w,a) if agent_allowed(w,a) else (None,None)
    return None,None

def appearance(w,s):
    a=entitlements(w);return {'logo':s.get('logo',''),'color':s.get('color','#3182F6') if 'design' in a else '#3182F6','unbrand':bool(s.get('unbrand') and 'unbrand' in a),'theme':s.get('theme','dark') if 'design' in a else 'dark','density':s.get('density','normal') if 'design' in a else 'normal','bubble_radius':s.get('bubble_radius','rounded') if 'design' in a else 'rounded'}
def merged(c,w,v):
    s=loads(w['settings']);agent=None
    if v.get('agent'):
        agent=owned_agent(c,w,v['agent']);require(v['kind']=='test' or agent['enabled'],'추가 브랜드 상담원 비활성화',403);s=brand_settings(w,agent)
    return s,agent

def unique_slug(c,slug):return not (one(c,'SELECT id FROM workspace WHERE slug=?',(slug,)) or one(c,'SELECT alias FROM brand_alias WHERE alias=?',(slug,)) or one(c,'SELECT id FROM agent_profile WHERE slug=?',(slug,)))
@app.get('/api/appearance')
def get_appearance(agent:str='',ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);profile=owned_agent(c,w,agent);s=brand_settings(w,profile);a=one(c,'SELECT alias FROM brand_alias WHERE ws=?',(ws,)) if not profile else None;return appearance(w,s)|{'alias':a['alias'] if a else ''}
@app.post('/api/appearance')
def set_appearance(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);profile=owned_agent(c,w,body.get('agent',''));s=loads(profile['settings'] if profile else w['settings']);a=entitlements(w)
        if 'logo' in body:
            data=bounded(body['logo'],600000)
            if data:
                try:
                    raw=base64.b64decode(data,validate=True);require(len(raw)<=400000,'로고 400KB 이하',422)
                    with Image.open(io.BytesIO(raw)) as im:
                        im.thumbnail((128,128));o=io.BytesIO();im.convert('RGBA').save(o,format='PNG');s['logo']='data:image/png;base64,'+base64.b64encode(o.getvalue()).decode()
                except Exception:raise HTTPException(422,'유효한 이미지 파일을 선택하세요.')
            else:s['logo']=''
        if 'color' in body:require('design' in a);require(isinstance(body['color'],str) and bool(re.fullmatch(r'#[0-9a-fA-F]{6}',body['color'])),'색상 형식 오류',422);s['color']=body['color']
        for key,choices in {'theme':{'dark','toss','messenger','premium'},'density':{'normal','compact','roomy'},'bubble_radius':{'rounded','square'}}.items():
            if key in body:require('design' in a);require(isinstance(body[key],str) and body[key] in choices,'디자인 옵션 오류',422);s[key]=body[key]
        if 'unbrand' in body:require('unbrand' in a);s['unbrand']=body['unbrand'] is True
        if 'alias' in body:
            require(not profile,'브랜드별 별칭 연동 준비 중',409);require('custom_url' in a);alias=bounded(body['alias'],48).lower();old=one(c,'SELECT alias FROM brand_alias WHERE ws=?',(ws,))
            if alias:
                require(re.fullmatch(r'[a-z0-9][a-z0-9-]{2,47}',alias),'3~48자 영문 소문자·숫자·하이픈',422);require(old and old['alias']==alias or unique_slug(c,alias),'이미 사용 중인 주소',409);c.execute('INSERT INTO brand_alias VALUES(?,?) ON CONFLICT(ws) DO UPDATE SET alias=excluded.alias',(alias,ws))
            else:c.execute('DELETE FROM brand_alias WHERE ws=?',(ws,))
        if profile:c.execute('UPDATE agent_profile SET settings=? WHERE ws=? AND id=?',(dump(s),ws,profile['id']))
        else:c.execute('UPDATE workspace SET settings=? WHERE id=?',(dump(s),ws))
    return {'ok':True}
@app.get('/api/agents/list')
def agent_list(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws)
        return {'quantity':brand_quantity(w),'agents':[brand_view(w,a)|{'archived':bool(one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(ws,a['id'])))} for a in rows(c,'SELECT * FROM agent_profile WHERE ws=? ORDER BY slot',(ws,))]}

@app.get('/api/agents')
def agents(agent:str='',ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);require('extra_agent' in entitlements(w));a=owned_agent(c,w,agent) if agent else one(c,'SELECT * FROM agent_profile WHERE ws=? AND slot=1',(ws,));return None if not a else brand_view(w,a)

@app.post('/api/agents')
def agent_save(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);require('extra_agent' in entitlements(w))
        old=owned_agent(c,w,body['id']) if body.get('id') else (None if body.get('create') is True else one(c,'SELECT * FROM agent_profile WHERE ws=? AND slot=1',(ws,)))
        previous=brand_settings(w,old) if old else loads(dump(DEFAULT))
        s={k:bounded(body.get(k,previous.get(k,'')),1500) for k in ['brand','tone','welcome','fallback','notice','price','location','hours']}
        s['prompt']=previous.get('prompt',DEFAULT['prompt']);require('prompt' not in body or body['prompt']==s['prompt'],'상담 지침은 AI 교육에서 변경하세요.',422);require(s['brand'] and s['welcome'],'상담원 이름 및 인사말 필요',422)
        s['emoji']=body.get('emoji',previous.get('emoji')) is True
        for key in ('logo','color','theme','density','bubble_radius','unbrand'):
            if key in previous:s[key]=previous[key]
        links=body.get('links',previous.get('links',[]));require(isinstance(links,list) and len(links)<=10,'판매처 최대 10개',422);s['links']=[]
        from urllib.parse import urlsplit
        for link in links:
            require(isinstance(link,dict),'링크 형식 오류',422);u=bounded(link.get('url',''),1000);p=urlsplit(u);require(p.scheme=='https' and p.hostname and not p.username,'HTTPS 링크만 등록',422);s['links'].append({'name':bounded(link.get('name',''),100),'url':u})
        for key in ('industries','desired_work'):
            value=body.get(key,previous.get(key,[]));require(isinstance(value,list) and len(value)<=30 and all(isinstance(x,str) and 0<len(x.strip())<=80 for x in value),'복수 선택 항목 형식 오류',422);s[key]=list(dict.fromkeys(x.strip() for x in value))
        s['consultation_mode']=body.get('consultation_mode',previous.get('consultation_mode','ai'));require(s['consultation_mode'] in ('ai','staff'),'상담 방식 오류',422)
        fs=loads(old['faq']) if old else [];require('faq' not in body or body['faq']==fs,'개별 FAQ는 AI 교육에서 등록하세요.',422)
        slots={r['slot'] for r in rows(c,'SELECT slot FROM agent_profile WHERE ws=?',(ws,))}
        slot=old['slot'] if old else next((n for n in range(1,brand_quantity(w)+1) if n not in slots),None)
        require(slot is not None,'구매한 브랜드 수량을 모두 사용했습니다.',409)
        i=old['id'] if old else uid();slug=old['slug'] if old else secrets.token_urlsafe(10)
        enabled=int(body.get('enabled',bool(old and old['enabled'])) is True)
        if enabled:require(not one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(ws,i)),'보관된 브랜드를 먼저 복구하세요.',409)
        c.execute('INSERT INTO agent_profile(id,ws,slug,settings,faq,enabled,slot) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET settings=excluded.settings,faq=excluded.faq,enabled=excluded.enabled',(i,ws,slug,dump(s),dump(fs),enabled,slot))
    return {'slug':slug,'id':i,'slot':slot}

@app.get('/api/agents/versions')
def agent_versions(ws=Depends(ident)):
    with db() as c:
        require('extra_agent' in entitlements(getw(c,ws)));return rows(c,'SELECT id,agent,created FROM agent_knowledge_version WHERE ws=? ORDER BY created DESC LIMIT 100',(ws,))
@app.post('/api/agents/versions/{i}/restore')
def agent_restore(i:str,ws=Depends(ident)):
    with db(True) as c:
        require('extra_agent' in entitlements(getw(c,ws)));v=one(c,'SELECT * FROM agent_knowledge_version WHERE ws=? AND id=?',(ws,i));require(v,'교육 버전 없음',404);a=one(c,'SELECT * FROM agent_profile WHERE ws=? AND id=?',(ws,v['agent']));require(agent_allowed(getw(c,ws),a),'상담원 없음 또는 권한 없음',404);c.execute('INSERT INTO agent_knowledge_version VALUES(?,?,?,?,?)',(uid(),ws,a['id'],a['published'],now()));c.execute('UPDATE agent_profile SET published=? WHERE ws=? AND id=?',(v['content'],ws,a['id']))
    return {'ok':True}

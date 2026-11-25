"""Paid appearance/alias and one extra independently configured assistant.
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
        c.execute('CREATE TABLE IF NOT EXISTS agent_knowledge_version(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,content TEXT NOT NULL,created INTEGER NOT NULL)')
        if 'agent' not in [r[1] for r in c.execute('PRAGMA table_info(visitor)')]:c.execute("ALTER TABLE visitor ADD COLUMN agent TEXT NOT NULL DEFAULT ''")
init_branding()

def resolve(c,slug):
    w=one(c,'SELECT * FROM workspace WHERE slug=?',(slug,))
    if w:return getw(c,w['id']),None
    a=one(c,'SELECT * FROM brand_alias WHERE alias=?',(slug,))
    if a:
        w=getw(c,a['ws']);return (w,None) if 'custom_url' in entitlements(w) else (None,None)
    a=one(c,'SELECT * FROM agent_profile WHERE slug=? AND enabled=1',(slug,))
    if a:
        w=getw(c,a['ws']);return (w,a) if 'extra_agent' in entitlements(w) else (None,None)
    return None,None

def appearance(w,s):
    a=entitlements(w);return {'logo':s.get('logo',''),'color':s.get('color','#3182F6') if 'design' in a else '#3182F6','unbrand':bool(s.get('unbrand') and 'unbrand' in a),'theme':s.get('theme','dark') if 'design' in a else 'dark','density':s.get('density','normal') if 'design' in a else 'normal','bubble_radius':s.get('bubble_radius','rounded') if 'design' in a else 'rounded'}
def merged(c,w,v):
    s=loads(w['settings']);agent=None
    if v.get('agent'):
        agent=one(c,'SELECT * FROM agent_profile WHERE id=? AND ws=? AND enabled=1',(v['agent'],w['id']));require(agent and 'extra_agent' in entitlements(w),'추가 상담원 비활성화',403);s.update(loads(agent['settings']))
    return s,agent

def unique_slug(c,slug):return not (one(c,'SELECT id FROM workspace WHERE slug=?',(slug,)) or one(c,'SELECT alias FROM brand_alias WHERE alias=?',(slug,)) or one(c,'SELECT id FROM agent_profile WHERE slug=?',(slug,)))
@app.get('/api/appearance')
def get_appearance(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);s=loads(w['settings']);a=one(c,'SELECT alias FROM brand_alias WHERE ws=?',(ws,));return appearance(w,s)|{'alias':a['alias'] if a else ''}
@app.post('/api/appearance')
def set_appearance(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);s=loads(w['settings']);a=entitlements(w)
        if 'logo' in body:
            require(public_access(w) or body['logo']=='','유료 구독 또는 초청 체험 필요');data=bounded(body['logo'],600000)
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
            require('custom_url' in a);alias=bounded(body['alias'],48).lower();old=one(c,'SELECT alias FROM brand_alias WHERE ws=?',(ws,))
            if alias:
                require(re.fullmatch(r'[a-z0-9][a-z0-9-]{2,47}',alias),'3~48자 영문 소문자·숫자·하이픈',422);require(old and old['alias']==alias or unique_slug(c,alias),'이미 사용 중인 주소',409);c.execute('INSERT INTO brand_alias VALUES(?,?) ON CONFLICT(ws) DO UPDATE SET alias=excluded.alias',(alias,ws))
            else:c.execute('DELETE FROM brand_alias WHERE ws=?',(ws,))
        c.execute('UPDATE workspace SET settings=? WHERE id=?',(dump(s),ws))
    return {'ok':True}
@app.get('/api/agents')
def agents(ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);require('extra_agent' in entitlements(w));a=one(c,'SELECT * FROM agent_profile WHERE ws=?',(ws,));return None if not a else dict(a,settings=loads(a['settings']),faq=loads(a['faq']),published=loads(a['published']))
@app.post('/api/agents')
def agent_save(body:dict,ws=Depends(ident)):
    with db(True) as c:
        w=getw(c,ws);require('extra_agent' in entitlements(w));old=one(c,'SELECT * FROM agent_profile WHERE ws=?',(ws,));previous=loads(old['settings']) if old else DEFAULT;s={k:bounded(body.get(k,previous.get(k,'')),1500) for k in ['brand','tone','welcome','fallback']};s['prompt']=previous.get('prompt',DEFAULT['prompt']);require('prompt' not in body or body['prompt']==s['prompt'],'상담 지침은 AI 교육에서 변경하세요.',422);require(s['brand'] and s['welcome'],'상담원 이름 및 인사말 필요',422);s['emoji']=body.get('emoji') is True
        fs=loads(old['faq']) if old else [];require('faq' not in body or body['faq']==fs,'개별 FAQ는 AI 교육에서 등록하세요.',422);i=old['id'] if old else uid();slug=old['slug'] if old else secrets.token_urlsafe(10)
        c.execute('INSERT INTO agent_profile(id,ws,slug,settings,faq,enabled) VALUES(?,?,?,?,?,?) ON CONFLICT(ws) DO UPDATE SET settings=excluded.settings,faq=excluded.faq,enabled=excluded.enabled',(i,ws,slug,dump(s),dump(fs),int(body.get('enabled') is True)))
    return {'slug':slug,'id':i}

@app.get('/api/agents/versions')
def agent_versions(ws=Depends(ident)):
    with db() as c:
        require('extra_agent' in entitlements(getw(c,ws)));return rows(c,'SELECT id,agent,created FROM agent_knowledge_version WHERE ws=? ORDER BY created DESC LIMIT 100',(ws,))
@app.post('/api/agents/versions/{i}/restore')
def agent_restore(i:str,ws=Depends(ident)):
    with db(True) as c:
        require('extra_agent' in entitlements(getw(c,ws)));v=one(c,'SELECT * FROM agent_knowledge_version WHERE ws=? AND id=?',(ws,i));require(v,'교육 버전 없음',404);a=one(c,'SELECT * FROM agent_profile WHERE ws=? AND id=?',(ws,v['agent']));require(a,'상담원 없음',404);c.execute('INSERT INTO agent_knowledge_version VALUES(?,?,?,?,?)',(uid(),ws,a['id'],a['published'],now()));c.execute('UPDATE agent_profile SET published=? WHERE ws=? AND id=?',(v['content'],ws,a['id']))
    return {'ok':True}

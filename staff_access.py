"""Staff portal with explicit membership, never an owner workspace session."""
import re,secrets,hashlib
from fastapi import Depends,Request
from app import app,ident,require,bounded,limit
from store import *
import ops,branding,policies

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS session_verified_email(token TEXT PRIMARY KEY REFERENCES session(token) ON DELETE CASCADE,email TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS staff_member(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),email TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,agent TEXT NOT NULL,assigned_only INTEGER NOT NULL,identity TEXT NOT NULL DEFAULT '',state TEXT NOT NULL,invite_hash TEXT NOT NULL DEFAULT '',expires INTEGER NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,email));
        CREATE INDEX IF NOT EXISTS staff_identity ON staff_member(identity,state);
        CREATE TABLE IF NOT EXISTS staff_thread(ws TEXT NOT NULL,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,member TEXT NOT NULL REFERENCES staff_member(id),PRIMARY KEY(ws,thread));
        CREATE TABLE IF NOT EXISTS staff_audit(id TEXT PRIMARY KEY,ws TEXT NOT NULL,member TEXT NOT NULL,thread TEXT NOT NULL,action TEXT NOT NULL,client TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,member,client));
        """)
init()

def digest(code):return hashlib.sha256(code.encode()).hexdigest()

def verified(c,req,own_ws):
    s=one(c,"SELECT w.owner,e.email FROM session s JOIN workspace w ON w.id=s.ws JOIN session_verified_email e ON e.token=s.token WHERE s.token=? AND s.ws=? AND s.expires>?",(req.cookies.get('csai_session',''),own_ws,now()))
    require(s and s['owner'].startswith('google:'),'초청받은 이메일로 Google 재로그인하세요.',403)
    return s

def active_owner(c,ws):
    w=getw(c,ws);require(public_access(w),'유료 상담 또는 체험 이용 권한 필요',403)
    if policies.ENFORCED:require(policies.status(c,ws)['accepted'],'업체 정책 확인 필요',403)
    return w

def scope(c,w,agent,write=False):
    ops.work_scope(c,w,agent,write)
    if agent:require(not one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(w['id'],agent)),'보관된 브랜드입니다.',403)

def view(m):
    return {k:m[k] for k in ('id','name','email','role','agent','assigned_only','state','expires','created')}

def membership(c,own,mid):
    w=getw(c,own);m=one(c,"SELECT * FROM staff_member WHERE id=? AND identity=? AND state='active'",(mid,w['owner']))
    require(m and w['owner'].startswith('google:'),'직원 권한 없음',403)
    target=active_owner(c,m['ws']);scope(c,target,m['agent']);return m,target

def visible_thread(c,m,w,tid,write=False):
    t=one(c,"SELECT t.id,t.kind,t.status,t.manual,t.created FROM thread t JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE t.ws=? AND t.id=? AND t.kind<>'test' AND COALESCE(v.agent,'')=? AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id)",(m['ws'],tid,m['agent']))
    require(t and thread_accessible(c,w,tid),'상담 없음 또는 조회 권한 없음',404)
    if m['assigned_only']:require(one(c,'SELECT thread FROM staff_thread WHERE ws=? AND thread=? AND member=?',(m['ws'],tid,m['id'])),'배정된 상담 없음',404)
    if write:require(m['role']=='agent','조회 전용 직원입니다.',403)
    return t

@app.get('/api/team')
def team(ws=Depends(ident)):
    with db() as c:return [view(m) for m in rows(c,'SELECT * FROM staff_member WHERE ws=? ORDER BY created DESC',(ws,))]

@app.post('/api/team/invite')
def invite(body:dict,ws=Depends(ident)):
    email=bounded(body.get('email',''),254).lower();name=bounded(body.get('name',''),80);role=body.get('role','agent');agent=body.get('agent','');assigned=body.get('assigned_only',True)
    require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) and name and role in ('viewer','agent') and type(assigned) is bool,'직원 정보 오류',422)
    limit('team-invite:'+ws,20,3600)
    with db(True) as c:
        w=active_owner(c,ws);scope(c,w,agent,True)
        require(email!=(w.get('owner_email') or '').lower(),'사업주 본인은 초청할 필요가 없습니다.',409)
        old=one(c,'SELECT * FROM staff_member WHERE ws=? AND email=?',(ws,email))
        require(not old or old['state']!='active','이미 등록된 직원입니다.',409)
        require(old and old['state']!='revoked' or one(c,"SELECT count(*) n FROM staff_member WHERE ws=? AND state<>'revoked'",(ws,))['n']<30,'직원 최대 30명',409)
        code=secrets.token_urlsafe(32);i=old['id'] if old else uid()
        if old:
            c.execute('DELETE FROM staff_thread WHERE ws=? AND member=?',(ws,i))
            c.execute("UPDATE staff_member SET name=?,role=?,agent=?,assigned_only=?,identity='',state='pending',invite_hash=?,expires=? WHERE ws=? AND id=?",(name,role,agent,int(assigned),digest(code),now()+604800,ws,i))
        else:c.execute('INSERT INTO staff_member VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,email,name,role,agent,int(assigned),'','pending',digest(code),now()+604800,now()))
        return {'id':i,'code':code,'accept_path':'/#staff-invite='+code}

@app.post('/api/team/{mid}/permissions')
def permissions(mid:str,body:dict,ws=Depends(ident)):
    role=body.get('role');agent=body.get('agent','');assigned=body.get('assigned_only')
    require(role in ('viewer','agent') and type(assigned) is bool,'권한 오류',422)
    with db(True) as c:
        w=active_owner(c,ws);scope(c,w,agent,True)
        m=one(c,"SELECT * FROM staff_member WHERE ws=? AND id=? AND state='active'",(ws,mid));require(m,'활성 직원 없음',404)
        if m['agent']!=agent:c.execute('DELETE FROM staff_thread WHERE ws=? AND member=?',(ws,mid))
        c.execute('UPDATE staff_member SET role=?,agent=?,assigned_only=? WHERE ws=? AND id=?',(role,agent,int(assigned),ws,mid))
    return {'ok':True}

@app.post('/api/team/{mid}/revoke')
def revoke(mid:str,ws=Depends(ident)):
    with db(True) as c:
        require(one(c,'SELECT id FROM staff_member WHERE ws=? AND id=?',(ws,mid)),'직원 없음',404)
        c.execute("UPDATE staff_member SET state='revoked',invite_hash='',identity='' WHERE ws=? AND id=?",(ws,mid));c.execute('DELETE FROM staff_thread WHERE ws=? AND member=?',(ws,mid))
    return {'ok':True}

@app.post('/api/staff/accept')
def accept(body:dict,req:Request,ws=Depends(ident)):
    code=bounded(body.get('code',''),100);limit('team-accept:'+ws,10,60)
    require(re.fullmatch(r'[A-Za-z0-9_-]{30,100}',code),'초청 코드 오류',422)
    with db(True) as c:
        s=verified(c,req,ws)
        m=one(c,"SELECT * FROM staff_member WHERE invite_hash=? AND state='pending' AND expires>?",(digest(code),now()))
        require(m and s['email']==m['email'] and m['ws']!=ws,'유효하지 않은 초청 또는 이메일 불일치',403)
        w=active_owner(c,m['ws']);scope(c,w,m['agent'],True)
        require(not one(c,"SELECT id FROM staff_member WHERE ws=? AND identity=? AND state='active'",(m['ws'],s['owner'])),'이미 등록된 계정입니다.',409)
        c.execute("UPDATE staff_member SET identity=?,state='active',invite_hash='' WHERE id=? AND state='pending'",(s['owner'],m['id']))
    return {'id':m['id']}

@app.get('/api/staff/memberships')
def memberships(ws=Depends(ident)):
    with db() as c:
        own=getw(c,ws)
        if not own['owner'].startswith('google:'):return []
        out=[]
        for m in rows(c,"SELECT * FROM staff_member WHERE identity=? AND state='active'",(own['owner'],)):
            w=getw(c,m['ws'])
            if not public_access(w) or (policies.ENFORCED and not policies.status(c,m['ws'])['accepted']):continue
            a=one(c,'SELECT * FROM agent_profile WHERE ws=? AND id=?',(m['ws'],m['agent'])) if m['agent'] else None
            if m['agent'] and (not branding.agent_allowed(w,a) or one(c,'SELECT agent FROM archived_brand WHERE ws=? AND agent=?',(m['ws'],m['agent']))):continue
            out.append({'id':m['id'],'name':m['name'],'role':m['role'],'assigned_only':bool(m['assigned_only']),'brand':branding.brand_settings(w,a)['brand']})
        return out

@app.get('/api/team/threads/{tid}')
def assigned(tid:str,ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);agent=ops.thread_brand(c,w,tid)
        current=one(c,'SELECT member FROM staff_thread WHERE ws=? AND thread=?',(ws,tid))
        people=rows(c,"SELECT id,name,role FROM staff_member WHERE ws=? AND agent=? AND state='active' ORDER BY name",(ws,agent))
        return {'member':current['member'] if current else '', 'people':people}

@app.post('/api/team/threads/{tid}')
def assign(tid:str,body:dict,ws=Depends(ident)):
    mid=bounded(body.get('member',''),100)
    with db(True) as c:
        w=active_owner(c,ws);agent=ops.thread_brand(c,w,tid,True)
        if mid:
            m=one(c,"SELECT id,name FROM staff_member WHERE ws=? AND agent=? AND id=? AND state='active'",(ws,agent,mid));require(m,'같은 브랜드의 활성 직원만 배정할 수 있습니다.',404)
            c.execute('INSERT INTO staff_thread VALUES(?,?,?) ON CONFLICT(ws,thread) DO UPDATE SET member=excluded.member',(ws,tid,mid))
        else:c.execute('DELETE FROM staff_thread WHERE ws=? AND thread=?',(ws,tid))
    return {'ok':True}

@app.get('/api/staff/{mid}/threads')
def staff_threads(mid:str,ws=Depends(ident)):
    with db() as c:
        m,w=membership(c,ws,mid);target=m['ws'];cutoff=history_cutoff(w)
        sql="SELECT t.id,t.kind,t.status,t.manual,t.created,(SELECT body FROM message WHERE ws=t.ws AND thread=t.id AND created>=? ORDER BY rowid DESC LIMIT 1) last,(SELECT MAX(created) FROM message WHERE ws=t.ws AND thread=t.id) activity FROM thread t JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE t.ws=? AND COALESCE(v.agent,'')=? AND t.kind<>'test' AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id) AND (t.created>=? OR EXISTS(SELECT 1 FROM message x WHERE x.ws=t.ws AND x.thread=t.id AND x.created>=?))"
        args=[cutoff,target,m['agent'],cutoff,cutoff]
        if m['assigned_only']:
            sql+=" AND EXISTS(SELECT 1 FROM staff_thread st WHERE st.ws=t.ws AND st.thread=t.id AND st.member=?)";args.append(mid)
        return rows(c,sql+" ORDER BY COALESCE((SELECT MAX(created) FROM message WHERE ws=t.ws AND thread=t.id),t.created) DESC LIMIT 200",args)

@app.get('/api/staff/{mid}/threads/{tid}')
def staff_detail(mid:str,tid:str,ws=Depends(ident)):
    with db() as c:
        m,w=membership(c,ws,mid);t=visible_thread(c,m,w,tid)
        import chat_attachments,web_calls
        return t|{'messages':chat_attachments.messages(c,m['ws'],tid,history_cutoff(w)), 'can_reply':m['role']=='agent' and t['kind']=='public','photos':chat_attachments.enabled(c,m['ws'],m['agent']),'files':chat_attachments.files_enabled(c,m['ws'],m['agent']),'web_calls':web_calls.enabled(c,m['ws'],m['agent'])}

@app.post('/api/staff/{mid}/threads/{tid}')
def staff_update(mid:str,tid:str,body:dict,ws=Depends(ident)):
    action=body.get('action');client=bounded(body.get('client',''),100)
    require(action in ('reply','resolve') and re.fullmatch(r'[A-Za-z0-9_-]{12,100}',client),'처리 유형 오류',422)
    limit('staff-write:'+ws,60,60)
    with db(True) as c:
        m,w=membership(c,ws,mid);t=visible_thread(c,m,w,tid,True);target=m['ws']
        require(t['kind']=='public','외부 채널 직원 발송은 아직 지원하지 않습니다.',409)
        old=one(c,'SELECT thread,action FROM staff_audit WHERE ws=? AND member=? AND client=?',(target,mid,client))
        if old:
            require(old['thread']==tid and old['action']==action,'요청 ID 중복',409)
            return {'ok':True,'duplicate':True}
        require(not one(c,"SELECT client FROM request WHERE ws=? AND thread=? AND state='running'",(target,tid)),'AI 응답 완료 후 처리하세요.',409)
        if action=='reply':
            message=bounded(body.get('reply',''),2000);require(message,'답변을 입력하세요.',422)
            clear_temporary_takeover(c,target,tid)
            c.execute("UPDATE thread SET manual=1,status='open' WHERE ws=? AND id=?",(target,tid))
            c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),target,tid,'staff',message,now()))
        else:c.execute("UPDATE thread SET status='resolved' WHERE ws=? AND id=?",(target,tid))
        c.execute('INSERT INTO staff_audit VALUES(?,?,?,?,?,?,?)',(uid(),target,mid,tid,action,client,now()))
    return {'ok':True,'duplicate':False}

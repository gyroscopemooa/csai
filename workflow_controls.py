"""Owner-approved workflow rules. No additional LLM calls or automatic financial actions."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import Depends
from store import *
import ai

TASKS={
 'refund':r'환불|반품|refund|chargeback',
 'complaint':r'불만|민원|항의|complaint',
 'change':r'예약.{0,12}(변경|취소)|reschedule|cancel.{0,12}booking',
 'booking':r'예약|일정|booking|appointment',
 'quote':r'견적|제안서|quotation|estimate',
 'price':r'가격|금액|비용|얼마|price|cost',
 'purchase':r'구매|결제|주문|purchase|payment|order',
 'location':r'위치|주소|영업시간|location|address|hours',
}
def default_policy():
    return {'tasks':{},'blocked_terms':[],'urgent_terms':[],'schedule':{'enabled':False,'days':[0,1,2,3,4],'start':'09:00','end':'18:00'},'checked_tasks':[]}

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS workflow_policy(ws TEXT NOT NULL,agent TEXT NOT NULL,config TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS archived_brand(ws TEXT NOT NULL,agent TEXT NOT NULL,created INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS answer_issue(id TEXT PRIMARY KEY,ws TEXT NOT NULL,thread TEXT NOT NULL,message TEXT NOT NULL,agent TEXT NOT NULL,note TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,message));
        CREATE TABLE IF NOT EXISTS answer_context(ws TEXT NOT NULL,message TEXT NOT NULL,agent TEXT NOT NULL,context TEXT NOT NULL,PRIMARY KEY(ws,message));
        CREATE TABLE IF NOT EXISTS workflow_reminder(ws TEXT NOT NULL,message TEXT NOT NULL,created INTEGER NOT NULL,PRIMARY KEY(ws,message));
        """)
init()
def get_policy(c,ws,agent):
    r=one(c,'SELECT config FROM workflow_policy WHERE ws=? AND agent=?',(ws,agent))
    return loads(r['config']) if r else default_policy()
def valid_policy(body):
    from app import require
    p=default_policy();tasks=body.get('tasks',{});require(isinstance(tasks,dict) and set(tasks)<=set(TASKS)|{'general'} and all(v in ('auto','staff','off') for v in tasks.values()),'업무 권한 오류',422);p['tasks']=tasks
    for key in ('blocked_terms','urgent_terms'):
        values=body.get(key,[]);require(isinstance(values,list) and len(values)<=30 and all(isinstance(x,str) and 1<=len(x.strip())<=80 for x in values),'키워드는 최대 30개',422);p[key]=list(dict.fromkeys(x.strip() for x in values))
    sch=body.get('schedule',p['schedule']);require(isinstance(sch,dict) and type(sch.get('enabled')) is bool,'시간대 설정 오류',422)
    days=sch.get('days');start=sch.get('start');end=sch.get('end')
    require(isinstance(days,list) and all(type(x) is int and 0<=x<=6 for x in days) and isinstance(start,str) and isinstance(end,str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',start) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',end) and start<end,'같은 날 시작·종료 시간과 요일을 확인하세요.',422)
    p['schedule']={'enabled':sch['enabled'],'days':sorted(set(days)),'start':start,'end':end}
    checks=body.get('checked_tasks',[]);require(isinstance(checks,list) and all(isinstance(x,str) and x in set(TASKS)|{'general'} for x in checks),'점검 업무 오류',422);p['checked_tasks']=list(dict.fromkeys(checks))
    return p

def decision(p,msg,settings,at=None):
    """Conservative deterministic routing. A keyword hit is not an AI classification."""
    lower=msg.casefold()
    if any(x.casefold() in lower for x in p['blocked_terms']):return 'staff','restricted'
    if any(x.casefold() in lower for x in p['urgent_terms']):return 'staff','urgent'
    # All matching task restrictions apply, not just the first keyword hit.
    categories=[k for k,pat in TASKS.items() if re.search(pat,msg,re.I)] or ['general']
    modes=[p['tasks'].get(k,'auto') for k in categories]
    if 'off' in modes:return 'off','task'
    if 'staff' in modes:return 'staff','task'
    sch=p['schedule']
    if sch['enabled']:
        at=at or datetime.now(ZoneInfo(settings.get('timezone','Asia/Seoul')))
        if at.weekday() not in sch['days'] or not sch['start']<=at.strftime('%H:%M')<sch['end']:return 'staff','schedule'
    return 'auto',''

def register(app,ident):
    from app import require,bounded,visitor,limit
    import branding,ops
    def owner_brand(c,ws,agent):return branding.owned_agent(c,getw(c,ws),agent)
    @app.get('/api/workflow')
    def get(agent:str='',ws=Depends(ident)):
        with db() as c:
            owner_brand(c,ws,agent);return get_policy(c,ws,agent)
    @app.post('/api/workflow')
    def save(body:dict,ws=Depends(ident)):
        agent=body.get('agent','');p=valid_policy(body)
        with db(True) as c:
            owner_brand(c,ws,agent);c.execute('INSERT INTO workflow_policy VALUES(?,?,?,?) ON CONFLICT(ws,agent) DO UPDATE SET config=excluded.config,updated=excluded.updated',(ws,agent,dump(p),now()))
        return p
    @app.post('/api/workflow/archive')
    def archive(body:dict,ws=Depends(ident)):
        agent=body.get('agent','');archived=body.get('archived');require(bool(agent) and type(archived) is bool and body.get('confirmed') is True,'브랜드 및 확인 필요',422)
        with db(True) as c:
            a=owner_brand(c,ws,agent);require(a,'추가 브랜드 필요',422)
            require(not one(c,"SELECT r.client FROM request r JOIN thread t ON t.ws=r.ws AND t.id=r.thread JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE r.ws=? AND v.agent=? AND r.state='running'",(ws,agent)),'상담 처리 완료 후 변경하세요.',409)
            if archived:
                c.execute('INSERT INTO archived_brand VALUES(?,?,?) ON CONFLICT(ws,agent) DO NOTHING',(ws,agent,now()));c.execute('UPDATE agent_profile SET enabled=0 WHERE ws=? AND id=?',(ws,agent))
            else:c.execute('DELETE FROM archived_brand WHERE ws=? AND agent=?',(ws,agent))
        return {'archived':archived,'enabled':False,'billing_changed':False}
    @app.get('/api/workflow/backup')
    def backup(agent:str='',ws=Depends(ident)):
        with db() as c:
            a=owner_brand(c,ws,agent);w=getw(c,ws)
            published=loads(a['published'] if a else w['published']);faq=loads(a['faq']) if a else rows(c,'SELECT q,a FROM faq WHERE ws=?',(ws,))
            versions=rows(c,'SELECT content,created FROM agent_knowledge_version WHERE ws=? AND agent=? ORDER BY created DESC LIMIT 100',(ws,agent)) if a else rows(c,'SELECT content,created FROM knowledge_version WHERE ws=? ORDER BY created DESC LIMIT 100',(ws,))
            # Export approved education only, not conversation transcripts, tokens or raw uploads.
            return {'format':'csai-knowledge-v1','brand':branding.brand_settings(w,a)['brand'],'exported_at':now(),'published':published,'faq':faq,'versions':[{'created':v['created'],'content':loads(v['content'])} for v in versions]}
    @app.get('/api/workflow/queue')
    def queue(agent:str='',ws=Depends(ident)):
        with db() as c:
            owner_brand(c,ws,agent);w=getw(c,ws);cutoff=history_cutoff(w)
            base=" FROM thread t JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE t.ws=? AND COALESCE(v.agent,'')=? AND t.kind<>'test' AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id)"
            overdue=rows(c,"SELECT t.id,t.status,t.manual,t.created,(SELECT MAX(m.created) FROM message m WHERE m.ws=t.ws AND m.thread=t.id AND m.role='user') last_customer"+base+" AND t.status<>'resolved' AND EXISTS(SELECT 1 FROM message m WHERE m.ws=t.ws AND m.thread=t.id AND m.role='user' AND m.created>=?) ORDER BY t.created LIMIT 100",(ws,agent,cutoff))
            # Count a waiting customer only if latest customer message has no newer staff/AI reply.
            waiting=[]
            for t in overdue:
                last=one(c,'SELECT role,created FROM message WHERE ws=? AND thread=? ORDER BY rowid DESC LIMIT 1',(ws,t['id']))
                if last and last['role']=='user' and last['created']<=now()-1800:
                    urgency=one(c,"SELECT id FROM event_log WHERE ws=? AND kind='handoff_urgent' AND ref=?",(ws,t['id']))
                    waiting.append({'id':t['id'],'minutes':(now()-last['created'])//60,'urgent_keyword':bool(urgency)})
            issues=rows(c,"SELECT i.id,i.thread,i.note,i.state,i.created FROM answer_issue i JOIN thread t ON t.ws=i.ws AND t.id=i.thread WHERE i.ws=? AND i.agent=? AND i.state='open' AND i.created>=? ORDER BY i.created DESC LIMIT 50",(ws,agent,cutoff))
            return {'waiting':waiting,'issues':issues,'threshold_minutes':30}
    def create_issue(c,v,t,note):
        w=getw(c,v['ws']);require(thread_accessible(c,w,t['id']),'보관 기간 초과',404)
        require(not one(c,'SELECT thread FROM demo_sample WHERE ws=? AND thread=?',(v['ws'],t['id'])),'샘플 제외',409)
        m=one(c,"SELECT id FROM message WHERE ws=? AND thread=? AND role='assistant' ORDER BY rowid DESC LIMIT 1",(v['ws'],t['id']));require(m,'신고할 AI 답변 없음',409)
        i=uid();c.execute('INSERT INTO answer_issue VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(ws,message) DO NOTHING',(i,v['ws'],t['id'],m['id'],v.get('agent',''),note,'open',now()))
        return {'ok':True}
    @app.post('/api/customer/answer-issue')
    def customer_issue(body:dict):
        token=bounded(body.get('token',''),100);limit('answer-issue:'+token,5,60)
        with db(True) as c:
            v=visitor(c,token,kind='public');branding.merged(c,getw(c,v['ws']),v);t=one(c,'SELECT id FROM thread WHERE ws=? AND visitor=?',(v['ws'],token));require(t,'상담 없음',404)
            return create_issue(c,v,t,ai.clean(bounded(body.get('note',''),500)))
    @app.post('/api/workflow/answer-issue')
    def owner_issue(body:dict,ws=Depends(ident)):
        with db(True) as c:
            t=one(c,'SELECT id,visitor FROM thread WHERE ws=? AND id=?',(ws,body.get('thread')));require(t,'상담 없음',404)
            v=one(c,'SELECT * FROM visitor WHERE ws=? AND token=?',(ws,t['visitor']));require(v,'상담 없음',404);owner_brand(c,ws,v.get('agent',''))
            return create_issue(c,v,t,ai.clean(bounded(body.get('note',''),500)))
    @app.get('/api/workflow/answer-issue/{i}/education')
    def issue_education(i:str,ws=Depends(ident)):
        with db() as c:
            w=getw(c,ws);r=one(c,'SELECT * FROM answer_issue WHERE ws=? AND id=?',(ws,i))
            require(r and thread_accessible(c,w,r['thread']),'신고 없음 또는 보관 범위 초과',404);owner_brand(c,ws,r['agent'])
            m=one(c,"SELECT rowid AS sequence,body FROM message WHERE ws=? AND id=? AND thread=? AND role='assistant'",(ws,r['message'],r['thread']))
            require(m,'기존 답변 없음',404)
            q=one(c,"SELECT body FROM message WHERE ws=? AND thread=? AND role='user' AND rowid<? ORDER BY rowid DESC LIMIT 1",(ws,r['thread'],m['sequence']))
            require(q,'질문 없음',404)
            return {'agent':r['agent'],'question':ai.clean(q['body']),'previous':ai.clean(m['body']),'note':r['note']}
    @app.post('/api/workflow/answer-issue/{i}/resolve')
    def resolve_issue(i:str,ws=Depends(ident)):
        with db(True) as c:
            r=one(c,'SELECT agent FROM answer_issue WHERE ws=? AND id=?',(ws,i));require(r,'신고 없음',404);owner_brand(c,ws,r['agent']);c.execute("UPDATE answer_issue SET state='resolved' WHERE ws=? AND id=?",(ws,i))
        return {'ok':True}
    @app.get('/api/workflow/answer-context/{message}')
    def context(message:str,ws=Depends(ident)):
        with db() as c:
            w=getw(c,ws);m=one(c,'SELECT thread FROM message WHERE ws=? AND id=?',(ws,message));require(m and thread_accessible(c,w,m['thread']),'답변 없음 또는 조회 범위 초과',404)
            r=one(c,'SELECT agent,context FROM answer_context WHERE ws=? AND message=?',(ws,message))
            if not r:return {'available':False}
            owner_brand(c,ws,r['agent']);return {'available':True,'context':loads(r['context'])}


def tick_reminders():
    """Optional worker. One internal event per unanswered customer message."""
    import ops,branding
    with db(True) as c:
        candidates=rows(c,"SELECT t.ws,t.id,t.visitor,m.id AS message,m.created FROM thread t JOIN message m ON m.ws=t.ws AND m.thread=t.id WHERE t.kind<>'test' AND t.status<>'resolved' AND m.role='user' AND m.created>=? AND m.created<=? AND m.rowid=(SELECT MAX(last.rowid) FROM message last WHERE last.ws=t.ws AND last.thread=t.id) AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id) AND NOT EXISTS(SELECT 1 FROM workflow_reminder r WHERE r.ws=t.ws AND r.message=m.id) ORDER BY m.created LIMIT 100",(now()-86400,now()-1800))
        for r in candidates:
            w=getw(c,r['ws'])
            if not w or not public_access(w) or 'new_alert' not in entitlements(w):continue
            v=one(c,'SELECT agent FROM visitor WHERE ws=? AND token=?',(r['ws'],r['visitor']))
            if v and v['agent']:
                a=one(c,'SELECT * FROM agent_profile WHERE ws=? AND id=?',(r['ws'],v['agent']))
                if not branding.agent_allowed(w,a) or not a['enabled']:continue
            elif not w['enabled']:continue
            cur=c.execute('INSERT INTO workflow_reminder VALUES(?,?,?) ON CONFLICT(ws,message) DO NOTHING',(r['ws'],r['message'],now()))
            if cur.rowcount:ops.event(c,r['ws'],'unanswered','30분 이상 고객 답변 대기',r['id'])

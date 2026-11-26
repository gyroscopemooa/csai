"""Deterministic quality tools. Private notes are never supplied to models."""
import re
from fastapi import Depends
from store import *
import ai

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS model_usage_brand(usage_id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS quality_rating(ws TEXT NOT NULL,thread TEXT NOT NULL,score INTEGER NOT NULL,created INTEGER NOT NULL,PRIMARY KEY(ws,thread));
        CREATE TABLE IF NOT EXISTS business_rating(ws TEXT NOT NULL,thread TEXT NOT NULL,score INTEGER NOT NULL,created INTEGER NOT NULL,PRIMARY KEY(ws,thread));
        CREATE TABLE IF NOT EXISTS private_brand_note(id TEXT PRIMARY KEY,ws TEXT NOT NULL,agent TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS feature_draft(ws TEXT NOT NULL,agent TEXT NOT NULL,feature TEXT NOT NULL,config TEXT NOT NULL,updated INTEGER NOT NULL,PRIMARY KEY(ws,agent,feature));
        """)
init()
def owned(c,ws,agent):
    from branding import owned_agent
    from app import require
    require(isinstance(agent,str),'브랜드 오류',422)
    return owned_agent(c,getw(c,ws),agent)
def knowledge(c,ws,agent):
    a=owned(c,ws,agent)
    return loads(a['published'] if a else getw(c,ws)['published'])
def norm(s):return re.sub(r'\W+','',str(s)).lower()
def compare_knowledge(old,new):
    prev={norm(f['q']):f for f in old.get('faq',[]) if isinstance(f,dict) and f.get('q')}
    seen={};duplicates=[];conflicts=[];added=[]
    for f in new.get('faq',[]):
        if not isinstance(f,dict) or not f.get('q') or not f.get('a'):continue
        key=norm(f['q'])
        if not key:continue
        earlier=seen.get(key) or prev.get(key)
        if earlier:
            (duplicates if norm(earlier['a'])==norm(f['a']) else conflicts).append({'question':f['q'],'previous':earlier['a'],'proposed':f['a']})
        else:added.append(f['q'])
        seen[key]=f
    old_rules=set(map(norm,old.get('rules',[])))
    return {'added_questions':added,'duplicates':duplicates,'conflicts':conflicts,'duplicate_rules':sum(norm(x) in old_rules for x in new.get('rules',[])),'old_rule_count':len(old.get('rules',[])),'new_rule_count':len(new.get('rules',[])),'style_changed':old.get('style','')!=new.get('style','')}
def staff_batch(c,ws,agent,ids):
    from app import require
    require(isinstance(ids,list) and 1<=len(ids)<=20 and all(isinstance(x,str) for x in ids),'1~20개 상담 선택',422)
    w=getw(c,ws);parts=[]
    for thread in dict.fromkeys(ids):
        t=one(c,"SELECT t.id FROM thread t JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE t.ws=? AND t.id=? AND t.kind<>'test' AND COALESCE(v.agent,'')=? AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id)",(ws,thread,agent))
        require(t and thread_accessible(c,w,thread),'상담 없음 또는 다른 브랜드',404)
        questions=[]
        for m in rows(c,'SELECT role,body FROM message WHERE ws=? AND thread=? AND created>=? ORDER BY rowid',(ws,thread,history_cutoff(w))):
            if m['role']=='user':questions.append(m['body'])
            elif m['role']=='assistant':questions=[]
            elif m['role']=='staff' and questions:
                parts.append('고객: '+'\n'.join(questions)+'\n담당자: '+m['body']);questions=[]
    text=ai.clean('\n\n'.join(parts));require(text and len(text)<=30000,'담당자 답변이 없거나 30,000자 초과',422)
    return {'text':text,'pairs':len(parts),'agent':agent}
DRAFT_FIELDS={'calendar':['운영 시간','소요 시간'],'auto_booking':['승인 기준','소요 시간'],'crm':['수집 항목','처리 단계'],'quote':['견적 양식','승인 기준'],'widget':['배치 위치','첫 인사'],'design':['테마','색상'],'multilingual':['지원 언어']}
def register(app,ident):
    from app import require,bounded,visitor,limit
    @app.get('/api/quality/overview')
    def overview(agent:str='',ws=Depends(ident)):
        with db() as c:
            pub=knowledge(c,ws,agent);w=getw(c,ws);since=max(now()-30*86400,history_cutoff(w))
            scope=" FROM thread t JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE t.ws=? AND t.kind<>'test' AND COALESCE(v.agent,'')=? AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id)"
            args=(ws,agent)
            counts=one(c,"SELECT COUNT(*) n,COALESCE(SUM(CASE WHEN t.status='resolved' THEN 1 ELSE 0 END),0) resolved,COALESCE(SUM(t.manual),0) manual"+scope+" AND t.created>=?",args+(since,))
            unknown=rows(c,"SELECT u.q FROM unknown u JOIN thread t ON t.id=u.thread AND t.ws=u.ws JOIN visitor v ON v.token=t.visitor AND v.ws=t.ws WHERE u.ws=? AND COALESCE(v.agent,'')=? AND u.created>=? AND u.status='open' AND t.kind<>'test' AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id) ORDER BY u.created DESC LIMIT 1000",args+(since,))
            groups={}
            for r in unknown:
                q=ai.clean(r['q']);key=norm(q)
                if key:
                    if key not in groups:groups[key]={'question':q,'count':0}
                    groups[key]['count']+=1
            ratings=one(c,"SELECT COUNT(*) n,AVG(r.score) average FROM quality_rating r JOIN thread t ON t.ws=r.ws AND t.id=r.thread JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE r.ws=? AND COALESCE(v.agent,'')=? AND r.created>=?",args+(since,))
            staff=rows(c,"SELECT t.id,t.created"+scope+" AND EXISTS(SELECT 1 FROM message m WHERE m.ws=t.ws AND m.thread=t.id AND m.role='staff' AND m.created>=?) ORDER BY t.created DESC LIMIT 50",args+(since,))
            business_ratings=one(c,"SELECT COUNT(*) n,AVG(r.score) average FROM business_rating r JOIN thread t ON t.ws=r.ws AND t.id=r.thread JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE r.ws=? AND COALESCE(v.agent,'')=? AND r.created>=?",args+(since,))
            return {'business_ratings':business_ratings,'days':30,'threads':counts['n'],'resolved':counts['resolved'],'manual':counts['manual'],'unknown_count':len(unknown),'unknown_count_capped':len(unknown)==1000,'suggestions':sorted(groups.values(),key=lambda x:-x['count'])[:20],'ratings':ratings,'staff_threads':staff,'knowledge':{'faq':len(pub.get('faq',[])),'rules':len(pub.get('rules',[]))}}
    @app.post('/api/quality/staff-source')
    def batch(body:dict,ws=Depends(ident)):
        require(body.get('consent') is True,'교육 자료 이용 확인 필요',422)
        with db() as c:
            agent=body.get('agent','');owned(c,ws,agent);return staff_batch(c,ws,agent,body.get('threads'))
    @app.post('/api/customer/feedback')
    def feedback(body:dict):
        score=body.get('score');business=body.get('business_score');require(score is not None or business is not None,'평가 점수 필요',422);require(all(type(x) is int and 1<=x<=5 for x in (score,business) if x is not None),'평가 점수 오류',422)
        token=bounded(body.get('token',''),100);limit('feedback:'+token,5,60)
        with db(True) as c:
            v=visitor(c,token,kind='public');t=one(c,'SELECT id FROM thread WHERE ws=? AND visitor=?',(v['ws'],token))
            require(t and one(c,"SELECT id FROM message WHERE ws=? AND thread=? AND role IN ('staff','assistant')",(v['ws'],t['id'])),'평가할 답변이 없습니다.',409)
            require(not one(c,'SELECT thread FROM demo_sample WHERE ws=? AND thread=?',(v['ws'],t['id'])),'샘플 평가 불가',409)
            if score is not None:c.execute('INSERT INTO quality_rating VALUES(?,?,?,?) ON CONFLICT(ws,thread) DO UPDATE SET score=excluded.score,created=excluded.created',(v['ws'],t['id'],score,now()))
            if business is not None:c.execute('INSERT INTO business_rating VALUES(?,?,?,?) ON CONFLICT(ws,thread) DO UPDATE SET score=excluded.score,created=excluded.created',(v['ws'],t['id'],business,now()))
        return {'ok':True}
    @app.get('/api/quality/training/{job}/compare')
    def training_compare(job:str,ws=Depends(ident)):
        with db() as c:
            j=one(c,'SELECT source,result,state FROM training WHERE ws=? AND id=?',(ws,job));require(j and j['state']=='review' and j['result'],'검토할 교육 결과 없음',404)
            return compare_knowledge(knowledge(c,ws,loads(j['source']).get('agent','')),loads(j['result']))
    @app.get('/api/quality/version/{version}/compare')
    def version_compare(version:str,agent:str='',ws=Depends(ident)):
        with db() as c:
            old=knowledge(c,ws,agent)
            v=one(c,'SELECT content FROM agent_knowledge_version WHERE ws=? AND id=? AND agent=?',(ws,version,agent)) if agent else one(c,'SELECT content FROM knowledge_version WHERE ws=? AND id=?',(ws,version))
            require(v,'교육 버전 없음',404);return compare_knowledge(old,loads(v['content']))
    @app.get('/api/quality/private-notes')
    def notes(agent:str='',ws=Depends(ident)):
        with db() as c:
            owned(c,ws,agent);return rows(c,'SELECT id,body,created FROM private_brand_note WHERE ws=? AND agent=? ORDER BY created DESC LIMIT 100',(ws,agent))
    @app.post('/api/quality/private-notes')
    def note_create(body:dict,ws=Depends(ident)):
        agent=body.get('agent','');content=bounded(body.get('body',''),4000);require(content,'메모 필요',422)
        with db(True) as c:
            owned(c,ws,agent);require(one(c,'SELECT COUNT(*) n FROM private_brand_note WHERE ws=? AND agent=?',(ws,agent))['n']<100,'최대 100개',422);i=uid();c.execute('INSERT INTO private_brand_note VALUES(?,?,?,?,?)',(i,ws,agent,content,now()))
        return {'id':i}
    @app.delete('/api/quality/private-notes/{i}')
    def note_delete(i:str,ws=Depends(ident)):
        with db(True) as c:c.execute('DELETE FROM private_brand_note WHERE ws=? AND id=?',(ws,i))
        return {'ok':True}
    @app.get('/api/quality/feature-draft/{feature}')
    def draft_get(feature:str,agent:str='',ws=Depends(ident)):
        require(feature in ADD,'기능 오류',422)
        with db() as c:
            owned(c,ws,agent);r=one(c,'SELECT config FROM feature_draft WHERE ws=? AND agent=? AND feature=?',(ws,agent,feature))
            return {'fields':DRAFT_FIELDS.get(feature,['설정 메모']),'config':loads(r['config']) if r else {}}
    @app.post('/api/quality/feature-draft/{feature}')
    def draft_save(feature:str,body:dict,ws=Depends(ident)):
        require(feature in ADD,'기능 오류',422);agent=body.get('agent','');config=body.get('config')
        require(isinstance(config,dict) and set(config)<=set(DRAFT_FIELDS.get(feature,['설정 메모'])) and all(isinstance(x,str) and len(x)<=500 for x in config.values()),'미리 설정 형식 오류',422)
        with db(True) as c:
            owned(c,ws,agent);c.execute('INSERT INTO feature_draft VALUES(?,?,?,?,?) ON CONFLICT(ws,agent,feature) DO UPDATE SET config=excluded.config,updated=excluded.updated',(ws,agent,feature,dump({k:ai.clean(v) for k,v in config.items()}),now()))
        return {'ok':True,'activated':False}
    @app.get('/api/quality/brand-metrics')
    def brand_metrics(ws=Depends(ident)):
        with db() as c:
            w=getw(c,ws);require('stats' in entitlements(w),'통계 기능 구매 필요',403);since=now()-30*86400
            return rows(c,"SELECT COALESCE(v.agent,'') agent,COUNT(*) threads,SUM(CASE WHEN t.status='resolved' THEN 1 ELSE 0 END) resolved FROM thread t LEFT JOIN visitor v ON v.token=t.visitor AND v.ws=t.ws WHERE t.ws=? AND t.kind<>'test' AND t.created>=? AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id) GROUP BY COALESCE(v.agent,'')",(ws,since))

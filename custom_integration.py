"""Paid custom external workflow bridge. Staff explicitly approve work, external
workers poll with scoped keys. No arbitrary outbound URLs or automatic side effects."""
import hashlib,hmac,re
from fastapi import Depends,Request
from app import app,ident,require,bounded
from store import *
from developer_api import authorize

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS custom_workflow(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),name TEXT NOT NULL,description TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS custom_job(id TEXT PRIMARY KEY,ws TEXT NOT NULL REFERENCES workspace(id),workflow TEXT NOT NULL REFERENCES custom_workflow(id),work TEXT NOT NULL,payload TEXT NOT NULL,state TEXT NOT NULL,claim_hash TEXT NOT NULL DEFAULT '',key_id TEXT NOT NULL DEFAULT '',result TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL,updated INTEGER NOT NULL,UNIQUE(ws,workflow,work));
        """)
init()

def access(c,ws):
    require({'custom_integration','external_api'}.issubset(entitlements(getw(c,ws))),'맞춤 외부 업무 API 및 외부 API 이용권 필요',403)
def public_job(row):
    return {k:row[k] for k in ('id','workflow','work','state','created','updated')}|{'payload':loads(row['payload']),'result':row['result']}

@app.get('/api/custom-workflows')
def workflows(ws=Depends(ident)):
    with db() as c:
        access(c,ws)
        return {'workflows':rows(c,'SELECT id,name,description,active,created FROM custom_workflow WHERE ws=? ORDER BY created DESC',(ws,)),'jobs':[public_job(x) for x in rows(c,'SELECT * FROM custom_job WHERE ws=? ORDER BY created DESC LIMIT 200',(ws,))]}
@app.post('/api/custom-workflows')
def create_workflow(body:dict,ws=Depends(ident)):
    name=bounded(body.get('name',''),100);description=bounded(body.get('description',''),1000);require(name,'업무명 필요',422)
    with db(True) as c:
        access(c,ws);require(one(c,'SELECT count(*) n FROM custom_workflow WHERE ws=?',(ws,))['n']<30,'최대 30개',409)
        i=uid();c.execute('INSERT INTO custom_workflow VALUES(?,?,?,?,1,?)',(i,ws,name,description,now()))
    return {'id':i}
@app.post('/api/custom-workflows/{i}/disable')
def disable_workflow(i:str,ws=Depends(ident)):
    with db(True) as c:
        access(c,ws);require(one(c,'SELECT id FROM custom_workflow WHERE ws=? AND id=?',(ws,i)),'업무 없음',404)
        c.execute('UPDATE custom_workflow SET active=0 WHERE ws=? AND id=?',(ws,i));c.execute("UPDATE custom_job SET state='cancelled',updated=? WHERE ws=? AND workflow=? AND state='queued'",(now(),ws,i))
    return {'ok':True}
@app.post('/api/custom-jobs')
def create_job(body:dict,ws=Depends(ident)):
    require(body.get('confirmed') is True,'외부 전달 내용 최종 확인 필요',422)
    workflow=bounded(body.get('workflow',''),100);work=bounded(body.get('work',''),100);payload=body.get('payload')
    require(isinstance(payload,dict) and len(payload)<=30 and all(isinstance(k,str) and len(k)<=100 and isinstance(v,(str,int,float,bool,type(None))) for k,v in payload.items()),'단순 JSON 객체만 지원',422)
    require(len(dump(payload))<=10000,'전달 데이터 최대 10000자',422)
    with db(True) as c:
        access(c,ws);w=getw(c,ws);row=one(c,'SELECT kind FROM work WHERE ws=? AND id=? AND NOT EXISTS(SELECT 1 FROM work_brand b WHERE b.ws=work.ws AND b.work=work.id)',(ws,work))
        require(row and row['kind'] in entitlements(w),'업무 권한 없음',404)
        require(one(c,'SELECT id FROM custom_workflow WHERE ws=? AND id=? AND active=1',(ws,workflow)),'활성 업무 없음',404)
        old=one(c,'SELECT * FROM custom_job WHERE ws=? AND workflow=? AND work=?',(ws,workflow,work))
        if old:return public_job(old)
        i=uid();c.execute("INSERT INTO custom_job(id,ws,workflow,work,payload,state,created,updated) VALUES(?,?,?,?,?,'queued',?,?)",(i,ws,workflow,work,dump(payload),now(),now()))
        return public_job(one(c,'SELECT * FROM custom_job WHERE id=?',(i,)))
@app.post('/api/custom-jobs/{i}/cancel')
def cancel_job(i:str,ws=Depends(ident)):
    with db(True) as c:
        access(c,ws);row=one(c,'SELECT state FROM custom_job WHERE ws=? AND id=?',(ws,i));require(row and row['state']=='queued','외부 실행 전에만 취소 가능',409)
        c.execute("UPDATE custom_job SET state='cancelled',updated=? WHERE ws=? AND id=?",(now(),ws,i))
    return {'ok':True}

def key_active(c,k):
    access(c,k['ws']);require(one(c,'SELECT id FROM developer_key WHERE ws=? AND id=? AND revoked=0',(k['ws'],k['id'])),'API 키 폐기됨',401)

@app.get('/v1/custom/jobs')
def queued(req:Request):
    k=authorize(req,'custom:jobs')
    with db() as c:
        key_active(c,k);return rows(c,"SELECT j.id,j.workflow,j.work,j.created,w.name FROM custom_job j JOIN custom_workflow w ON w.id=j.workflow AND w.ws=j.ws WHERE j.ws=? AND j.state='queued' AND w.active=1 ORDER BY j.created LIMIT 30",(k['ws'],))
@app.post('/v1/custom/jobs/{i}/claim')
def claim(i:str,req:Request):
    k=authorize(req,'custom:jobs');token=secrets.token_urlsafe(24);digest=hashlib.sha256(token.encode()).hexdigest()
    with db(True) as c:
        key_active(c,k);row=one(c,"SELECT j.* FROM custom_job j JOIN custom_workflow w ON w.id=j.workflow AND w.ws=j.ws WHERE j.id=? AND j.ws=? AND j.state='queued' AND w.active=1",(i,k['ws']))
        require(row,'실행 대기 업무 없음',409)
        c.execute("UPDATE custom_job SET state='claimed',claim_hash=?,key_id=?,updated=? WHERE id=? AND ws=?",(digest,k['id'],now(),i,k['ws']))
        return public_job(one(c,'SELECT * FROM custom_job WHERE id=?',(i,)))|{'claim_token':token}
@app.post('/v1/custom/jobs/{i}/complete')
def complete(i:str,body:dict,req:Request):
    k=authorize(req,'custom:jobs');token=bounded(body.get('claim_token',''),100);state=body.get('state');result=bounded(body.get('result',''),2000)
    require(state in ('completed','failed'),'실행 결과 상태 오류',422)
    with db(True) as c:
        key_active(c,k);row=one(c,'SELECT * FROM custom_job WHERE ws=? AND id=? AND key_id=?',(k['ws'],i,k['id']))
        require(row and hmac.compare_digest(row['claim_hash'],hashlib.sha256(token.encode()).hexdigest()),'실행권한 없음',403)
        if row['state'] in ('completed','failed'):
            require(row['state']==state and row['result']==result,'이미 기록된 실행 결과와 다름',409);return public_job(row)
        require(row['state']=='claimed','실행 중인 업무 없음',409)
        c.execute('UPDATE custom_job SET state=?,result=?,updated=? WHERE ws=? AND id=?',(state,result,now(),k['ws'],i))
        return public_job(one(c,'SELECT * FROM custom_job WHERE id=?',(i,)))

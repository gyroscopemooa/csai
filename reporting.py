"""Aggregate reporting from real workspace records; no AI-generated metrics."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from fastapi import Depends
from app import app,ident,require
from store import *

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS report_config(ws TEXT PRIMARY KEY,frequency TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS report_history(id TEXT PRIMARY KEY,ws TEXT NOT NULL,period TEXT NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,summary TEXT NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,period));
        """)
init()

def summarize(c,ws,start,end):
    t=rows(c,"SELECT kind,status,COUNT(*) n FROM thread WHERE ws=? AND created>=? AND created<? GROUP BY kind,status",(ws,start,end))
    m=rows(c,"SELECT m.role,COUNT(*) n FROM message m JOIN thread t ON t.id=m.thread AND t.ws=m.ws WHERE m.ws=? AND m.created>=? AND m.created<? AND t.kind<>'test' GROUP BY m.role",(ws,start,end))
    u=one(c,"SELECT COUNT(*) n FROM unknown u JOIN thread t ON t.id=u.thread AND t.ws=u.ws WHERE u.ws=? AND u.created>=? AND u.created<? AND t.kind<>'test'",(ws,start,end))['n']
    b=rows(c,"SELECT status,COUNT(*) n FROM booking WHERE ws=? AND created>=? AND created<? AND status NOT IN ('draft','superseded') GROUP BY status",(ws,start,end))
    work=rows(c,"SELECT kind,status,COUNT(*) n FROM work WHERE ws=? AND created>=? AND created<? GROUP BY kind,status",(ws,start,end))
    public=[r for r in t if r['kind']!='test']
    return {'threads':sum(x['n'] for x in public),'resolved':sum(x['n'] for x in public if x['status']=='resolved'),'unknown':u,'messages':sum(x['n'] for x in m),'channels':public,'roles':m,'bookings':b,'work':work}

def periods(ws,c,freq):
    s=loads(getw(c,ws)['settings'])
    tz=ZoneInfo(s.get('timezone','Asia/Seoul'));d=datetime.now(tz).replace(hour=0,minute=0,second=0,microsecond=0)
    if freq=='weekly':
        d=d-timedelta(days=d.weekday());begin=d-timedelta(days=7)
    else:begin=d-timedelta(days=1)
    return int(begin.timestamp()),int(d.timestamp()),freq+':'+begin.date().isoformat()

@app.get('/api/analytics')
def analytics(days:int=30,ws=Depends(ident)):
    require(days in (7,30,90),'기간은 7, 30, 90일 중 선택',422)
    with db() as c:
        w=getw(c,ws);require('stats' in entitlements(w))
        tz=ZoneInfo(loads(w['settings']).get('timezone','Asia/Seoul'));end=datetime.now(tz);today=end.replace(hour=0,minute=0,second=0,microsecond=0);start=today-timedelta(days=days-1)
        out=summarize(c,ws,int(start.timestamp()),int(end.timestamp())+1)
        daily=[]
        for i in range(days):
            a=start+timedelta(days=i);z=a+timedelta(days=1)
            count=one(c,"SELECT COUNT(*) n FROM thread WHERE ws=? AND kind<>'test' AND created>=? AND created<?",(ws,int(a.timestamp()),int(z.timestamp())))['n']
            daily.append({'date':a.date().isoformat(),'threads':count})
        return out|{'daily':daily,'days':days,'remaining':remaining(c,w)}

@app.get('/api/reports')
def reports(ws=Depends(ident)):
    with db() as c:
        require('report' in entitlements(getw(c,ws)))
        cfg=one(c,'SELECT frequency,enabled FROM report_config WHERE ws=?',(ws,)) or {'frequency':'daily','enabled':0}
        return {'settings':cfg,'worker_enabled':os.getenv('ENABLE_AUTO_REPORTS')=='1','reports':[dict(r,summary=loads(r['summary'])) for r in rows(c,'SELECT * FROM report_history WHERE ws=? ORDER BY end DESC LIMIT 60',(ws,))]}

@app.post('/api/reports/settings')
def settings(body:dict,ws=Depends(ident)):
    f=body.get('frequency');require(f in ('daily','weekly'),'리포트 주기 오류',422)
    with db(True) as c:
        require('report' in entitlements(getw(c,ws)));c.execute('INSERT INTO report_config VALUES(?,?,?,?) ON CONFLICT(ws) DO UPDATE SET frequency=excluded.frequency,enabled=excluded.enabled,created=excluded.created',(ws,f,int(body.get('enabled') is True),now()))
    return {'ok':True}

def generate(c,ws,freq):
    a,b,key=periods(ws,c,freq);old=one(c,'SELECT * FROM report_history WHERE ws=? AND period=?',(ws,key))
    if old:return dict(old,summary=loads(old['summary']))
    summary=summarize(c,ws,a,b);i=uid();c.execute('INSERT INTO report_history VALUES(?,?,?,?,?,?,?)',(i,ws,key,a,b,dump(summary),now()));c.execute('INSERT INTO event_log VALUES(?,?,?,?,?,0,?)',(uid(),ws,'report','상담 리포트 생성',i,now()))
    return {'id':i,'period':key,'start':a,'end':b,'summary':summary}

@app.post('/api/reports/generate')
def generate_now(ws=Depends(ident)):
    with db(True) as c:
        require('report' in entitlements(getw(c,ws)));cfg=one(c,'SELECT frequency FROM report_config WHERE ws=?',(ws,))
        return generate(c,ws,cfg['frequency'] if cfg else 'daily')

def tick():
    if os.getenv('ENABLE_AUTO_REPORTS')!='1':return 0
    with db() as c:targets=rows(c,'SELECT ws,frequency FROM report_config WHERE enabled=1')
    n=0
    for t in targets:
        with db(True) as c:
            w=getw(c,t['ws'])
            if not w or 'report' not in entitlements(w):continue
            a,b,key=periods(t['ws'],c,t['frequency'])
            if not one(c,'SELECT id FROM report_history WHERE ws=? AND period=?',(t['ws'],key)):
                generate(c,t['ws'],t['frequency']);n+=1
    return n

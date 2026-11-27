"""Read-only operational dashboard using actual scoped records."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from fastapi import Depends
from app import app,ident
from store import *
import ops,brand_calendar,commerce

def count(c,sql,args):
    return one(c,sql,args)['n']

@app.get('/api/business-dashboard')
def dashboard(agent:str='',ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);ops.work_scope(c,w,agent);a=entitlements(w)
        s=brand_calendar.config(c,ws,agent) if agent else loads(w['settings'])
        zone=ZoneInfo(s.get('timezone','Asia/Seoul'));local=datetime.now(zone);start=local.replace(hour=0,minute=0,second=0,microsecond=0);end=start+timedelta(days=1)
        lo,hi=int(start.timestamp()),int(end.timestamp());utc_lo=start.astimezone(timezone.utc).isoformat();utc_hi=end.astimezone(timezone.utc).isoformat()
        base=" FROM thread t JOIN visitor v ON v.ws=t.ws AND v.token=t.visitor WHERE t.ws=? AND COALESCE(v.agent,'')=? AND t.kind<>'test' AND NOT EXISTS(SELECT 1 FROM demo_sample d WHERE d.ws=t.ws AND d.thread=t.id)"
        args=(ws,agent)
        result={'date':local.date().isoformat(),'timezone':str(zone),'new_threads':count(c,'SELECT COUNT(*) n'+base+' AND t.created>=? AND t.created<?',args+(lo,hi)), 'manual_pending':count(c,'SELECT COUNT(*) n'+base+" AND t.manual=1 AND t.status<>'resolved' AND (t.created>=? OR EXISTS(SELECT 1 FROM message m WHERE m.ws=t.ws AND m.thread=t.id AND m.created>=?))",args+(history_cutoff(w),history_cutoff(w))), 'calendar':None,'work':None,'contacts':None,'leads':None,'sales':None}
        if 'calendar' in a:
            if agent:
                bbase=" FROM brand_booking b WHERE b.ws=? AND b.agent=?";ba=args
            else:
                bbase=" FROM booking b WHERE b.ws=? AND NOT EXISTS(SELECT 1 FROM demo_sample_entity d WHERE d.ws=b.ws AND d.kind='booking' AND d.id=b.id)";ba=(ws,)
            active=" AND b.status IN ('confirmed','pending','pending_payment')"
            today=bbase+active+' AND b.start>=? AND b.start<?'
            records=rows(c,'SELECT b.id,b.start,b.end,b.status'+today+' ORDER BY b.start LIMIT 30',ba+(utc_lo,utc_hi))
            pending=count(c,"SELECT COUNT(*) n"+bbase+" AND b.status IN ('pending','pending_payment')",ba)
            changes=0
            if 'change_booking' in a:
                changes=count(c,"SELECT COUNT(*) n FROM brand_booking_change WHERE ws=? AND agent=? AND state='pending'" if agent else "SELECT COUNT(*) n FROM booking_change WHERE ws=? AND state='pending'",ba)
            result['calendar']={'today':count(c,'SELECT COUNT(*) n'+today,ba+(utc_lo,utc_hi)),'pending':pending,'changes':changes,'records':records}
        if a & {'crm','quote','tasks','leads','complaints'}:
            work=rows(c,"SELECT w.kind,COUNT(*) n FROM work w LEFT JOIN work_brand b ON b.ws=w.ws AND b.work=w.id WHERE w.ws=? AND COALESCE(b.agent,'')=? AND w.status<>'resolved' AND NOT EXISTS(SELECT 1 FROM demo_sample_entity d WHERE d.ws=w.ws AND d.kind='work' AND d.id=w.id) GROUP BY w.kind",args)
            result['work']={x['kind']:x['n'] for x in work if x['kind'] in a}
        if 'crm' in a:result['contacts']=count(c,'SELECT COUNT(*) n FROM crm_contact WHERE ws=? AND agent=?',args)
        if 'leads' in a:result['leads']=count(c,"SELECT COUNT(*) n FROM lead_profile l JOIN work w ON w.id=l.work AND w.ws=l.ws LEFT JOIN work_brand b ON b.work=w.id AND b.ws=w.ws WHERE l.ws=? AND COALESCE(b.agent,'')=? AND l.stage IN ('interested','ready') AND w.status<>'resolved'",args)
        if public_access(w) and commerce.enabled(c,ws,agent):
            result['sales']={'orders_today':count(c,'SELECT COUNT(*) n FROM commerce_order WHERE ws=? AND agent=? AND created>=? AND created<?',args+(lo,hi)), 'preparing':count(c,"SELECT COUNT(*) n FROM commerce_order WHERE ws=? AND agent=? AND state IN ('received','preparing')",args),'pending_requests':count(c,"SELECT COUNT(*) n FROM commerce_request WHERE ws=? AND agent=? AND state IN ('pending','review')",args),'recorded_amount':one(c,"SELECT COALESCE(SUM(amount),0) n FROM commerce_order WHERE ws=? AND agent=? AND state<>'cancelled' AND created>=? AND created<?",args+(lo,hi))['n']}
        return result

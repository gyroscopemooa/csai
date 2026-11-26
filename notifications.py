"""Bounded durable email outbox. No real sends unless explicitly enabled.
Claims are serialized in SQLite; ambiguous delivery stays failed for operator review.
"""
from store import *
import httpx
ALLOWED={'unknown':'unknown_alert','booking':'booking_alert','new':'new_alert','report':'report'}

def live_enabled():
    return not DEMO and os.getenv('ENABLE_LIVE_EMAIL','0')=='1' and bool(os.getenv('RESEND_API_KEY') and os.getenv('RESEND_FROM'))

def dispatch(ws, batch=10):
    # Simulate even if real credentials happen to be present in a demo.
    if not DEMO and not live_enabled():return []
    with db(True) as c:
        w=getw(c,ws);a=entitlements(w);cfg=one(c,'SELECT * FROM notification_config WHERE ws=? AND enabled=1',(ws,))
        if not cfg or (not DEMO and (w.get('owner_email') or '').lower()!=cfg['email'].lower()) or 'email' not in a or loads(w['settings'])['modes'].get('email')=='off':return []
        pending=rows(c,"SELECT e.* FROM event_log e LEFT JOIN delivery d ON d.ws=e.ws AND d.event=e.id WHERE e.ws=? AND d.id IS NULL AND e.created>? ORDER BY e.rowid LIMIT 200",(ws,now()-86400))
        pending=[x for x in pending if ALLOWED.get(x['kind']) in a][:batch]
        for x in pending:c.execute('INSERT INTO delivery VALUES(?,?,?,?,?,?)',(uid(),ws,x['id'],'sending','',now()))
    results=[]
    for x in pending:
        status='simulated';error=''
        if live_enabled():
            try:
                # Recheck entitlement and recipient in case settings changed while queued.
                with db() as c:
                    w=getw(c,ws);latest=one(c,'SELECT * FROM notification_config WHERE ws=? AND enabled=1',(ws,))
                    if not latest or latest['email']!=cfg['email'] or (w.get('owner_email') or '').lower()!=cfg['email'].lower() or not {'email',ALLOWED[x['kind']]}.issubset(entitlements(w)) or loads(w['settings'])['modes'].get('email')=='off':raise RuntimeError('알림 설정 변경')
                subject='CS AI 업무 알림';body='새로운 업무 알림이 있습니다.\n관리자 페이지에서 확인: '+APP_URL
                if x['kind']=='report':
                    with db() as c:report=one(c,'SELECT summary,period FROM report_history WHERE ws=? AND id=?',(ws,x['ref']))
                    if report:
                        summary=loads(report['summary']);subject='CS AI 상담 리포트';body='집계 기간: '+report['period']+'\n고객 상담 '+str(summary['threads'])+'건 · 완료 '+str(summary['resolved'])+'건 · 미학습 '+str(summary['unknown'])+'건\n관리자 페이지: '+APP_URL
                r=httpx.post('https://api.resend.com/emails',headers={'Authorization':'Bearer '+os.environ['RESEND_API_KEY'],'Idempotency-Key':'csai-'+x['id']},json={'from':os.environ['RESEND_FROM'],'to':[cfg['email']],'subject':subject,'text':body},timeout=15)
                status='sent' if r.is_success else 'failed';error='' if r.is_success else 'HTTP '+str(r.status_code)
            except Exception:status='failed';error='전송 미확인 또는 설정 변경: 자동 재전송하지 않음'
        elif not DEMO:status='failed';error='발송 비활성화'
        with db(True) as c:c.execute('UPDATE delivery SET status=?,error=? WHERE ws=? AND event=?',(status,error,ws,x['id']))
        results.append({'status':status,'event':x['id']})
    return results

def tick():
    # A process crash after the network call is ambiguous, not a reason to resend.
    with db(True) as c:
        c.execute("UPDATE delivery SET status='failed',error='전송 결과 미확인: 관리자 확인 필요' WHERE status IN ('sending','queued') AND created<?",(now()-1800,))
        ws=rows(c,'SELECT ws FROM notification_config WHERE enabled=1 ORDER BY ws')
    return sum(len(dispatch(x['ws'])) for x in ws)

from test_app import owner, post, patch, public
from fastapi.testclient import TestClient
from app import app
from datetime import datetime,timedelta,timezone
import google_calendar,store

def purchase(*addons):
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':list(addons)});patch(c,{'enabled':True});return c

def workspace(c):
    with store.db() as db:return store.one(db,'SELECT ws FROM session WHERE token=?',(c.cookies.get('csai_session'),))['ws']

def test_calendar_busy_and_stale_fail_closed(monkeypatch):
    c=purchase('google_calendar');ws=workspace(c)
    a=(datetime.now(timezone.utc)+timedelta(days=3)).replace(microsecond=0);b=a+timedelta(hours=1)
    with store.db(True) as db:
        db.execute('INSERT INTO calendar_policy(ws,block_busy,refreshed,horizon) VALUES(?,1,?,?)',(ws,store.now(),store.now()+86400*90))
        db.execute('INSERT INTO calendar_busy VALUES(?,?,?)',(ws,a.isoformat(),b.isoformat()))
    with store.db() as db:
        assert google_calendar.busy_conflict(db,ws,a.isoformat(),b.isoformat())
        assert not google_calendar.busy_conflict(db,ws,b.isoformat(),(b+timedelta(hours=1)).isoformat())
    with store.db(True) as db:db.execute('UPDATE calendar_policy SET refreshed=0 WHERE ws=?',(ws,))
    import pytest
    from fastapi import HTTPException
    with store.db() as db:
        with pytest.raises(HTTPException) as exc:google_calendar.busy_conflict(db,ws,a.isoformat(),b.isoformat())
        assert exc.value.status_code==503

def test_calendar_busy_refresh_ignores_transparent_and_owned(monkeypatch):
    c=purchase('google_calendar');ws=workspace(c)
    with store.db(True) as db:db.execute('INSERT INTO calendar_link VALUES(?,?,?)',(ws,'fake',store.now()))
    monkeypatch.setattr(google_calendar,'access',lambda w:'fake')
    class Reply:
        is_success=True
        def json(self):
            return {'timeZone':'Asia/Seoul','items':[
                {'id':'outside','start':{'date':'2030-01-01'},'end':{'date':'2030-01-02'}},
                {'id':'transparent','transparency':'transparent','start':{'date':'2030-01-01'},'end':{'date':'2030-01-02'}},
                {'id':google_calendar.event_id(ws,'own'),'extendedProperties':{'private':{'csai_workspace':ws,'csai_booking':'own'}},'start':{'date':'2030-01-01'},'end':{'date':'2030-01-02'}}]}
    monkeypatch.setattr(google_calendar,'api',lambda *a,**k:Reply())
    assert google_calendar.refresh_busy(ws)['count']==1
    with store.db() as db:
        assert store.rows(db,'SELECT start,end FROM calendar_busy WHERE ws=?',(ws,))==[{'start':'2029-12-31T15:00:00+00:00','end':'2030-01-01T15:00:00+00:00'}]

def test_crm_contacts_isolated_and_linked():
    c=purchase('crm');other=purchase('crm');u,t=public(c)
    thread=next(x['id'] for x in c.get('/api/inbox').json() if x['kind']=='public')
    r=post(c,'/api/crm/contacts',{'name':'테스트 고객','phone':'010-1234-5678','thread':thread})
    assert c.get('/api/crm/contacts').json()[0]['threads']==[{'thread':thread}]
    assert other.get('/api/crm/contacts').json()==[]
    assert other.patch('/api/crm/contacts/'+r['id'],json={'name':'변경'}).status_code==404
    assert c.delete('/api/crm/contacts/'+r['id']).status_code==200
    assert c.get('/api/inbox/'+thread).status_code==200

def test_lead_automatic_classification_and_entitlement():
    c=purchase('leads');u,t=public(c)
    post(u,'/api/chat',{'token':t,'message':'예약하고 싶어요','clientMessageId':'lead'})
    xs=c.get('/api/leads').json();assert len(xs)==1 and xs[0]['stage']=='ready'
    assert c.patch('/api/leads/'+xs[0]['thread'],json={'stage':'interested'}).status_code==200
    assert c.get('/api/leads').json()[0]['stage']=='interested'
    assert owner().get('/api/leads').status_code==403

def test_quote_server_price_and_confirmed_chat_delivery():
    c=purchase('quote');u,t=public(c)
    req=post(u,'/api/customer/requests',{'token':t,'kind':'quote','title':'촬영','details':'2개','confirmed':True})
    item=post(c,'/api/quotes/items',{'name':'촬영','price':30000})
    offer=post(c,'/api/quotes/offers',{'work':req['id'],'items':[{'id':item['id'],'quantity':2,'price':1}],'note':'예시'})
    assert offer['amount']==60000
    assert c.post('/api/quotes/offers/'+offer['id']+'/send',json={}).status_code==422
    sent=post(c,'/api/quotes/offers/'+offer['id']+'/send',{'confirmed':True});assert sent['status']=='sent'
    post(c,'/api/quotes/offers/'+offer['id']+'/send',{'confirmed':True})
    messages=u.get('/api/session/'+t+'/messages').json()
    assert sum('60,000원' in x['body'] for x in messages)==1

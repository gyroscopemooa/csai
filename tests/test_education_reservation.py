from test_app import owner,post,app
from test_product_access_regression import google_owner
import store
import ai

def ws_id(c):
    with store.db() as d:
        return store.one(d,'SELECT ws FROM session WHERE token=?',(c.cookies.get('csai_session'),))['ws']

def test_expired_or_revoked_trial_does_not_credit_ordinary_wallet(monkeypatch):
    monkeypatch.setattr(store,'OPERATOR_OWNERS',{'google:education-refund-operator'})
    op=google_owner('education-refund-operator')
    c=google_owner('education-refund-trial')
    invitation=post(op,'/api/operator/invites',{'credit_limit':100})
    post(c,'/api/invites/accept',{'code':invitation['code']})
    j=post(c,'/api/training/estimate',{'text':'테스트 질문 => 답변'})
    def fail_after_revoke(*args):
        post(op,'/api/operator/invites/'+invitation['id']+'/revoke',{})
        raise RuntimeError('simulated upstream failure')
    monkeypatch.setattr(ai,'train',fail_after_revoke)
    assert c.post('/api/training/'+j['id']+'/run',json={}).status_code==502
    assert c.get('/api/me').json()['credits']==20
    with store.db() as d:
        r=store.one(d,'SELECT wallet,state,cost FROM education_reservation WHERE id=?',(j['id'],))
        assert r=={'wallet':'trial','state':'settled','cost':0}

def test_ordinary_reservation_settles_once():
    c=owner();ws=ws_id(c)
    with store.db(True) as d:
        w=store.getw(d,ws)
        store.reserve_education(d,w,8,'settle-once-'+ws)
        assert store.getw(d,ws)['credits']==12
        store.settle_education(d,ws,'settle-once-'+ws,3)
        store.settle_education(d,ws,'settle-once-'+ws,3)
        assert store.getw(d,ws)['credits']==17

def test_operator_old_month_refund_does_not_change_new_month(monkeypatch):
    monkeypatch.setattr(store,'OPERATOR_OWNERS',{'google:education-month-operator'})
    c=google_owner('education-month-operator');ws=ws_id(c)
    ref='operator-month-'+ws
    with store.db(True) as d:
        w=store.getw(d,ws);store.reserve_education(d,w,8,ref)
        d.execute("UPDATE operator_wallet SET period='2099-01',credit_used=4,chat_used=6 WHERE ws=?",(ws,))
        store.settle_education(d,ws,ref,0)
        store.refund_chat(d,w,store.month(),'operator')
        x=store.one(d,'SELECT credit_used,chat_used FROM operator_wallet WHERE ws=?',(ws,))
        assert x=={'credit_used':4,'chat_used':6}

def test_chat_persistence_failure_refunds_once(monkeypatch):
    from test_app import patch,public
    import customer_ops
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':[]})
    patch(c,{'enabled':True,'price':'100원'})
    u,token=public(c)
    body={'token':token,'message':'가격은?','clientMessageId':'persistence-failure'}
    original=customer_ops.capture_lead
    def fail(*args):raise RuntimeError('forced persistence failure')
    monkeypatch.setattr(customer_ops,'capture_lead',fail)
    assert u.post('/api/chat',json=body).status_code==502
    assert c.get('/api/me').json()['remaining']==300
    monkeypatch.setattr(customer_ops,'capture_lead',original)
    result=post(u,'/api/chat',body)
    assert result['remaining']==299
    assert post(u,'/api/chat',body)==result
    assert c.get('/api/me').json()['remaining']==299

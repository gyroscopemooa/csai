from test_app import owner,post
from fastapi.testclient import TestClient
from app import app
import store
from store import db,one,uid,now,workspace

def make_google_client(subject):
    c=TestClient(app)
    with db(True) as d:
        w=workspace(d,'google:'+subject);token=uid();d.execute('INSERT INTO session VALUES(?,?,?)',(token,w['id'],now()+3600))
    c.cookies.set('csai_session',token)
    return c

def test_operator_invite_trial_wallet_and_direct_education():
    op=owner()
    # owner is resolved from the authenticated workspace, not an email or request body.
    with db() as d:
        session=one(d,'SELECT * FROM session WHERE token=?',(op.cookies.get('csai_session'),));owner_id=one(d,'SELECT owner FROM workspace WHERE id=?',(session['ws'],))['owner']
    store.OPERATOR_OWNERS.add(owner_id)
    invite=post(op,'/api/operator/invites',{'chat_limit':50,'credit_limit':100,'days':14})
    guest=make_google_client('trial-subject')
    assert post(guest,'/api/invites/accept',{'code':invite['code']})['ok']
    me=guest.get('/api/me').json();assert me['trial']['bookings_remaining']==10 and me['remaining']==50 and me['credits']==100
    job=post(guest,'/api/faq',{'q':'체험 질문','a':'체험 답변'});assert job['requires_run'] and job['maxCredits']>0
    post(guest,'/api/training/'+job['id']+'/run',{});post(guest,'/api/training/'+job['id']+'/publish',{})
    assert guest.get('/api/me').json()['credits']<100
    assert post(op,'/api/operator/invites/'+invite['id']+'/revoke',{})['ok']
    assert guest.get('/api/me').json()['trial'] is None

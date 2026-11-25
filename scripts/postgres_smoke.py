"""Disposable PostgreSQL smoke test. Never run against a real workspace database."""
import os
from urllib.parse import urlsplit
dsn=os.environ.get('DATABASE_URL','')
assert os.environ.get('CSAI_DB_BACKEND')=='postgres'
assert os.environ.get('DEMO_MODE')=='1'
assert os.environ.get('CSAI_DISPOSABLE_DB')=='1'
assert urlsplit(dsn).hostname in ('127.0.0.1','localhost')
assert urlsplit(dsn).path=='/csai_ci'

# Local CI PostgreSQL is configured with SSL. Do not alter production settings here.
from fastapi.testclient import TestClient
from app import app
from store import db,one
c=TestClient(app)
assert c.get('/health').status_code==200
r=c.get('/auth/demo');assert r.status_code==200,r.text
r=c.post('/api/demo/billing',json={'plan':'lite','addons':['calendar','widget']});assert r.status_code==200,r.text
r=c.patch('/api/settings',json={'enabled':True,'price':'100원'});assert r.status_code==200,r.text
me=c.get('/api/me').json();assert me['remaining']==300
u=TestClient(app)
r=u.post('/api/session',json={'slug':me['slug']});assert r.status_code==200,r.text
token=r.json()['token']
body={'token':token,'message':'가격은?','clientMessageId':'smoke'}
r=u.post('/api/chat',json=body);assert r.status_code==200,r.text
assert r.json()['remaining']==299
assert u.post('/api/chat',json=body).json()==r.json()
assert c.get('/api/me').json()['remaining']==299
with db() as d:
    assert one(d,"SELECT count(*) n FROM workspace")['n']>=1
print('PostgreSQL smoke passed: schema, login, purchase, public session, quota, replay.')

from test_app import owner,post,patch,public
from fastapi.testclient import TestClient
from app import app
from openpyxl import load_workbook
from io import BytesIO

def setup(*addons):
    c=owner()
    post(c,'/api/demo/billing',{'plan':'lite','addons':list(addons)})
    patch(c,{'enabled':True,'price':'100원'})
    return c

def test_analytics_actual_public_records_only():
    c=setup('stats')
    u,t=public(c)
    post(u,'/api/chat',{'token':t,'message':'가격은?','clientMessageId':'stats-one'})
    r=c.get('/api/analytics?days=7')
    assert r.status_code==200,r.text
    data=r.json()
    assert data['threads']==1
    assert data['messages']==2
    assert len(data['daily'])==7
    assert owner().get('/api/analytics?days=7').status_code==403

def test_report_generation_idempotent():
    c=setup('report')
    post(c,'/api/reports/settings',{'frequency':'weekly','enabled':True})
    r=post(c,'/api/reports/generate',{})
    same=post(c,'/api/reports/generate',{})
    assert r['id']==same['id']
    assert len(c.get('/api/reports').json()['reports'])==1
    assert owner().get('/api/reports').status_code==403

def test_export_sheets_and_formula_escaping():
    c=setup('crm','export')
    post(c,'/api/crm/contacts',{'name':'=1+1','notes':'  =1+1'})
    r=c.get('/api/export')
    assert r.status_code==200
    b=load_workbook(BytesIO(r.content))
    assert '상담 기록' in b.sheetnames and '고객' in b.sheetnames
    assert b['고객']['B2'].data_type!='f'
    assert b['고객']['E2'].data_type!='f'
    assert '예약' not in b.sheetnames
    assert owner().get('/api/export').status_code==403

def test_extended_api_purchase_scope_and_isolation():
    c=setup('external_api','crm','stats')
    assert c.post('/api/developer/keys',json={'label':'권한 없음','scopes':['quotes:send']}).status_code==403
    key=post(c,'/api/developer/keys',{'label':'CRM 조회','scopes':['crm:read','stats']})
    u=TestClient(app);headers={'Authorization':'Bearer '+key['key']}
    post(c,'/api/crm/contacts',{'name':'내 고객'})
    other=setup('crm')
    post(other,'/api/crm/contacts',{'name':'다른 업체 고객'})
    r=u.get('/v1/crm/contacts',headers=headers)
    assert r.status_code==200
    assert [x['name'] for x in r.json()]==['내 고객']
    assert u.post('/v1/crm/contacts',headers=headers,json={'name':'금지'}).status_code==403
    assert u.get('/v1/analytics?days=7',headers=headers).status_code==200
    post(c,'/api/demo/billing',{'plan':'lite','addons':['external_api']})
    assert u.get('/v1/crm/contacts',headers=headers).status_code==403

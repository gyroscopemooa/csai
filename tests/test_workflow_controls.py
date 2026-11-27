from datetime import datetime
from workflow_controls import default_policy,decision
from test_app import owner,post,patch,public

def test_workflow_decision():
    p=default_policy();p['tasks']={'refund':'staff','price':'auto'}
    assert decision(p,'환불 금액',{})==('staff','task')
    p['blocked_terms']=['계약서'];assert decision(p,'계약서 요청',{})==('staff','restricted')
    p['schedule']={'enabled':True,'days':[0],'start':'09:00','end':'18:00'}
    assert decision(p,'안녕하세요',{},datetime(2026,11,27,10))==('staff','schedule')

def test_policy_handoff_uses_no_ai_quota():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True})
    post(c,'/api/workflow',{'tasks':{'refund':'staff'}})
    u,token=public(c);before=c.get('/api/me').json()['remaining']
    assert post(u,'/api/chat',{'token':token,'message':'환불 문의','clientMessageId':'policy-manual'})['manual']
    assert c.get('/api/me').json()['remaining']==before
    assert owner().get('/api/workflow').json()['tasks']=={}


def test_backup_import_review_only():
    c=owner();before=c.get('/api/me').json()
    backup={'format':'csai-knowledge-v1','published':{'style':'친절','rules':['정확히 답변'],'faq':[{'q':'가격','a':'100원'}]},'faq':[{'q':'영업시간','a':'09:00'}]}
    payload={'backup':backup,'confirmed':True}
    assert c.post('/api/workflow/backup/import',json={'backup':backup}).status_code==422
    r=post(c,'/api/workflow/backup/import',payload)
    assert r['state']=='review' and r['cost']==0 and r['faq_count']==2
    assert c.get('/api/me').json()['published']==before['published']
    assert c.get('/api/me').json()['credits']==before['credits']
    assert owner().post('/api/training/'+r['id']+'/publish',json={}).status_code==409
    post(c,'/api/training/'+r['id']+'/publish',{})
    assert len(c.get('/api/me').json()['published']['faq'])==2
    assert c.get('/api/me').json()['credits']==before['credits']
    backup['faq']=[{'q':'가격','a':'200원'}]
    assert c.post('/api/workflow/backup/import',json=payload).status_code==422
    assert c.post('/api/workflow/backup/import',json={'confirmed':True,'backup':{'format':'bad'}}).status_code==422

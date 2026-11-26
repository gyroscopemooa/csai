from test_app import owner,post
def test_apply_draft_requires_purchase_and_confirmation():
    c=owner()
    post(c,'/api/quality/feature-draft/design',{'config':{'테마':'토스형','색상':'#3182f6'}})
    assert c.get('/api/quality/ready-drafts').json()==[]
    post(c,'/api/demo/billing',{'plan':'lite','addons':['design']})
    d=c.get('/api/quality/ready-drafts').json()[0]
    body={'candidate':d['candidate'],'updated':d['updated']}
    assert c.post('/api/quality/feature-draft/design/apply',json=body).status_code==422
    assert post(c,'/api/quality/feature-draft/design/apply',body|{'confirmed':True})['ok']
    assert c.get('/api/appearance').json()['theme']=='toss'

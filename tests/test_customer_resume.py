from test_app import owner,post,patch,public

def test_resume_opt_in_and_forget():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True})
    u,token=public(c);slug=c.get('/api/me').json()['slug']
    assert not post(u,'/api/customer/resume',{'slug':slug,'action':'load'})['remembered']
    assert post(u,'/api/customer/resume',{'slug':slug,'token':token,'action':'remember'})['remembered']
    assert post(u,'/api/customer/resume',{'slug':slug,'action':'load'})['token']==token
    assert not post(u,'/api/customer/resume',{'slug':slug,'action':'forget'})['remembered']
    assert not post(u,'/api/customer/resume',{'slug':slug,'action':'load'})['remembered']

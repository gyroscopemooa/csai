from test_app import owner,post

def test_kakao_consult_request_modes():
    c=owner();other=owner();path='/api/kakao-consultation/request'
    own={'agent':'','mode':'own_contract','dealer':'dealer','channel_ref':'channel','budget_krw':0,'confirmed':True}
    assert c.post(path,json=own|{'confirmed':False}).status_code==422
    r=post(c,path,own)
    assert r['request']['mode']=='own_contract' and not r['active'] and r['unit_price_krw'] is None
    assert other.get(path).json()['request'] is None
    managed=own|{'mode':'managed_prepaid','dealer':'','budget_krw':10000}
    assert c.post(path,json=managed|{'budget_krw':0}).status_code==422
    r=post(c,path,managed)
    assert r['request']['budget_krw']==10000 and not r['billing_enabled']
    assert c.delete(path).status_code==200
    assert c.get(path).json()['request'] is None

from test_app import owner,post
from integrations import smartstore_transport as smart
import pytest

CSV='channel,reference,product,quantity,amount,state,carrier,tracking\nsmartstore,O1,상품,2,1000,received,,\n'
def test_import_preview_confirm_and_no_duplicate():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]})
    post(c,'/api/commerce/settings',{'enabled':True})
    p=post(c,'/api/commerce/import-orders',{'csv':CSV})
    assert p['new']==1 and p['imported']==0
    assert c.get('/api/commerce').json()['orders']==[]
    assert c.post('/api/commerce/import-orders',json={'csv':CSV,'checksum':'bad','confirmed':True}).status_code==409
    body={'csv':CSV,'checksum':p['checksum'],'confirmed':True}
    assert post(c,'/api/commerce/import-orders',body)['imported']==1
    assert post(c,'/api/commerce/import-orders',body)['duplicates']==1
    assert c.post('/api/commerce/import-orders',json={'csv':CSV+'smartstore,O1,상품,1,1000,received,,\n'}).status_code==422

def test_smartstore_fixed_read_only_probe(monkeypatch):
    monkeypatch.setattr(smart,'signature',lambda *a:'signed')
    calls=[]
    class Resp:
        is_success=True
        def __init__(self,data):self.data=data
        def json(self):return self.data
    def post_(url,**kw):calls.append((url,kw));return Resp({'access_token':'test'})
    def get_(url,**kw):calls.append((url,kw));return Resp({'data':['123','456']})
    monkeypatch.setattr(smart.httpx,'post',post_)
    monkeypatch.setattr(smart.httpx,'get',get_)
    assert smart.order_probe('app','secret','12345')==2
    assert calls[0][1]['params']['type']=='SELF'
    assert calls[1][1]['headers']['Authorization']=='Bearer test'
    assert all(x[1]['follow_redirects'] is False for x in calls)
    with pytest.raises(smart.SmartStoreError):smart.order_probe('app','secret','../bad')

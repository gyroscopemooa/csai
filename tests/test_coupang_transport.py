import hashlib,hmac,pytest
from integrations import coupang_transport as cp

def test_hmac_and_minimal_order_fields(monkeypatch):
    path='/v2/providers/openapi/apis/api/v5/vendors/A00012345/123/ordersheets'
    stamp='261127T000000Z';secret='test-secret';access='test-access'
    expected=hmac.new(secret.encode(),(stamp+'GET'+path).encode(),hashlib.sha256).hexdigest()
    assert cp.authorization(access,secret,path,stamp).endswith(expected)
    class Resp:
        is_success=True
        content=b'{}'
        def json(self):return {'code':'200','data':[{'orderId':123,'shipmentBoxId':456,'status':'DELIVERING','orderer':{'name':'private'},'receiver':{'addr1':'private'},'deliveryCompanyName':'CJ','invoiceNumber':'99','orderItems':[{'vendorItemName':'상품'}]}]}
    def get(url,**kw):
        assert url==cp.ROOT+path and not kw['follow_redirects']
        assert kw['headers']['Authorization'].startswith('CEA ')
        return Resp()
    monkeypatch.setattr(cp.httpx,'get',get)
    result=cp.order_status('A00012345',access,secret,'123')
    assert result['shipments'][0]['state_label']=='배송중'
    assert 'private' not in str(result)
    with pytest.raises(cp.CoupangError):cp.order_status('A00012345',access,secret,'../123')

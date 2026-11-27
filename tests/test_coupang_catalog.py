from integrations import coupang_transport as cp
import pytest,hmac,hashlib

def test_signed_query_and_catalog_pages(monkeypatch):
    calls=[]
    def fake(vendor,access,secret,path,params):
        calls.append(dict(params))
        second='nextToken' in dict(params)
        return {'data':[{'sellerProductId':2 if second else 1,'productId':9,'sellerProductName':'상품','vendorId':vendor,'statusName':'승인완료'}],'nextToken':'' if second else '2'}
    monkeypatch.setattr(cp,'signed_json',fake)
    result=cp.product_catalog('A00012345','access-test','secret-test')
    assert [x['id'] for x in result]==['1','2'] and len(calls)==2
    assert 'price' not in result[0] and 'stock' not in result[0]
    q='vendorId=A00012345&maxPerPage=100'
    expected=hmac.new(b'secret-test',('261127T000000ZGET'+cp.PRODUCT_PATH+q).encode(),hashlib.sha256).hexdigest()
    assert cp.authorization('access-test','secret-test',cp.PRODUCT_PATH,'261127T000000Z',query=q).endswith(expected)
    monkeypatch.setattr(cp,'signed_json',lambda *a:{'data':[{'sellerProductId':1,'vendorId':'other'}],'nextToken':''})
    with pytest.raises(cp.CoupangError):cp.product_catalog('A00012345','access-test','secret-test')

from integrations import coupang_transport as cp
from coupang_detail import normalize
import pytest

def test_detail_omits_internal_fields():
    r=normalize({'displayProductName':'공개 상품','returnCharge':5000,'items':[{'vendorItemId':123,'itemName':'private','supplyPrice':400,'attributes':[{'exposed':'EXPOSED','attributeTypeName':'색상','attributeValueName':'블루'},{'exposed':'NONE','attributeTypeName':'hidden','attributeValueName':'private'}],'contents':[{'contentDetails':[{'detailType':'TEXT','content':'&lt;p&gt;상품 설명&lt;/p&gt;&lt;script&gt;private&lt;/script&gt;'},{'detailType':'IMAGE','content':'https://example.test/image'}]}]}]})
    assert r['variants'][0]['name']=='블루' and r['text']=='상품 설명'
    assert r['fees']['returnCharge']==5000 and r['image_count']==1
    assert 'private' not in str(r) and 'supplyPrice' not in str(r)

def test_inventory_and_product_scope(monkeypatch):
    monkeypatch.setattr(cp,'signed_json',lambda *a,**k:{'data':{'vendorItemId':123,'amountInStock':0,'salePrice':999,'onSale':False}})
    assert cp.inventory('A00012345','access-test','secret-test','123')['stock']==0
    with pytest.raises(cp.CoupangError):cp.inventory('A00012345','access-test','secret-test','124')
    monkeypatch.setattr(cp,'signed_json',lambda *a,**k:{'data':{'sellerProductId':123,'vendorId':'other'}})
    with pytest.raises(cp.CoupangError):cp.product_detail('A00012345','access-test','secret-test','123')

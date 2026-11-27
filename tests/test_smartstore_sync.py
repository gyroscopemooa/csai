from integrations import smartstore_transport as ss
from commerce import rank_products
import pytest

def test_catalog_normalization_and_paging(monkeypatch):
    calls=[]
    def read(token,path,body):
        calls.append(body)
        return {'page':body['page'],'totalPages':2,'totalElements':2,'contents':[{'channelProducts':[{'channelProductNo':body['page'],'channelServiceType':'STOREFARM','channelProductDisplayStatusType':'ON','statusType':'SALE','name':'테스트 상품','salePrice':1000,'stockQuantity':4,'deliveryFee':3000}]}]}
    monkeypatch.setattr(ss,'read_json',read)
    result=ss.product_catalog('token')
    assert [x['id'] for x in result]==['1','2']
    assert len(calls)==2 and result[0]['facts']=={'deliveryFee':3000}
    monkeypatch.setattr(ss,'read_json',lambda *a:{'page':1,'totalPages':21,'totalElements':2100,'contents':[]})
    with pytest.raises(ss.SmartStoreError):ss.product_catalog('token')

def test_search_beyond_first_hundred_and_bounded():
    items=[{'name':'일반 상품 '+str(i)} for i in range(1100)]+[{'name':'고유한 스냅 카메라'}]
    assert rank_products(items,'고유한 스냅 카메라 가격 알려주세요')[0]['name']=='고유한 스냅 카메라'
    assert len(rank_products(items,'일반 상품 가격'))<=3

def test_order_status_excludes_personal_details(monkeypatch):
    monkeypatch.setattr(ss,'read_json',lambda *a:{'data':[{'order':{'ordererName':'private'},'productOrder':{'productOrderId':'123','productName':'상품','productOrderStatus':'DELIVERING','shippingAddress':{'baseAddress':'private'}},'delivery':{'trackingNumber':'1234','deliveryCompany':'CJ'}}]})
    result=ss.order_status('token','123')
    assert result['tracking']=='1234' and 'private' not in str(result)

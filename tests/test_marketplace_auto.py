from test_app import owner
from marketplace_auto import safe,normalize,product_hash

def test_conservative_match():
    assert safe('소재가 면인가요?')
    assert not safe('주문번호 알려 주세요')
    assert not safe('가격 알려 주세요')
    assert not safe('배송비는 무료인가요')
    assert not safe('test@example.com')
    assert not safe('01012345678')
    assert normalize('  소재가   면인가요? ')=='소재가 면인가요?'
    assert normalize('면인가요?')!=normalize('면이 아닌가요?')

def test_product_change_invalidates_approved_rule():
    p={'source':'coupang','product_id':'1','name':'상품','detail_as_of':1,'description':'면','options':[{'id':'1','name':'빨강','attributes':[],'inventory':{'stock':2}}]}
    h=product_hash(p)
    assert h and h==product_hash({**p,'detail_as_of':2,'price':9000,'options':[{**p['options'][0],'inventory':{'stock':0}}]})
    assert h!=product_hash({**p,'description':'폴리에스터'})
    assert not product_hash({'name':'상품'})

from integrations import coupang_transport as cp,smartstore_transport as ss
import marketplace_qna as q

def test_qna_transport_omits_customer_identifiers(monkeypatch):
    monkeypatch.setattr(cp,'signed_json',lambda *a,**k:{'data':{'pagination':{'totalPages':1},'content':[{'inquiryId':1,'sellerProductId':2,'content':'상품 재질?','commentDtoList':[],'orderIds':[999999],'inquiryAt':'2026-11-27'}]}})
    items,pages=cp.pending_inquiries('A00012345','access-test','secret-test','2026-11-21','2026-11-27',1)
    assert pages==1 and items[0]['product_id']=='2' and 'orderIds' not in items[0]
    class Response:
        is_success=True
        content=b'{}'
        def json(self):return {'contents':[{'questionId':3,'productId':4,'productName':'상품','question':'설명?','answered':False,'answers':[],'maskedWriterId':'private'}],'totalPages':1}
    monkeypatch.setattr(ss.httpx,'get',lambda *a,**k:Response())
    items,pages=ss.pending_inquiries('token','start','end',1)
    assert items[0]['id']=='3' and 'private' not in str(items)

def test_product_context_excludes_private_fields():
    result=q.safe_product({'name':'상품','price':None,'description':'문의 test@example.com','customer':'private','credential':'private'})
    assert result['price'] is None and 'test@example.com' not in str(result) and 'private' not in str(result)

from integrations import smartstore_transport as ss
import pytest

START='2026-11-27T00:00:00+00:00'
END='2026-11-27T01:00:00+00:00'
def test_changed_orders_paging_and_no_pii(monkeypatch):
    calls=[]
    class Response:
        is_success=True
        content=b'{}'
        def __init__(self,data):self.data=data
        def json(self):return self.data
    def get(url,**kwargs):
        calls.append(kwargs['params'])
        row={'productOrderId':'123','orderId':'456','productOrderStatus':'PAYED' if len(calls)==1 else 'DELIVERING','lastChangedDate':'2026-11-27T00:30:00+00:00','receiver':'private','claimStatus':'RETURN_REQUEST'}
        data={'lastChangeStatuses':[row]}
        if len(calls)==1:data['more']={'moreFrom':row['lastChangedDate'],'moreSequence':1}
        return Response({'data':data})
    monkeypatch.setattr(ss.httpx,'get',get)
    result=ss.changed_orders('token',START,END)
    assert len(result)==1 and result[0]['status']=='DELIVERING'
    assert result[0]['claimStatus']=='RETURN_REQUEST' and 'private' not in str(result)
    assert calls[1]['moreSequence']==1
    monkeypatch.setattr(ss.httpx,'get',lambda *a,**k:Response({'data':{'lastChangeStatuses':[],'more':{'moreFrom':START,'moreSequence':1}}}))
    with pytest.raises(ss.SmartStoreError):ss.changed_orders('token',START,END)

def test_empty_feed_and_invalid_range(monkeypatch):
    class Response:
        is_success=True
        content=b'{}'
        def json(self):return {'timestamp':START,'traceId':'test'}
    monkeypatch.setattr(ss.httpx,'get',lambda *a,**k:Response())
    assert ss.changed_orders('token',START,END)==[]
    with pytest.raises(ss.SmartStoreError):ss.changed_orders('token',END,START)

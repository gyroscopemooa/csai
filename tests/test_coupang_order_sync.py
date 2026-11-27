from test_app import owner,post
from integrations import coupang_transport as cp
from coupang_order_sync import next_scan
from datetime import date
import pytest

def test_ordersheets_pagination_and_privacy(monkeypatch):
    calls=[]
    def fake(vendor,access,secret,path,params):
        calls.append(dict(params))
        n=len(calls)
        return {'code':200,'data':[{'shipmentBoxId':n,'orderId':12,'status':'DELIVERING','receiver':{'name':'private'},'orderer':{'phone':'private'}}],'nextToken':'abc' if n==1 else ''}
    monkeypatch.setattr(cp,'signed_json',fake)
    rows=cp.ordersheets_day('A00012345','access-test','secret-test','2026-11-27','DELIVERING')
    assert [x['shipment_id'] for x in rows]==['1','2']
    assert calls[0]['createdAtFrom']=='2026-11-27+09:00' and calls[1]['nextToken']=='abc'
    assert 'private' not in str(rows)
    with pytest.raises(cp.CoupangError):cp.ordersheets_day('A00012345','access-test','secret-test','2026-11-31','DELIVERING')

def test_scan_rotation():
    d=date(2026,11,27)
    assert next_scan({'scan_state':5,'history_offset':6},d)==('2026-11-21',6,6,10)
    assert next_scan({'scan_state':11,'history_offset':6},d)==('2026-11-27',0,1,600)

from test_app import owner,post,patch,public
from store import db,one,now
import order_access as oa

def test_one_time_order_code(monkeypatch):
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});patch(c,{'enabled':True})
    post(c,'/api/commerce/settings',{'enabled':True})
    me=c.get('/api/me').json()
    u,t=public(c);v,other=public(c)
    with db(True) as d:
        ws=one(d,'SELECT id FROM workspace WHERE slug=?',(me['slug'],))['id']
        tid=one(d,'SELECT id FROM thread WHERE ws=? AND visitor=?',(ws,t))['id']
        d.execute("INSERT INTO smartstore_connection VALUES(?,?,?,?,?,1,'synced','',?,?,0)",(ws,'','client','encrypted','rev',now(),now()+3600))
    monkeypatch.setattr(oa.sync,'configured',lambda:True)
    class Cipher:
        def decrypt(self,v):return b'secret'
    monkeypatch.setattr(oa,'encryption',lambda:Cipher())
    monkeypatch.setattr(oa.ss,'access_token',lambda *a:'token')
    monkeypatch.setattr(oa.ss,'order_status',lambda *a:{'reference':'123','product':'상품','status':'DELIVERING','delivery_status':'','carrier':'CJ','tracking':'123','queried_at':now(),'private':'never'})
    path='/api/inbox/'+tid+'/order-access'
    assert c.post(path,json={'reference':'123','confirmed':True}).status_code==422
    r=post(c,path,{'reference':'123','confirmed':True,'verified_outside_chat':True})
    assert v.post('/api/customer/order-access',json={'token':other,'code':r['code']}).status_code==403
    result=post(u,'/api/customer/order-access',{'token':t,'code':r['code']})
    assert result['status']=='DELIVERING' and 'private' not in result
    assert u.post('/api/customer/order-access',json={'token':t,'code':r['code']}).status_code==403

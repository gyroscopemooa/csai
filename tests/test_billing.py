from test_app import owner,post,patch,public
from store import db,now

def order(c,kind,**kw):return post(c,'/api/billing/orders',{'kind':kind,**kw})
def paid(c,o):return post(c,'/api/billing/orders/'+o['id']+'/sandbox-confirm',{})

def test_server_quote_and_idempotent_checkout():
    c=owner();o=order(c,'subscription',plan='lite',addons=['auto_booking','naver','kakao'],client='one',amount=1);assert o['amount']==9900+2900+4900+7900;assert order(c,'subscription',plan='lite',addons=['kakao','naver','auto_booking'],client='one')['id']==o['id'];assert paid(c,o)['status']=='paid';assert paid(c,o)['status']=='paid';assert c.get('/api/me').json()['remaining']==300
    patch(c,{'enabled':True});u,t=public(c);post(u,'/api/chat',{'token':t,'message':'문의','clientMessageId':'one'});assert c.get('/api/me').json()['remaining']==299;up=order(c,'subscription',plan='basic',addons=[],client='upgrade');paid(c,up);assert c.get('/api/me').json()['remaining']==499
    post(c,'/api/billing/subscription/cancel',{});assert c.get('/api/billing/history').json()['subscription']['cancel_at_end']==1
    with db(True) as d:d.execute('UPDATE subscription SET period_end=? WHERE order_id=?',(now()-1,up['id']))
    assert c.get('/api/me').json()['plan']=='free';assert c.get('/api/public/'+c.get('/api/me').json()['slug']).status_code==404

def test_credit_message_orders_and_isolation():
    c=owner();o=order(c,'education',sku='mini',client='edu');assert owner().post('/api/billing/orders/'+o['id']+'/sandbox-confirm',json={}).status_code==404;paid(c,o);paid(c,o);assert c.get('/api/me').json()['credits']==120
    m=order(c,'message',name='SMS',quantity=100,client='msg');paid(c,m);paid(c,m);assert c.get('/api/billing/history').json()['messages']==[{'kind':'SMS','n':100}];o=order(c,'education',sku='mini',client='cancel');post(c,'/api/billing/orders/'+o['id']+'/cancel',{});assert c.post('/api/billing/orders/'+o['id']+'/sandbox-confirm',json={}).status_code==409

def test_package_overlap():
    c=owner();r=c.post('/api/billing/quote',json={'kind':'subscription','plan':'lite','addons':['customer_pack','work_pack']});assert r.status_code==422;r=post(c,'/api/billing/quote',{'kind':'subscription','plan':'lite','addons':['all','channel_pack','channels','widget']});assert r['amount']==49800

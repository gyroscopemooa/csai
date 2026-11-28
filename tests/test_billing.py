from test_app import owner,post,patch,public
from store import db,now

def order(c,kind,**kw):return post(c,'/api/billing/orders',{'kind':kind,**kw})
def paid(c,o):return post(c,'/api/billing/orders/'+o['id']+'/sandbox-confirm',{})

def test_server_quote_and_idempotent_checkout():
    c=owner();o=order(c,'subscription',plan='lite',addons=['auto_booking','naver','kakao'],client='one',amount=1);assert o['amount']==24900+2900+14900+7900;assert order(c,'subscription',plan='lite',addons=['kakao','naver','auto_booking'],client='one')['id']==o['id'];assert paid(c,o)['status']=='paid';assert paid(c,o)['status']=='paid';assert c.get('/api/me').json()['remaining']==300
    patch(c,{'enabled':True});u,t=public(c);post(u,'/api/chat',{'token':t,'message':'문의','clientMessageId':'one'});assert c.get('/api/me').json()['remaining']==299;up=order(c,'subscription',plan='basic',addons=[],client='upgrade');paid(c,up);assert c.get('/api/me').json()['remaining']==499
    post(c,'/api/billing/subscription/cancel',{});assert c.get('/api/billing/history').json()['subscription']['cancel_at_end']==1
    with db(True) as d:d.execute('UPDATE subscription SET period_end=? WHERE order_id=?',(now()-1,up['id']))
    assert c.get('/api/me').json()['plan']=='free';assert c.get('/api/public/'+c.get('/api/me').json()['slug']).status_code==404

def test_credit_message_orders_and_isolation():
    c=owner();o=order(c,'education',sku='mini',client='edu');assert owner().post('/api/billing/orders/'+o['id']+'/sandbox-confirm',json={}).status_code==404;paid(c,o);paid(c,o);assert c.get('/api/me').json()['credits']==120
    m=order(c,'message',name='SMS',quantity=100,client='msg');paid(c,m);paid(c,m);assert c.get('/api/billing/history').json()['messages']==[{'kind':'SMS','n':100}];o=order(c,'education',sku='mini',client='cancel');post(c,'/api/billing/orders/'+o['id']+'/cancel',{});assert c.post('/api/billing/orders/'+o['id']+'/sandbox-confirm',json={}).status_code==409

def test_package_overlap():
    c=owner();r=c.post('/api/billing/quote',json={'kind':'subscription','plan':'lite','addons':['customer_pack','work_pack']});assert r.status_code==422;r=post(c,'/api/billing/quote',{'kind':'subscription','plan':'lite','addons':['all','channel_pack','channels','widget']});assert r['amount']==123900

def test_polar_sandbox_uses_server_calculated_price(monkeypatch):
    import httpx
    import polar_sandbox

    client = owner()
    request = {'kind': 'subscription', 'plan': 'lite', 'addons': ['all', 'widget'], 'amount': 1}
    path = '/api/operator/polar/sandbox-checkout'
    assert client.post(path, json=request).status_code == 403
    monkeypatch.setattr(polar_sandbox, 'require_operator', lambda request: None)
    monkeypatch.setenv('POLAR_SANDBOX_CHECKOUT_ENABLED', '0')
    assert client.post(path, json=request).status_code == 503
    product = '6d2751d7-e66a-4c56-a700-e66dd883b3cb'
    monkeypatch.setenv('POLAR_SANDBOX_CHECKOUT_ENABLED', '1')
    monkeypatch.setenv('POLAR_SANDBOX_TOKEN', 'test-token')
    monkeypatch.setenv('POLAR_SANDBOX_MONTHLY_PRODUCT_ID', product)

    def checkout(url, *, json, headers, timeout):
        assert url == 'https://sandbox-api.polar.sh/v1/checkouts/'
        assert json['prices'][product][0]['price_amount'] == 123900
        return httpx.Response(201, request=httpx.Request('POST', url), json={
            'id': 'test-checkout', 'amount': 123900, 'currency': 'krw', 'url': 'https://sandbox.polar.sh/example',
        })

    monkeypatch.setattr(polar_sandbox.httpx, 'post', checkout)
    result = client.post(path, json=request)
    assert result.status_code == 200
    assert result.json()['items']['addons'] == ['all']


def test_existing_channel_bundle_and_education():
    c=owner()
    def amount(addons):
        return post(c,'/api/billing/quote',{'kind':'subscription','plan':'mini','addons':addons})['amount']
    assert amount(['naver','kakao']) == amount(['channels']) == 16800
    assert amount(['channel_pack']) == 18800
    assert amount(['channel_pack']) < amount(['channels','widget'])
    assert amount(['all']) == 107900
    assert post(c,'/api/billing/quote',{'kind':'education','sku':'mini'})['amount'] == 1900
    assert post(c,'/api/billing/quote',{'kind':'subscription','plan':'enterprise','addons':[]})['amount'] == 8990000


def test_subscription_change_quote_is_read_only():
    c=owner()
    paid(c,order(c,'subscription',plan='lite',addons=[],client='initial-change'))
    r=post(c,'/api/billing/quote',{'kind':'subscription','plan':'lite','addons':['auto_booking']})
    assert r['amount']==42700
    assert r['change']['current_monthly']==24900
    assert r['change']['monthly_delta']==17800
    assert 0<=r['change']['estimated_upgrade_proration']<=17800
    assert not r['change']['actual_charge_verified']
    assert c.get('/api/me').json()['addons']==[]

from fastapi.testclient import TestClient
from app import app
from test_app import owner,post,patch,public

def test_manual_sales_scoped_dashboard_and_customer_request():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['extra_agent','calendar','crm','tasks']});patch(c,{'enabled':True})
    a=post(c,'/api/agents',{'create':True,'brand':'별도 브랜드','enabled':True})
    pa='?agent='+a['id']
    post(c,'/api/commerce/settings',{'enabled':True});post(c,'/api/commerce/settings'+pa,{'enabled':True})
    p=post(c,'/api/commerce/products',{'sku':'A1','name':'상품','price':1000,'stock':3,'published':True,'description':'공개 설명'})
    assert c.get('/api/commerce'+pa).json()['products']==[]
    assert c.post('/api/commerce/products'+pa,json={'id':p['id'],'sku':'A1','name':'상품','price':1,'stock':1}).status_code==404
    post(c,'/api/commerce/orders',{'channel':'smartstore','reference':'order-1','product':'상품','quantity':2,'amount':2000})
    u,t=public(c)
    assert u.get('/api/customer/commerce/'+t).json()['products']==[{'name':'상품','variant':'','price':1000,'url':'','description':'공개 설명'}]
    body={'token':t,'client':'req1','kind':'return','channel':'smartstore','reference':'order-1','details':'반품 문의','confirmed':True}
    req=post(u,'/api/customer/commerce',body);assert post(u,'/api/customer/commerce',body)['duplicate']
    assert c.get('/api/commerce'+pa).json()['requests']==[]
    assert c.patch('/api/commerce/requests/'+req['id']+pa,json={'state':'resolved'}).status_code==404
    assert c.get('/api/business-dashboard').json()['sales']['recorded_amount']==2000
    assert c.get('/api/business-dashboard'+pa).json()['sales']['orders_today']==0
    assert owner().get('/api/commerce').status_code==403
    assert c.patch('/api/commerce/requests/'+req['id'],json={'state':'resolved'}).status_code==200
    assert c.get('/api/business-dashboard').json()['sales']['pending_requests']==0

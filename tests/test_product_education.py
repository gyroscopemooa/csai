from product_education import extract,enrich
from test_app import owner,post
from store import db,one,dump,now

def test_detail_text_and_public_policy_only():
    content,fp=extract({'detailContent':'<p>상품 특징</p><script>ignore this</script><img src="https://example.com/a.jpg">','deliveryInfo':{'deliveryFee':{'baseFee':3000},'claimDeliveryInfo':{'returnDeliveryFee':6000,'returnAddress':'private'}}})
    assert content['text']=='상품 특징'
    assert content['fees']=={'baseFee':3000,'returnDeliveryFee':6000}
    assert content['image_count']==1
    assert 'private' not in str(content)
    assert fp==extract({'detailContent':'<p>상품 특징</p><script>ignore this</script><img src="https://example.com/a.jpg">','deliveryInfo':{'deliveryFee':{'baseFee':3000},'claimDeliveryInfo':{'returnDeliveryFee':6000}}})[1]

def test_product_education_estimate_no_charge_and_scoped_publish():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':[]});post(c,'/api/commerce/settings',{'enabled':True})
    me=c.get('/api/me').json();before=me['credits']
    with db(True) as d:
        ws=one(d,'SELECT id FROM workspace WHERE slug=?',(me['slug'],))['id']
        d.execute('INSERT INTO smartstore_product VALUES(?,?,?,?,?,?,?,?)',(ws,'','123','테스트 상품',1000,3,dump({'name':'테스트 상품'}),now()))
        d.execute('INSERT INTO smartstore_detail VALUES(?,?,?,?,?,?,?)',(ws,'','123','hash',dump({'text':'상품 특징','fees':{},'image_count':0,'truncated':False}),'',now()))
    path='/api/commerce/smartstore/products/123/education'
    q=post(c,path,{'confirmed':True})
    assert q['maxCredits']>0 and c.get('/api/me').json()['credits']==before
    assert owner().post(path,json={'confirmed':True}).status_code in (403,404,409)
    # Fake reviewed training result to verify only product-specific publish, independent of model/cost.
    with db(True) as d:d.execute("UPDATE training SET state='review',result=? WHERE ws=? AND id=?",(dump({'style':'global change','rules':['상품 특징'],'faq':[{'q':'특징?','a':'상품 특징'}]}),ws,q['id']))
    old=c.get('/api/me').json()['published']
    assert post(c,'/api/training/'+q['id']+'/publish',{'replace':True})['product_only']
    assert c.get('/api/me').json()['published']==old
    with db() as d:
        assert enrich(d,ws,'','123')['approved_product_facts']==['상품 특징']
        assert enrich(d,ws,'other','123')=={}

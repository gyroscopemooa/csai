import os,tempfile,sys,base64,concurrent.futures
from pathlib import Path
from datetime import datetime,timedelta
os.environ['DATA_DIR']=tempfile.mkdtemp(prefix='csai-tests-');os.environ['DEMO_MODE']='1';os.environ['OPENAI_API_KEY']=''
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app import app
import ai

def owner():
    c=TestClient(app); assert c.get('/auth/demo').status_code==200;return c

def test_health_endpoint():
    r=TestClient(app).get('/health');assert r.status_code==200 and r.json()['ok'] is True

def post(c,path,body):
    r=c.post(path,json=body);assert r.status_code==200,(path,r.status_code,r.text);return r.json()
def teach(c,q,a,unknown=None):
    job=post(c,'/api/faq',{'q':q,'a':a,**({'unknown':unknown} if unknown else {})})
    post(c,'/api/training/'+job['id']+'/run',{})
    return post(c,'/api/training/'+job['id']+'/publish',{})
def patch(c,body):
    r=c.patch('/api/settings',json=body);assert r.status_code==200,r.text

def setup_booking(auto=True,payment=False):
    c=owner();post(c,'/api/demo/billing',{'plan':'lite','addons':['auto_booking','change_booking']});policy=c.get('/api/policies/status').json();post(c,'/api/policies/automation-ack',{'version':policy['version'],'errors':True,'accuracy':True,'approval':True});patch(c,{'enabled':True,'fields':[{'key':'name','label':'고객명','type':'text','required':True}], 'modes':{'booking':'auto' if auto else 'manual'},'payment_required':payment});return c

def public(c):
    slug=c.get('/api/me').json()['slug'];u=TestClient(app);t=post(u,'/api/session',{'slug':slug})['token'];return u,t

def future():return (datetime.now()+timedelta(days=3)).strftime('%Y-%m-%d')+'T14:00'
def draft(u,t,start=None):
    v=u.get('/api/booking/form/'+t).json()['template_version'];return post(u,'/api/booking/draft',{'token':t,'version':v,'start':start or future(),'payload':{'name':'테스트'}})
def confirm(u,t,b):return u.post('/api/booking/'+b['id']+'/confirm',json={'token':t,'confirmation':b['token']})

def test_free_gate_idempotency():
    c=owner();patch(c,{'price':'150,000원'});t=post(c,'/api/session',{'test':True})['token'];p={'token':t,'message':'가격은?','clientMessageId':'one'}
    r=post(c,'/api/chat',p);assert r['remaining']==0 and r['reply']=='150,000원';assert post(c,'/api/chat',p)==r
    assert c.post('/api/chat',json=p|{'clientMessageId':'two'}).status_code==402
    assert c.patch('/api/settings',json={'enabled':True}).status_code==403
    assert c.get('/api/public/'+c.get('/api/me').json()['slug']).status_code==404

def test_training_file_review_publish_and_duplicate():
    c=owner();f={'name':'faq.txt','data':base64.b64encode('주말 예약? => 주말 예약은 가능합니다.'.encode()).decode()};a=post(c,'/api/files',f);assert post(c,'/api/files',f)['duplicate'];j=post(c,'/api/training/estimate',{'files':[a['id']]});assert j['enough'];r=post(c,'/api/training/'+j['id']+'/run',{});assert c.get('/api/me').json()['credits']==20-r['cost'];assert c.get('/api/me').json()['published']=={};post(c,'/api/training/'+j['id']+'/publish',{});assert c.get('/api/me').json()['published']['faq'];assert c.post('/api/training/'+j['id']+'/run',json={}).status_code==409

def test_training_failure_refund(monkeypatch):
    c=owner();j=post(c,'/api/training/estimate',{'text':'교육자료'});monkeypatch.setattr(ai,'train',lambda *a:(_ for _ in ()).throw(RuntimeError('test')));assert c.post('/api/training/'+j['id']+'/run',json={}).status_code==502;assert c.get('/api/me').json()['credits']==20

def test_chat_failure_refund(monkeypatch):
    c=owner();t=post(c,'/api/session',{'test':True})['token'];monkeypatch.setattr(ai,'answer',lambda *a:(_ for _ in ()).throw(RuntimeError('test')));assert c.post('/api/chat',json={'token':t,'message':'hello','clientMessageId':'x'}).status_code==502;assert c.get('/api/me').json()['remaining']==1

def test_workspace_isolation():
    a,b=owner(),owner();f=post(a,'/api/files',{'name':'a.txt','data':'YWJj'});assert b.get('/api/files').json()==[];assert b.post('/api/training/estimate',json={'files':[f['id']]}).status_code==404;assert TestClient(app).get('/api/me').status_code==401

def test_unknown_and_manual():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite'});patch(c,{'enabled':True});u,t=public(c);p={'token':t,'message':'새로운 질문','clientMessageId':'a'};r=post(u,'/api/chat',p);assert r['unknown'];q=c.get('/api/unknown').json()[0];teach(c,q['q'],'직접 교육 답변',q['id']);r=post(u,'/api/chat',p|{'clientMessageId':'b'});assert r['reply']=='직접 교육 답변';post(c,'/api/inbox/'+q['thread'],{'manual':True,'reply':'담당자가 답변합니다.'});assert any(x['role']=='staff' for x in u.get('/api/session/'+t+'/messages').json())


def test_unified_inbox_filters_search_and_external_reply_boundary():
    from store import db,one,uid,now
    c=owner();post(c,'/api/demo/billing',{'plan':'lite'});patch(c,{'enabled':True})
    u,token=public(c);post(u,'/api/chat',{'token':token,'message':'촬영 문의 특별단어','clientMessageId':'search-one'})
    slug=c.get('/api/me').json()['slug']
    with db(True) as conn:
        ws=one(conn,'SELECT id FROM workspace WHERE slug=?',(slug,))['id']
        visitor_id=uid();external_thread=uid()
        conn.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(visitor_id,ws,now()+86400,'public'))
        conn.execute('INSERT INTO thread(id,ws,visitor,kind,created) VALUES(?,?,?,?,?)',(external_thread,ws,visitor_id,'naver',now()))
        conn.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,external_thread,'user','네이버 교환 요청',now()))
    assert len(c.get('/api/inbox?kind=public').json())==1
    assert [x['id'] for x in c.get('/api/inbox?kind=naver&q=교환').json()]==[external_thread]
    assert c.get('/api/inbox?kind=naver&q=특별단어').json()==[]
    assert c.get('/api/inbox?q=%25').json()==[]
    assert c.get('/api/inbox?kind=other').status_code==422
    assert c.post('/api/inbox/'+external_thread,json={'reply':'답변 전송'}).status_code==409
    assert c.get('/api/inbox/'+external_thread).json()['messages'][0]['body']=='네이버 교환 요청'

def test_booking_race_and_idempotent():
    c=setup_booking();a,t=public(c);b,u=public(c);x=draft(a,t);y=draft(b,u)
    with concurrent.futures.ThreadPoolExecutor(2) as ex:r=list(ex.map(lambda z:confirm(*z),[(a,t,x),(b,u,y)]))
    assert sorted(i.status_code for i in r)==[200,409];winner=(a,t,x) if r[0].status_code==200 else (b,u,y);assert confirm(*winner).json()['status']=='confirmed';assert len(c.get('/api/bookings').json())==1

def test_booking_payment_and_manual():
    c=setup_booking(payment=True);u,t=public(c);b=draft(u,t);r=confirm(u,t,b);assert r.json()['status']=='pending_payment';path='/api/bookings/'+b['id'];assert c.post(path,json={'action':'approve'}).status_code==409;assert post(c,path,{'action':'approve','paid':True})['status']=='confirmed';assert post(c,path,{'action':'cancel'})['status']=='cancelled'
    c=setup_booking(auto=False);u,t=public(c);b=draft(u,t);assert confirm(u,t,b).json()['status']=='pending';assert post(c,'/api/bookings/'+b['id'],{'action':'approve'})['status']=='confirmed'

def test_booking_validation_and_version():
    c=setup_booking();u,t=public(c);v=u.get('/api/booking/form/'+t).json()['template_version'];assert u.post('/api/booking/draft',json={'token':t,'version':v,'start':future(),'payload':{}}).status_code==422;b=draft(u,t);patch(c,{'duration':90});assert confirm(u,t,b).status_code==409

def test_paid_permissions_and_qr():
    c=owner();assert c.get('/api/bookings').status_code==403;post(c,'/api/demo/billing',{'plan':'lite','addons':['auto_booking','naver','kakao','channels']});m=c.get('/api/me').json();assert 'calendar' in m['entitlements'] and 'naver' in m['entitlements'] and 'naver' not in m['addons'];assert c.get('/api/qr').headers['content-type']=='image/png';assert c.get('/api/export').status_code==403

def test_external_refund_never_executes():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite'});patch(c,{'links':[{'name':'마이리얼트립','url':'https://www.myrealtrip.com/'}]});t=post(c,'/api/session',{'test':True})['token'];r=post(c,'/api/chat',{'token':t,'message':'마이리얼트립 환불','clientMessageId':'x'});assert 'https://' in r['reply'] and '신청' in r['reply']

def test_refund_followup_and_unknown_off():
    c=owner();post(c,'/api/demo/billing',{'plan':'lite'});patch(c,{'links':[{'name':'마이리얼트립','url':'https://www.myrealtrip.com/'}],'modes':{'unknown':'off'}});t=post(c,'/api/session',{'test':True})['token'];r=post(c,'/api/chat',{'token':t,'message':'환불하려고요','clientMessageId':'x'});assert '판매처' in r['reply'];r=post(c,'/api/chat',{'token':t,'message':'마이리얼트립이요','clientMessageId':'y'});assert 'https://' in r['reply'];r=post(c,'/api/chat',{'token':t,'message':'전혀 새로운 질문','clientMessageId':'z'});assert not r['unknown'];assert c.get('/api/unknown').json()==[]

def test_old_booking_draft_invalidated():
    c=setup_booking();u,t=public(c);a=draft(u,t);b=draft(u,t);assert confirm(u,t,a).status_code==409;assert confirm(u,t,b).status_code==200

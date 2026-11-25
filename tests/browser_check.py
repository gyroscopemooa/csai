"""Offline browser rendering + ASGI API bridge; no external browser navigation.
For full HTTP end-to-end on your PC use run.py and the checklist in README.
"""
import os,tempfile,sys,json,base64
from pathlib import Path
from datetime import date,timedelta
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
os.environ.update(DATA_DIR=tempfile.mkdtemp(prefix='csai-browser-'),DEMO_MODE='1',OPENAI_API_KEY='',APP_URL='http://127.0.0.1:8000');sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from app import app
from playwright.sync_api import sync_playwright
owner=TestClient(app);visitor=TestClient(app);errors=[];screens=[]
css=(ROOT/'web/style.css').read_text(encoding='utf-8');js=(ROOT/'web/app.js').read_text(encoding='utf-8')
# The application's exact DOM/rendering code runs in Chromium; only HTTP transport and public path are test adapters.
bridge='''const sessionStorage={data:{},getItem(k){return this.data[k]||null},setItem(k,v){this.data[k]=v},removeItem(k){delete this.data[k]}};const fetch=async(path,opts={})=>{let r=await py_api(String(path),opts.method||'GET',opts.body||null);return {ok:r.status>=200&&r.status<300,status:r.status,json:async()=>r.body}};'''
def page_content(page,c,public_slug=None):
    def dispatch(path,method,body):
        r=c.request(method,urlsplit(path).path or '/',json=json.loads(body) if body else None);return {'status':r.status_code,'body':r.json() if r.headers.get('content-type','').startswith('application/json') else {}}
    page.expose_function('py_api',dispatch);page.on('pageerror',lambda x:(errors.append(str(x)),print('PAGEERROR',x,flush=True)))
    script=js.replace("publicMode=location.pathname.startsWith('/c/')||location.pathname.startsWith('/widget/'),slug=location.pathname.split('/')[2]",f'publicMode={str(bool(public_slug)).lower()},slug={json.dumps(public_slug)}')
    # about:blank is not a secure origin, so provide only a test UUID helper.
    prefix="if(!crypto.randomUUID)crypto.randomUUID=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('');"
    page.set_content('<!doctype html><html lang="ko"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style><div id="app"></div><script>'+prefix+bridge+script+'</script></html>')
def post(c,path,data,method='POST'):
    r=c.request(method,path,json=data);assert r.status_code==200,(path,r.status_code,r.text);return r.json()
with sync_playwright() as pw:
    launch={'headless':True,'args':['--no-sandbox']};exe=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium');
    if Path(exe).exists():launch['executable_path']=exe
    b=pw.chromium.launch(**launch);pg=b.new_page(viewport={'width':1280,'height':900},device_scale_factor=1);page_content(pg,owner)
    def shot(name,page=pg):
        page.wait_for_timeout(520);page.screenshot(path=str(OUT/(name+'.png')),full_page=False,animations='disabled');screens.append(name)
    def nav(h,title):
        pg.evaluate('(h)=>{location.hash=h;render()}',h);pg.get_by_role('heading',name=title,exact=True).wait_for(timeout=5000);pg.wait_for_timeout(100)
        assert not pg.get_by_role('heading',name='오류',exact=True).count(),pg.locator('main').inner_text()
    pg.wait_for_timeout(500);print(pg.locator('body').inner_text(),errors,flush=True);pg.get_by_role('heading',name='나처럼 상담하는 AI').wait_for(timeout=5000);shot('01_home');owner.get('/auth/demo');pg.evaluate('async()=>{await refresh();location.hash="education";render()}');pg.get_by_role('heading',name='AI 교육시키기').wait_for(timeout=5000);shot('02_education')
    pg.locator('#training-text').fill('배송 기간? => 출고 후 2일입니다.');pg.get_by_role('button',name='교육 비용 확인').click();pg.get_by_role('button',name='비용 확인 및 교육 시작').click();pg.get_by_role('button',name='승인 및 상담에 반영').wait_for(timeout=5000);shot('03_training_review');pg.get_by_role('button',name='승인 및 상담에 반영').click();pg.get_by_text('반영 완료',exact=False).wait_for(timeout=5000)
    nav('test','AI 상담 테스트');pg.locator('#msg').fill('배송 기간?');pg.get_by_role('button',name='전송').click();pg.get_by_text('출고 후 2일입니다.',exact=True).wait_for(timeout=5000);shot('04_test_chat');pg.locator('#msg').fill('추가 질문');pg.get_by_role('button',name='전송').click();pg.get_by_role('heading',name='상담 이용 안내').wait_for(timeout=5000);shot('05_paywall');pg.get_by_role('button',name='요금제 보기',exact=True).click();pg.get_by_role('heading',name='요금제 및 결제').wait_for(timeout=5000);shot('06_pricing')
    post(owner,'/api/demo/billing',{'plan':'lite','addons':['auto_booking','change_booking','crm','quote','stats','export','widget']});post(owner,'/api/settings',{'brand':'테스트 스냅','fields':[{'key':'name','label':'고객명','type':'text','required':True},{'key':'location','label':'장소','type':'text','required':True}],'modes':{'booking':'auto'},'enabled':True,'notice':'공식 예약 안내','links':[{'name':'마이리얼트립','url':'https://www.myrealtrip.com/'}]},'PATCH');pg.evaluate('async()=>{await refresh();selectedPlan=me.plan;selectedAdd=new Set(me.addons);render()}')
    for h,title in [('features','전체 기능 비교'),('credits','AI 교육 크레딧'),('addons','추가 기능 요금표'),('settings','설정'),('style','상담 스타일 설정'),('preview','채팅창 미리보기'),('channels','외부 채널 연동'),('customers','고객·업무 관리'),('alerts','알림 및 미학습 질문'),('inbox','상담 목록'),('calendar','일정표 보기'),('fields','맞춤 일정 등록 양식'),('booking-settings','예약 설정')]:
        nav(h,title)
        if h=='preview':
            png=base64.b64encode(owner.get('/api/qr').content).decode();pg.locator('img').evaluate('(el,s)=>el.src=s','data:image/png;base64,'+png);pg.locator('#public-link').fill('http://127.0.0.1:8000/c/'+owner.get('/api/me').json()['slug'])
        if h in ['features','addons','preview','fields','channels','settings']:shot('screen_'+h)
    s=owner.get('/api/me').json()['slug'];mp=b.new_page(viewport={'width':390,'height':844},device_scale_factor=1);page_content(mp,visitor,s);mp.get_by_text('테스트 스냅 고객센터').wait_for(timeout=5000);shot('07_mobile_chat',mp)
    future=(date.today()+timedelta(days=3)).isoformat();mp.locator('#msg').fill(f'{future} 14:00 예약\n고객명: 김테스트\n장소: 해운대');mp.get_by_role('button',name='전송').click();mp.locator('#booking-time').wait_for(timeout=5000);assert mp.locator('#booking-name').input_value()=='김테스트';mp.wait_for_timeout(150);print('prefill',mp.locator('#booking-time').input_value(),flush=True);assert mp.locator('#booking-time').input_value()=='14:00';mp.get_by_role('button',name='예약 내용 확인').click();mp.get_by_role('heading',name='예약 내용 최종 확인').wait_for(timeout=5000);shot('08_mobile_confirm',mp);mp.get_by_role('button',name='확정 요청').click();mp.get_by_role('heading',name='확정',exact=True).wait_for(timeout=5000);shot('09_mobile_confirmed',mp)
    nav('calendar','일정표 보기');pg.evaluate('(d)=>{selectedDate=d;calendarMonth=new Date(d+"T12:00:00");render()}',future);pg.get_by_text('김테스트',exact=True).wait_for(timeout=5000);shot('10_calendar_confirmed');assert mp.evaluate('document.documentElement.scrollWidth<=innerWidth');pg.set_viewport_size({'width':390,'height':844});nav('education','AI 교육시키기');assert pg.evaluate('document.documentElement.scrollWidth<=innerWidth');shot('11_mobile_admin');
    pg.set_viewport_size({'width':1280,'height':900})
    post(owner,'/api/demo/billing',{'plan':'lite','addons':['auto_booking','change_booking','crm','quote','stats','export','widget','naver','kakao','extra_agent','design','custom_url','unbrand','email','new_alert','unknown_alert','google_calendar']})
    pg.evaluate('async()=>{await refresh();selectedPlan=me.plan;selectedAdd=new Set(me.addons);render()}')
    nav('calendar','일정표 보기');pg.get_by_role('button',name='담당자 관리',exact=True).click();pg.get_by_role('button',name='담당자 추가',exact=True).click();pg.locator('#res-1').fill('작가 B');pg.get_by_role('button',name='저장',exact=True).click();pg.locator('.modal').wait_for(state='detached');assert len(owner.get('/api/me').json()['settings']['resources'])==2;shot('12_resources_saved')
    mp.on('dialog',lambda d:d.accept())
    mp.get_by_role('button',name='내 예약 확인').click();mp.get_by_role('button',name='복구 코드 발급').click();mp.locator('#recovery-issued').wait_for(timeout=5000);code=mp.locator('#recovery-issued').input_value();mp.locator('#recovery-issued').evaluate('(el)=>el.value="TEST-CODE-REDACTED"');shot('19_recovery_code',mp)
    mp.get_by_role('button',name='닫기',exact=True).click()
    other=TestClient(app);mp2=b.new_page(viewport={'width':390,'height':844});page_content(mp2,other,s);mp2.get_by_text('테스트 스냅 고객센터').wait_for(timeout=5000);mp2.get_by_role('button',name='내 예약 확인').click();mp2.get_by_role('button',name='예약 불러오기').click();mp2.locator('#recovery-code').fill(code);mp2.get_by_role('button',name='예약 불러오기',exact=True).click();mp2.get_by_text('고객명: 김테스트',exact=True).wait_for(timeout=5000);shot('20_recovered_booking',mp2)
    mp2.on('dialog',lambda d:d.accept());mp2.get_by_role('button',name='복구 코드 발급').click();mp2.locator('#recovery-issued').wait_for(timeout=5000);back=mp2.locator('#recovery-issued').input_value();mp2.close();mp.get_by_role('button',name='내 예약 확인').click();mp.get_by_role('button',name='예약 불러오기').click();mp.locator('#recovery-code').fill(back);mp.get_by_role('button',name='예약 불러오기',exact=True).click();mp.get_by_text('고객명: 김테스트',exact=True).wait_for(timeout=5000);mp.get_by_role('button',name='닫기',exact=True).click()
    mp.get_by_role('button',name='내 예약 확인').click();mp.get_by_role('button',name='취소 요청',exact=True).click();mp.get_by_role('button',name='확인 및 요청').click();mp.get_by_text('취소 요청: 승인 대기',exact=True).wait_for(timeout=5000);shot('13_customer_change',mp);mp.get_by_role('button',name='닫기',exact=True).click()
    nav('calendar','일정표 보기');pg.get_by_role('button',name='승인',exact=True).click();pg.get_by_text('승인 완료',exact=True).wait_for(timeout=5000);shot('14_change_approved')
    mp.get_by_role('button',name='업무 요청',exact=True).click();mp.locator('#req-title').fill('새 촬영 견적');mp.locator('#req-detail').fill('부산 커플 스냅');mp.get_by_role('button',name='확인 및 접수',exact=True).click();mp.locator('.modal').wait_for(state='detached');nav('customers','고객·업무 관리');pg.get_by_text('새 촬영 견적',exact=True).wait_for(timeout=5000);shot('15_work_request')
    nav('agents','AI 상담원 관리');pg.locator('#agent-brand').fill('추가 상담원 B');pg.locator('#agent-faq').fill('별도 문의 => 별도 답변');pg.locator('#agent-enabled').check();pg.get_by_role('button',name='저장',exact=True).click();pg.get_by_text('별도 상담 주소:',exact=False).wait_for(timeout=5000);shot('16_extra_agent')
    nav('channels','외부 채널 연동');pg.get_by_role('button',name='메시지 테스트',exact=True).first.click();pg.locator('#external-text').fill('배송 기간?');pg.get_by_role('button',name='메시지 처리').click();pg.locator('#channel-result').get_by_text('출고 후 2일입니다.',exact=False).wait_for(timeout=5000);shot('17_naver_test');pg.get_by_role('button',name='닫기',exact=True).click()
    nav('credits','AI 교육 크레딧');pg.get_by_role('button',name='로컬 테스트 충전').click();pg.get_by_role('button',name='테스트 결제 완료').click();pg.locator('.modal').wait_for(state='detached');nav('orders','주문 및 구독 내역');pg.get_by_text('education · 1,900원',exact=True).wait_for(timeout=5000);shot('18_order_history')
    assert not errors,errors;b.close()
result={'result':'PASS','transport':'ASGI bridge; no direct HTTP browser navigation','screenshots':screens,'page_errors':errors};print(json.dumps(result,ensure_ascii=False));(OUT/'browser_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))

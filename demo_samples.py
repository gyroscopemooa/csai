"""Opt-in, removable sample conversations for isolated local demo workspaces."""
from fastapi import Depends
from urllib.parse import urlsplit
from datetime import datetime, timedelta, time as clock_time
from zoneinfo import ZoneInfo
from app import app, ident, require
from store import APP_URL, DEMO, SHARED_TEST, db, getw, one, rows, now, uid, dump, loads, entitlements, is_operator

SAMPLES = [
    ('public', 'open', False, [
        ('user', '샘플 · 가족사진 촬영을 예약하고 싶어요. 주말 오전 자리도 있나요?'),
        ('assistant', '안녕하세요. 원하시는 날짜와 인원, 촬영 장소를 알려주시면 예약 가능한 시간을 확인하겠습니다.'),
        ('user', '다음 주 토요일에 어른 4명, 아이 2명입니다. 스튜디오에서 찍고 싶어요.'),
        ('assistant', '6인 가족 촬영이군요. 오전 시간을 원하시면 희망 시작 시간도 알려주세요. 실제 예약 확정은 가능한 시간과 업체 설정을 확인한 뒤 진행됩니다.'),
        ('user', '오전 10시가 좋고, 아이가 어려서 촬영 중 쉬는 시간이 필요해요.'),
        ('assistant', '쉬는 시간이 필요한 점을 예약 메모에 남기겠습니다. 촬영 소요 시간과 휴식 가능 여부는 담당자에게 확인해 드릴게요.'),
        ('user', '가격은 얼마인가요? 원본 사진은 전부 받을 수 있나요?'),
        ('assistant', '가격과 원본 제공 범위는 업체가 등록한 상품 정보에 따라 달라집니다. 확인되지 않은 할인이나 제공 범위는 약속하지 않고 담당자에게 확인하겠습니다.'),
        ('user', '옷을 두 벌로 갈아입어도 되나요? 반려견도 한 장 같이 찍고 싶은데요.'),
        ('assistant', '의상 교체와 반려견 동반 가능 여부를 함께 확인 요청하겠습니다. 반려견 촬영이 가능한 경우 필요한 준비 사항도 안내받아 드릴게요.'),
        ('user', '주차장이 있나요? 유모차를 가져가도 되는지도 궁금합니다.'),
        ('assistant', '주차 및 유모차 이동 동선은 방문 전에 꼭 확인할 내용입니다. 업체의 공식 위치 안내와 담당자 답변을 함께 확인해 주세요.'),
        ('user', '아이가 아프면 날짜를 바꿔야 할 수도 있어요. 변경이나 취소 기준이 어떻게 되나요?'),
        ('assistant', '변경·취소 기준은 예약 상품과 업체 정책에 따라 결정됩니다. 확정 전에 적용되는 기준을 담당자가 안내하도록 요청하겠습니다.'),
        ('user', '알겠어요. 가능한 시간과 가격이 확인되면 알려주세요.'),
        ('assistant', '요청 내용을 정리했습니다: 다음 주 토요일 오전 10시, 성인 4명과 아이 2명, 스튜디오 촬영, 휴식·의상 교체·반려견 동반·주차 확인. 담당자 확인 후 답변하겠습니다.'),
        ('user', '사진 보정은 자연스럽게 해주세요. 가족 전체가 너무 인위적으로 보이는 건 싫어요.'),
        ('assistant', '자연스러운 보정을 선호하신다는 점도 메모에 추가하겠습니다. 보정 범위와 납품 일정은 담당자 확인이 필요합니다.'),
        ('user', '예약금은 언제 내나요? 카드 결제가 되나요?'),
        ('assistant', '결제 시점과 수단은 아직 확인되지 않았습니다. 결제 안내를 받기 전까지 입금이나 카드 정보를 이 채팅에 보내지 마세요.'),
        ('user', '네, 담당자 답변 기다릴게요.'),
        ('assistant', '확인해 주셔서 감사합니다. 담당자에게 전달할 항목을 한곳에 모아 두었습니다.')
    ]),
    ('naver', 'pending', True, [
        ('user', '샘플 · 네이버 톡톡에서 주문한 상품의 교환을 문의합니다.'),
        ('assistant', '교환 사유와 상품 상태를 알려주시면 업체 정책에 맞춰 접수 방법을 안내하겠습니다.'),
        ('user', '사이즈가 맞지 않아 한 치수 큰 상품으로 바꾸고 싶어요.'),
        ('assistant', '사이즈 교환 요청으로 정리했습니다. 구매처와 수령일, 상품 사용 여부를 확인해 주세요.'),
        ('user', '어제 받았고 포장만 열어 봤어요. 교환 배송비가 있나요?'),
        ('assistant', '배송비는 상품과 업체의 교환 정책에 따라 다릅니다. 등록되지 않은 금액을 임의로 안내하지 않고 담당자에게 확인하겠습니다.'),
        ('user', '교환할 사이즈 재고도 확인해 주세요.'),
        ('assistant', '재고 확인 요청을 담당자에게 전달하겠습니다. 확정 전에는 교환 완료로 안내하지 않습니다.'),
        ('staff', '샘플 담당자 메모: 교환 가능 여부와 재고를 확인 중입니다.')
    ]),
    ('kakao', 'pending', True, [
        ('user', '샘플 · 카카오톡 채널에서 환불을 문의합니다. 예약을 취소해야 할 것 같아요.'),
        ('assistant', '취소 요청을 접수하겠습니다. 예약 시점과 결제 여부에 따라 환불 조건이 달라질 수 있어 담당자 확인이 필요합니다.'),
        ('user', '아직 촬영일까지 일주일 남았는데 전액 환불이 되나요?'),
        ('assistant', '전액 환불 여부를 임의로 약속할 수 없습니다. 예약 조건과 결제 내역을 담당자가 확인하도록 전달하겠습니다.'),
        ('user', '언제 답변을 받을 수 있나요?'),
        ('assistant', '담당자 확인 요청 상태로 기록했습니다. 이 화면에서 환불을 실제 실행하거나 금액을 확정하지 않습니다.')
    ]),
    ('public', 'resolved', False, [
        ('user', '샘플 · 홈페이지 상담 링크로 가격과 위치를 문의합니다.'),
        ('assistant', '가격은 선택한 상품에 따라 달라집니다. 원하시는 촬영 종류를 알려주세요.'),
        ('user', '프로필 촬영이고 주차 가능한 곳을 찾고 있어요.'),
        ('assistant', '프로필 촬영 가격과 주차 정보는 업체가 등록한 공식 안내를 확인해 드리겠습니다.'),
        ('user', '알려주셔서 감사합니다.'),
        ('assistant', '추가로 궁금한 점이 생기면 언제든 상담 링크로 문의해 주세요.')
    ]),
    ('test', 'open', False, [
        ('user', '샘플 · 관리자 테스트: 아직 교육하지 않은 해외 배송 질문입니다.'),
        ('assistant', '해외 배송 가능 국가와 운임은 등록된 정보에서 확인되지 않습니다. 담당자 확인이 필요합니다.'),
        ('user', '이 질문을 교육 목록에 넣어 두고 싶어요.'),
        ('assistant', '확인되지 않은 정책은 추측해서 답하지 않고 교육 후보로 남깁니다.')
    ]),
    ('public', 'resolved', True, [
        ('user', '샘플 · 행사 촬영 견적을 부탁드려요. 참석자는 80명 정도입니다.'),
        ('assistant', '행사 날짜, 장소, 촬영 시간과 납품 범위를 알려주시면 견적 초안에 필요한 정보를 모으겠습니다.'),
        ('user', '금요일 오후 6시부터 9시까지 서울입니다. 사진 100장 정도가 필요해요.'),
        ('assistant', '3시간 서울 행사 촬영과 사진 100장 납품 요청으로 정리했습니다. 등록된 단가로 계산한 뒤 담당자가 최종 검토해야 합니다.'),
        ('user', '영상도 짧게 하나 넣을 수 있나요?'),
        ('assistant', '영상 촬영은 별도 옵션일 수 있습니다. 가능 여부와 단가를 확인해 견적 초안에 반영하겠습니다.'),
        ('staff', '샘플 담당자 답변: 사진 견적은 확인했고 영상 옵션은 별도 협의가 필요합니다.')
    ]),
    ('naver', 'open', False, [
        ('user', '샘플 · 네이버 톡톡에서 매장 위치와 운영 시간을 문의합니다.'),
        ('assistant', '등록된 위치와 운영 시간 정보를 확인해 안내하겠습니다.'),
        ('user', '일요일에도 상담받을 수 있나요?'),
        ('assistant', 'AI 상담 링크는 시간과 관계없이 문의를 받을 수 있지만 담당자 업무 시간은 업체 운영 시간에 따릅니다.')
    ]),
    ('kakao', 'pending', True, [
        ('user', '샘플 · 촬영 당일 서비스에 대한 불만이 있습니다.'),
        ('assistant', '불편을 겪으신 내용을 기록하고 담당자에게 전달하겠습니다. 어떤 점이 가장 문제였는지 알려주세요.'),
        ('user', '약속한 시간보다 30분 늦게 시작됐고 사진도 아직 받지 못했습니다.'),
        ('assistant', '시작 지연과 납품 지연을 각각 기록했습니다. 사실관계와 보상 여부는 담당자가 확인하겠습니다.'),
        ('user', '보상은 어떻게 되는 거죠?'),
        ('assistant', '보상 금액이나 방법은 제가 임의로 약속하지 않습니다. 담당자에게 우선 확인하도록 전달하겠습니다.')
    ]),
    ('public', 'resolved', False, [
        ('user', '샘플 · 이번 주 스튜디오 촬영 예약 가능한 시간이 있을까요?'),
        ('assistant', '예약 가능 시간을 확인했습니다. 원하시는 날짜와 시간을 선택해 주세요.'),
        ('user', '가능한 시간 중 오전 10시로 할게요. 인원은 두 명입니다.'),
        ('assistant', '예약 양식에 고객명과 연락처를 입력하고 내용을 확인해 주세요. 확인 전에는 일정이 확정되지 않습니다.'),
        ('user', '예약 내용을 확인했습니다.'),
        ('assistant', '예약이 확정되었습니다. 업체 일정표에도 같은 시간이 등록되고, 담당자에게 알림이 남습니다.')
    ])
]

# The same case follows the visitor from the inbox into the calendar and work queues.
CASES = [
    ('프로필 촬영', '배경색 선택', '회색 배경으로 촬영할 수 있나요?'),
    ('가족 촬영', '유아 의자', '두 살 아이가 앉을 의자가 있나요?'),
    ('상품 촬영', '원본 제공', '흰 배경 제품 사진의 원본도 받을 수 있나요?'),
    ('행사 촬영', '출장 범위', '행사장으로 출장 촬영이 가능한가요?'),
    ('여권 사진', '수령 방식', '인화물과 파일을 함께 받을 수 있나요?'),
    ('돌 촬영', '의상 준비', '돌 촬영용 한복을 가져가야 하나요?'),
    ('단체 촬영', '인원 변경', '예약 인원이 두 명 늘어도 되나요?'),
    ('반려동물 촬영', '동반 조건', '고양이 두 마리와 함께 갈 수 있나요?'),
    ('졸업 촬영', '날짜 변경', '졸업식 일정이 바뀌면 날짜를 옮길 수 있나요?'),
    ('공연 촬영', '납품 일정', '공연 홍보에 쓸 사진을 먼저 받을 수 있나요?'),
    ('커플 촬영', '야외 장소', '비가 오면 실내 촬영으로 바꿀 수 있나요?'),
    ('브랜드 촬영', '사용 범위', '온라인 광고에도 사진을 쓸 수 있나요?'),
]

def assistance_examples():
    combinations = [('web',), ('naver',), ('kakao',), ('web','naver'), ('web','kakao'), ('naver','kakao'), ('web','naver','kakao')]
    result = []
    for i,(service,topic,question) in enumerate(CASES):
        details = {}
        for k in combinations[i % len(combinations)]:
            details[k] = {'reference': 'shop-'+str(i+1)+'.example.com' if k=='web' else '샘플 '+service,
                          'access': '모름' if i%2 else '가능'}
            if k=='web':
                details[k]['platform'] = ('카페24','아임웹','자체 제작')[i%3]
            else:
                details[k]['existing'] = '있음' if i%2 else '없음'
        result.append({'sample':True,'status':'review' if i%2 else 'paid','items':{'details':details,'email':'shop'+str(i+1)+'@example.com'}})
    return result

def seed_admin_cases(c, ws):
    settings = loads(getw(c, ws)['settings'])
    zone = ZoneInfo(settings['timezone'])
    today = datetime.now(zone).date()
    for index, (service, topic, question) in enumerate(CASES):
        key = 'sample-admin-' + ws + '-' + str(index)
        if one(c, 'SELECT thread FROM demo_sample WHERE ws=? AND thread=?', (ws, key)):
            continue
        visitor = uid()
        stamp = now() - (len(CASES)-index)*3600
        channel = ('public','naver','kakao')[index % 3]
        c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)', (visitor, ws, now()+2592000, 'test'))
        c.execute('INSERT INTO thread(id,ws,visitor,kind,status,manual,created) VALUES(?,?,?,?,?,?,?)',
                  (key, ws, visitor, channel, ('open','pending','resolved')[index%3], 0, stamp))
        c.execute('INSERT INTO demo_sample(thread,ws) VALUES(?,?)', (key, ws))
        for offset, (role, body) in enumerate([('user','샘플 · '+question),('assistant',service+' 문의를 접수했습니다. '+topic+' 조건을 담당자가 확인하겠습니다.')]):
            c.execute('INSERT INTO message(id,ws,thread,role,body,created) VALUES(?,?,?,?,?,?)', (uid(),ws,key,role,body,stamp+offset))
        booking = uid()
        start = datetime.combine(today+timedelta(days=index+3), clock_time(10+index%6), tzinfo=zone)
        payload = {'name':'샘플 고객 '+str(index+1),'product':service,'note':question}
        c.execute('INSERT INTO booking VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (booking,ws,visitor,start.isoformat(),(start+timedelta(minutes=settings['duration'])).isoformat(),'default',dump(payload),settings['template_version'],dump(settings['fields']),('confirmed','pending','cancelled')[index%3],1,0,uid(),stamp))
        mark(c,ws,'booking',booking)
        for kind, action in [('crm','고객 상담 기록'),('tasks','담당자 확인'),('quote','견적 검토'),('leads','신규 문의'),('complaints','개선 요청')]:
            item=uid()
            c.execute('INSERT INTO work VALUES(?,?,?,?,?,?,?)',(item,ws,kind,'샘플 · '+service+' '+action,question,('open','pending','resolved')[index%3],stamp))
            c.execute('INSERT INTO work_link VALUES(?,?,?,?)',(ws,key,kind,item))
            mark(c,ws,'work',item)
        item=uid()
        c.execute('INSERT INTO unknown VALUES(?,?,?,?,?,?)',(item,ws,key,'샘플 · '+question,'open',stamp))
        mark(c,ws,'unknown',item)
        item=uid()
        c.execute('INSERT INTO event_log VALUES(?,?,?,?,?,0,?)',(item,ws,'booking','샘플 · '+service+' 예약 상태 안내',booking,stamp))
        mark(c,ws,'event',item)

def local_demo(c, ws):
    w = getw(c, ws)
    require(is_operator(w) or (DEMO and not SHARED_TEST and urlsplit(APP_URL).hostname in ('localhost', '127.0.0.1') and w['owner'].startswith('demo:')), '로컬 데모 계정에서만 샘플을 관리할 수 있습니다.', 403)

def mark(c, ws, kind, item):
    c.execute('INSERT OR IGNORE INTO demo_sample_entity(ws,kind,id) VALUES(?,?,?)', (ws, kind, item))

def seed_related(c, ws):
    samples = rows(c, 'SELECT t.id,t.visitor FROM thread t JOIN demo_sample d ON d.thread=t.id WHERE t.ws=? AND d.ws=? ORDER BY t.created', (ws, ws))
    if len(samples) < len(SAMPLES):
        return
    if not one(c, "SELECT id FROM demo_sample_entity WHERE ws=? AND kind='unknown'", (ws,)):
        unknown_id=uid()
        c.execute('INSERT INTO unknown VALUES(?,?,?,?,?,?)',(unknown_id,ws,samples[4]['id'],'샘플 · 해외 배송 가능 국가와 운임은 어떻게 되나요?','open',now()))
        mark(c,ws,'unknown',unknown_id)
    # Alerts and learning examples are available even in the free local demo.
    for index, (kind, title, sample_index) in enumerate([
        ('new','샘플 · 새로운 촬영 문의 접수',0),
        ('manual_message','샘플 · 직접 상담 중 새 고객 메시지',1),
        ('handoff_urgent','샘플 · 긴급 담당자 확인 요청',7),
        ('unknown','샘플 · 미학습 배송 질문 접수',4),
        ('booking','샘플 · 예약 확정 안내',8),
        ('handoff','샘플 · 환불 조건 검토 요청',2),
    ]):
        event_id='demo-alert-'+ws+'-'+str(index)
        if not one(c,'SELECT id FROM event_log WHERE ws=? AND id=?',(ws,event_id)):
            c.execute('INSERT INTO event_log VALUES(?,?,?,?,?,0,?)',(event_id,ws,kind,title,samples[sample_index]['id'],now()-index*180))
            mark(c,ws,'event',event_id)
    if 'calendar' not in entitlements(getw(c, ws)):
        return
    if one(c, "SELECT id FROM demo_sample_entity WHERE ws=? AND kind='booking'", (ws,)):
        return
    settings = loads(getw(c, ws)['settings'])
    local_now = datetime.now(ZoneInfo(settings['timezone']))
    start = datetime.combine((local_now + timedelta(days=2)).date(), clock_time(10), tzinfo=ZoneInfo(settings['timezone']))
    end = start + timedelta(minutes=settings['duration'])
    booking_id = uid()
    payload = {'name':'샘플 고객','contact':'010-0000-0000','location':'스튜디오','people':'2','product':'프로필 촬영','source':'CS AI 상담 링크','note':'예약 확인 후 자동 확정된 화면 예시'}
    c.execute('INSERT INTO booking VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (booking_id,ws,samples[-1]['visitor'],start.isoformat(),end.isoformat(),'default',dump(payload),settings['template_version'],dump(settings['fields']),'confirmed',1,0,uid(),now()))
    mark(c, ws, 'booking', booking_id)
    for index, kind, title, details, status in [
        (1,'tasks','샘플 · 네이버 교환 요청 확인','고객의 사이즈 교환 요청. 재고와 교환 배송비를 담당자가 확인합니다.','pending'),
        (2,'complaints','샘플 · 카카오 환불 문의','예약 취소 및 환불 조건 확인 요청. AI는 환불 금액을 확정하지 않았습니다.','open'),
        (5,'quote','샘플 · 행사 촬영 견적 검토','3시간 행사 촬영, 사진 100장 및 영상 옵션 견적을 담당자가 검토합니다.','resolved')]:
        work_id=uid()
        c.execute('INSERT INTO work VALUES(?,?,?,?,?,?,?)',(work_id,ws,kind,title,details,status,now()))
        c.execute('INSERT INTO work_link VALUES(?,?,?,?)',(ws,samples[index]['id'],kind,work_id))
        mark(c,ws,'work',work_id)
    event_id=uid()
    c.execute('INSERT INTO event_log VALUES(?,?,?,?,?,0,?)',(event_id,ws,'booking','샘플 · AI 상담 예약 확정',booking_id,now()))
    mark(c,ws,'event',event_id)

def seed_samples(c, ws):
    local_demo(c, ws)
    existing = one(c, 'SELECT COUNT(*) n FROM demo_sample WHERE ws=?', (ws,))['n']
    base = now() - 8 * 86400
    for index, (kind, status, manual, messages) in enumerate(SAMPLES):
        if index < existing:
            continue
        visitor = uid(); thread = uid(); created = base + index * 86400
        c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)', (visitor, ws, now() + 86400 * 30, 'test'))
        c.execute('INSERT INTO thread(id,ws,visitor,kind,status,manual,created) VALUES(?,?,?,?,?,?,?)', (thread, ws, visitor, kind, status, int(manual), created))
        c.execute('INSERT INTO demo_sample(thread,ws) VALUES(?,?)', (thread, ws))
        for pos, (role, body) in enumerate(messages):
            c.execute('INSERT INTO message(id,ws,thread,role,body,created) VALUES(?,?,?,?,?,?)', (uid(), ws, thread, role, body, created + pos * 120))
    # A recent, independent sample makes relative time and live inbox visible.
    for index, age in enumerate((2,12,38)):
        key='sample-recent-'+ws+'-'+str(index)
        if one(c,'SELECT thread FROM demo_sample WHERE ws=? AND thread=?',(ws,key)):
            continue
        visitor=uid(); stamp=now()-age*60
        c.execute('INSERT INTO visitor(token,ws,expires,kind) VALUES(?,?,?,?)',(visitor,ws,now()+2592000,'test'))
        c.execute('INSERT INTO thread(id,ws,visitor,kind,status,manual,created) VALUES(?,?,?,?,?,?,?)',(key,ws,visitor,'public','open',0,stamp))
        c.execute('INSERT INTO demo_sample(thread,ws) VALUES(?,?)',(key,ws))
        c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(uid(),ws,key,'user','샘플 · '+CASES[index][2],stamp))
    seed_related(c, ws)
    w = getw(c, ws)
    if is_operator(w) or w['owner'].endswith(':developer'):
        seed_admin_cases(c, ws)
    total = one(c,'SELECT COUNT(*) n FROM demo_sample WHERE ws=?',(ws,))['n']
    return {'count': total, 'created': total > existing}

@app.post('/api/demo/samples')
def add_samples(ws=Depends(ident)):
    with db(True) as c:
        return seed_samples(c, ws)

@app.post('/api/demo/samples/{thread}/message')
def sample_message(thread:str,body:dict,ws=Depends(ident)):
    # Isolated simulation: no AI call, real visitor, notifications or channel delivery.
    with db(True) as c:
        local_demo(c,ws)
        t=one(c,'SELECT t.id,t.kind FROM thread t JOIN demo_sample d ON d.thread=t.id AND d.ws=t.ws WHERE t.ws=? AND t.id=?',(ws,thread))
        require(t and t['kind'] in ('public','test','naver','telegram'),'직접 답변을 지원하는 샘플 상담만 체험할 수 있습니다.',409)
        role=body.get('role');value=body.get('message')
        require(role in ('staff','user') and isinstance(value,str) and 0<len(value.strip())<=2000,'메시지를 1~2000자로 입력하세요.',422)
        c.execute('INSERT INTO message(id,ws,thread,role,body,created) VALUES(?,?,?,?,?,?)',(uid(),ws,thread,role,value.strip(),now()))
        if role=='staff':c.execute("UPDATE thread SET manual=1,status='open' WHERE ws=? AND id=?",(ws,thread))
        else:c.execute("UPDATE thread SET status='open' WHERE ws=? AND id=?",(ws,thread))
        return {'ok':True}

@app.delete('/api/demo/samples')
def remove_samples(ws=Depends(ident)):
    with db(True) as c:
        local_demo(c, ws)
        for item in rows(c, 'SELECT kind,id FROM demo_sample_entity WHERE ws=?', (ws,)):
            if item['kind']=='booking':
                c.execute('DELETE FROM booking WHERE ws=? AND id=?',(ws,item['id']))
            elif item['kind']=='work':
                c.execute('DELETE FROM work_link WHERE ws=? AND work=?',(ws,item['id']))
                c.execute('DELETE FROM work WHERE ws=? AND id=?',(ws,item['id']))
            elif item['kind']=='event':
                c.execute('DELETE FROM event_log WHERE ws=? AND id=?',(ws,item['id']))
            elif item['kind']=='unknown':
                c.execute('DELETE FROM unknown WHERE ws=? AND id=?',(ws,item['id']))
        c.execute('DELETE FROM demo_sample_entity WHERE ws=?',(ws,))
        found = rows(c, 'SELECT t.id,t.visitor FROM thread t JOIN demo_sample d ON d.thread=t.id WHERE d.ws=? AND t.ws=?', (ws, ws))
        for item in found:
            c.execute('DELETE FROM demo_sample WHERE thread=? AND ws=?', (item['id'], ws))
            c.execute('DELETE FROM message WHERE thread=? AND ws=?', (item['id'], ws))
            c.execute('DELETE FROM thread WHERE id=? AND ws=?', (item['id'], ws))
            c.execute('DELETE FROM visitor WHERE token=? AND ws=?', (item['visitor'], ws))
        return {'removed': len(found)}

@app.get('/api/demo/feature-examples')
def feature_examples(ws=Depends(ident)):
    with db() as c:
        local_demo(c, ws)
        w=getw(c,ws)
        require(is_operator(w) or w['owner'].endswith(':developer'), '관리자 샘플입니다.', 403)
    return [{'service':service,'topic':topic,'question':question} for service,topic,question in CASES]

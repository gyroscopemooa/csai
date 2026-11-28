from store import CAT

def test_future_integrations_are_visible_but_not_billable():
    names = {item['name'] for item in CAT['roadmap']}
    assert {'홈페이지 회원정보 연동', '인스타그램 DM', '이메일 수신·답변',
            'LINE 공식 계정', '텔레그램 봇', '페이스북 메신저',
            'Android 앱 SDK', 'iOS 앱 SDK', '전화 상담 연동',
            '위챗', 'AI 전화 상담'} <= names
    assert all('price' not in item and 'id' not in item for item in CAT['roadmap'])
    assert CAT['plans'][1]['price'] == 8900
    assert next(item for item in CAT['addons'] if item['id'] == 'naver')['price'] == 4900

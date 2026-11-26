from tests.test_app import owner, post

def test_policy_documents_and_separate_acceptance():
    c = owner()
    docs = c.get('/api/policies').json()
    assert docs['draft'] is True
    for item in docs['documents']:
        page = c.get(item['url'])
        assert page.status_code == 200 and '개발용 초안' in page.text
    version = docs['version']
    assert c.post('/api/policies/accept', json={'version': version, 'terms': True, 'privacy': True, 'ai': True}).status_code == 422
    result = post(c, '/api/policies/accept', {'version': version, 'terms': True, 'privacy': True, 'ai': True, 'dpa': True, 'marketing': False})
    assert result['accepted'] is True
    assert c.get('/api/me').json()['policy']['accepted'] is True

def test_auto_booking_requires_separate_acknowledgement():
    c = owner()
    assert c.patch('/api/settings', json={'modes': {'booking': 'auto'}}).status_code == 403
    v = c.get('/api/policies/status').json()['version']
    assert c.post('/api/policies/automation-ack', json={'version': v, 'errors': True, 'accuracy': True}).status_code == 422
    post(c, '/api/policies/automation-ack', {'version': v, 'errors': True, 'accuracy': True, 'approval': True})
    assert c.patch('/api/settings', json={'modes': {'booking': 'auto'}}).status_code == 200

def test_published_policy_blocks_direct_api_until_accepted(monkeypatch):
    import policies
    c = owner()
    monkeypatch.setattr(policies, 'ENFORCED', True)
    assert c.get('/api/me').status_code == 200
    assert c.patch('/api/settings', json={'brand': '우회 시도'}).status_code == 403
    v = c.get('/api/policies/status').json()['version']
    post(c, '/api/policies/accept', {'version': v, 'terms': True, 'privacy': True, 'ai': True, 'dpa': True})
    assert c.patch('/api/settings', json={'brand': '확인 완료'}).status_code == 200

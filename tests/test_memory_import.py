import io
import json
import zipfile

from tests.test_app import owner


def test_memory_preflight_has_no_raw_messages_or_training_side_effects():
    conversation = {
        'title': 'Example', 'create_time': 1735689600, 'current_node': 'a',
        'mapping': {'a': {'message': {'author': {'role': 'user'}, 'content': {
            'content_type': 'text', 'parts': ['PRIVATE PAYLOAD'],
        }}}},
    }
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as out:
        out.writestr('conversations.json', json.dumps([conversation, conversation]))
    client = owner()
    credits = client.get('/api/me').json()['credits']
    jobs = client.get('/api/training').json()
    result = client.post('/api/memory-import/preview', content=archive.getvalue())
    assert result.status_code == 200
    assert result.json()['duplicates'] == 1
    assert len(result.json()['conversations']) == 1
    assert 'PRIVATE PAYLOAD' not in result.text
    filtered = client.post('/api/memory-import/preview?start=2026-01-01', content=archive.getvalue())
    assert filtered.json()['excluded'] == 2
    assert client.get('/api/me').json()['credits'] == credits
    assert client.get('/api/training').json() == jobs


def test_title_category_hints_are_not_ai_classification():
    from memory_import import category_hint
    assert '사업·상품·서비스' in category_hint('사업 상품 계획')
    assert '개인정보 주의' in category_hint('가족 건강')
    assert category_hint('unclassified text') == ['미분류']

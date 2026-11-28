from test_app import app, TestClient
import importlib
from special_evaluation_store import EvaluationStore
from special_local_fixture import approved_diagnostics

server = importlib.import_module('app')
PATH = '/api/special/preview'


def local_client(developer=False):
    c = TestClient(app, base_url='http://127.0.0.1:3000')
    assert c.get('/auth/demo').status_code == 200
    if developer:
        r = c.post('/api/demo/view', json={'mode': 'developer'})
        assert r.status_code == 200, r.text
    return c


def test_special_access_and_no_charge(tmp_path, monkeypatch):
    store = EvaluationStore(str(tmp_path / 'fixture.db'))
    monkeypatch.setattr(server, 'special_fixture_store', lambda: store)
    anon = TestClient(app, base_url='http://127.0.0.1:3000')
    assert anon.get(PATH).status_code == 401
    free = local_client()
    assert free.get(PATH).status_code == 403
    assert free.post(PATH+'/evaluate', json={}).status_code == 403
    c = local_client(True)
    before = c.get('/api/me').json()
    initial = c.get(PATH).json()
    assert initial['available_for_purchase'] is False
    assert initial['packages']['special_all'] == 99000
    assert initial['report']['status'] == 'no_verified_results'
    for _ in range(2):
        assert c.post(PATH+'/evaluate', json={}).status_code == 200
    result = c.get(PATH).json()
    assert result['report_kind'] == 'synthetic_retrieval_checks'
    assert result['report']['latest']['evaluated_cases'] == 4
    assert len(result['report']['trend']) == 1
    after = c.get('/api/me').json()
    for field in ('credits', 'remaining', 'plan', 'addons', 'entitlements', 'published'):
        assert before[field] == after[field]
    assert local_client(True).get(PATH).json()['report']['status'] == 'no_verified_results'


def test_special_remote_and_shared_denied(monkeypatch):
    c = local_client(True)
    remote = TestClient(app, base_url='https://example.invalid')
    remote.cookies.set('csai_session', c.cookies.get('csai_session'))
    assert remote.get(PATH).status_code == 403
    assert remote.post(PATH+'/evaluate', json={}).status_code == 403
    monkeypatch.setattr(server, 'SHARED_TEST', True)
    assert c.get(PATH).status_code == 403


def test_diagnostics_aggregate_only():
    data = {'faq': [{'q': '배송 기간', 'a': '2일'}, {'q': '배송기간?', 'a': '3일'}, {'q': '배송 기간', 'a': '2일'}]}
    assert approved_diagnostics(data) == {'status': 'measured', 'total': 3, 'distinct_questions': 1,
        'duplicate_count': 1, 'invalid_count': 0, 'review_group_count': 1}
    assert approved_diagnostics({'faq': 'bad'}) == {'status': 'unavailable'}

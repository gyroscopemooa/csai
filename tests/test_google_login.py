from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient

from test_app import app


def test_google_login_returns_to_same_workspace(monkeypatch):
    import app as csai
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
    monkeypatch.setattr(csai, 'APP_URL', 'http://127.0.0.1:3000')
    token_requests = []

    def exchange(url, *, data, timeout):
        assert url == 'https://oauth2.googleapis.com/token'
        assert data['redirect_uri'] == csai.APP_URL + '/auth/google/callback'
        token_requests.append(data['code'])
        return httpx.Response(200, json={'access_token': 'test-access'})

    def userinfo(url, *, headers, timeout):
        assert url == 'https://openidconnect.googleapis.com/v1/userinfo'
        assert headers['Authorization'] == 'Bearer test-access'
        return httpx.Response(200, json={'sub': 'login-regression-user'})

    monkeypatch.setattr(csai.httpx, 'post', exchange)
    monkeypatch.setattr(csai.httpx, 'get', userinfo)
    client = TestClient(app)
    slugs = []
    for code in ('first-login', 'second-login'):
        start = client.get('/auth/google', follow_redirects=False)
        location = urlsplit(start.headers['location'])
        assert location.hostname == 'accounts.google.com'
        state = parse_qs(location.query)['state'][0]
        assert client.cookies['oauth_state'] == state
        path = '/auth/google/callback'
        assert client.get(path, params={'code': code, 'state': 'wrong'}).status_code == 403
        auth = client.get(path, params={'code': code, 'state': state}, follow_redirects=False)
        assert auth.is_redirect
        me = client.get('/api/me')
        assert me.status_code == 200
        slugs.append(me.json()['slug'])
        assert client.get(path, params={'code': code, 'state': state}).status_code == 403
        assert client.post('/api/logout').status_code == 204
        assert client.get('/api/me').status_code == 401

    assert slugs[0] == slugs[1]
    assert token_requests == ['first-login', 'second-login']

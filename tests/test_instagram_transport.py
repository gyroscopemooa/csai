from integrations import instagram_transport as ig
import pytest
def test_profile(monkeypatch):
    monkeypatch.setenv('INSTAGRAM_GRAPH_VERSION','v27.0')
    class R:
        is_success=True
        content=b'{}'
        def json(self):return {'id':'1234','username':'test_user'}
    def get(url,**kwargs):
        assert url=='https://graph.instagram.com/v27.0/me'
        assert kwargs['params']=={'fields':'id,username'}
        assert kwargs['headers']['Authorization']=='Bearer '+'a'*30
        assert kwargs['follow_redirects'] is False
        return R()
    monkeypatch.setattr(ig.httpx,'get',get)
    assert ig.profile('a'*30)=={'id':'1234','username':'test_user'}
    with pytest.raises(ig.InstagramError):ig.profile('https://bad.test')

from integrations import line_transport as lt
import pytest
def test_bot_info_and_reply(monkeypatch):
    class Resp:
        is_success=True
        status_code=200
        def json(self):return {'userId':'U'+'a'*32}
    token='a'*30;calls=[]
    monkeypatch.setattr(lt.httpx,'get',lambda *a,**kw:Resp())
    assert lt.bot_info(token)['id']=='U'+'a'*32
    monkeypatch.setattr(lt.httpx,'post',lambda *a,**kw:calls.append((a,kw)) or Resp())
    lt.reply(token,'abc123','안녕하세요')
    assert calls[0][0][0]==lt.ROOT+'/message/reply'
    assert calls[0][1]['json']['replyToken']=='abc123'
    assert not calls[0][1]['follow_redirects']
    with pytest.raises(lt.LineError):lt.reply(token,'bad/path','hello')

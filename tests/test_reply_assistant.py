from test_app import owner,post
import ai

def test_reply_assistant_three_styles(monkeypatch):
    c=owner()
    monkeypatch.setattr(ai,'KEY','')
    payload={'message':'안녕하세요','styles':['짧게','친근하게','정중하게'],'intent':'확인 중','client':'reply-three','confirmed':True}
    assert c.post('/api/reply-assistant',json=payload|{'confirmed':False}).status_code==422
    first=post(c,'/api/reply-assistant',payload)
    assert first['demo'] and len(first['drafts'])==3
    assert post(c,'/api/reply-assistant',payload)==first
    assert c.post('/api/reply-assistant',json=payload|{'message':'다른 내용'}).status_code==409

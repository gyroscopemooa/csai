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


def test_email_reply_medium_and_idempotency(monkeypatch):
    c=owner()
    monkeypatch.setattr(ai,'KEY','mock')
    calls=[]
    def mock_call(model,prompt,context,**kwargs):
        calls.append(context)
        assert context['medium']=='email'
        assert not context['faq'] and not context['facts']
        assert '메일 본문' in prompt
        return {'drafts':['안녕하세요. 확인하겠습니다.','연락 감사합니다. 확인할게요.','안녕하십니까. 확인 후 회신드리겠습니다.']},{}
    monkeypatch.setattr(ai,'call',mock_call)
    payload={'medium':'email','message':'제목: 예약 문의\n본문: 일정 확인 부탁드립니다.','client':'email-draft','confirmed':True}
    assert c.post('/api/reply-assistant',json=payload|{'medium':'unsupported'}).status_code==422
    first=post(c,'/api/reply-assistant',payload)
    assert not first['demo'] and len(first['drafts'])==3
    assert post(c,'/api/reply-assistant',payload)==first
    assert len(calls)==1
    assert c.post('/api/reply-assistant',json=payload|{'medium':'message'}).status_code==409

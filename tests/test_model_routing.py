import ai
from app import MODEL_RATES

class Response:
    status_code=200
    def json(self):
        return {'status':'completed','output':[{'content':[{'type':'output_text','text':'{}'}]}],'usage':{}}

def test_same_model_separate_effort(monkeypatch):
    model='gpt-6.2-sol'; sent=[]
    monkeypatch.setattr(ai,'KEY','mock')
    monkeypatch.setattr(ai,'TRAIN',model)
    monkeypatch.setattr(ai,'CHAT',model)
    monkeypatch.setattr(ai,'TRAIN_EFFORT','high')
    monkeypatch.setattr(ai,'CHAT_EFFORT','low')
    monkeypatch.setattr(ai.httpx,'post',lambda *a,**kw:sent.append(kw['json']) or Response())
    ai.call(ai.CHAT,'chat',{})
    ai.train('training',[],{'tone':'formal'})
    ai.call(ai.CHAT,'booking',{},effort_override='low')
    assert [r['reasoning']['effort'] for r in sent]==['low','high','low']
    assert all(r['model']==model for r in sent)
    assert sent[1]['max_output_tokens']==ai.TRAIN_OUTPUT_CAP

def test_legacy_none_and_standard_rates(monkeypatch):
    sent=[]
    monkeypatch.setattr(ai,'KEY','mock')
    monkeypatch.setattr(ai,'CHAT_EFFORT','none')
    monkeypatch.setattr(ai.httpx,'post',lambda *a,**kw:sent.append(kw['json']) or Response())
    ai.call('gpt-6.2-sol','chat',{})
    assert sent[0]['reasoning']['effort']=='low'
    assert MODEL_RATES['gpt-6.2-sol']==(2.0,10.0,0.10)

def test_live_estimate_includes_repeated_guidance_and_cap(monkeypatch):
    monkeypatch.setattr(ai,'KEY','mock')
    text='a'*24000
    assert ai.estimate(text,[],'b'*12000)>ai.estimate(text,[])
    assert ai.estimate(text,[])>=2*ai.TRAIN_OUTPUT_CAP/200

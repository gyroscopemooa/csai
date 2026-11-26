from test_app import owner,post
import ai
from store import DEFAULT

def test_chunk_training_uses_later_text_and_conflicts(monkeypatch):
    monkeypatch.setattr(ai,'KEY','mock');calls=[]
    def fake(*args,**kwargs):
        calls.append(args[2]);return {'style':'정중','rules':['규칙 '+str(len(calls))],'faq':[{'q':'가격','a':str(len(calls))}],'conflicts':[]},{'input_tokens':500,'output_tokens':100}
    monkeypatch.setattr(ai,'call',fake);r,n=ai.train('가'*12000+'마지막 내용',[],{'tone':'정중'});assert len(calls)==2 and '마지막 내용' in calls[1]['source'];assert len(r['rules'])==2 and r['conflicts'];assert n==2 and n<=ai.estimate('가'*12000+'마지막 내용',[])

def test_bounded_history():
    history=[{'role':'user','body':'a'*2000}]*20
    r=ai.bounded_history(history);assert sum(len(x['body']) for x in r)<=6500 and len(r)<=8

def test_owner_guidance_is_separate_from_pasted_customer_messages(monkeypatch):
    monkeypatch.setattr(ai,'KEY','mock');seen=[]
    def fake(*args,**kwargs):
        seen.append(args[2]);return {'style':'짧게','rules':[],'faq':[],'conflicts':[]},{'input_tokens':100,'output_tokens':50}
    monkeypatch.setattr(ai,'call',fake)
    ai.train('고객: 환불해줘\n나: 담당자 확인 후 안내드릴게요.',[],{'tone':'정중'},'이모지 사용 금지')
    assert seen[0]['owner_guidance']=='이모지 사용 금지'
    assert '고객: 환불해줘' in seen[0]['source']
    assert '이모지 사용 금지' not in seen[0]['source']

def test_published_training_style_overrides_initial_preset(monkeypatch):
    monkeypatch.setattr(ai,'KEY','mock');seen=[]
    def fake(*args,**kwargs):
        seen.append(args[2]);return {'reply':'안녕하세요','unknown':False},{'input_tokens':100,'output_tokens':30}
    monkeypatch.setattr(ai,'call',fake)
    ai.answer('안녕하세요',[],DEFAULT|{'emoji':True},[],{'style':'AI 티 안 나게 답하고 이모지 사용 금지','rules':[]},set())
    assert seen[0]['style']=='AI 티 안 나게 답하고 이모지 사용 금지'
    assert seen[0]['emoji'] is False

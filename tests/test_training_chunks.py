from test_app import owner,post
import ai

def test_chunk_training_uses_later_text_and_conflicts(monkeypatch):
    monkeypatch.setattr(ai,'KEY','mock');calls=[]
    def fake(*args,**kwargs):
        calls.append(args[2]);return {'style':'정중','rules':['규칙 '+str(len(calls))],'faq':[{'q':'가격','a':str(len(calls))}],'conflicts':[]},{'input_tokens':500,'output_tokens':100}
    monkeypatch.setattr(ai,'call',fake);r,n=ai.train('가'*12000+'마지막 내용',[],{'tone':'정중'});assert len(calls)==2 and '마지막 내용' in calls[1]['source'];assert len(r['rules'])==2 and r['conflicts'];assert n==2 and n<=ai.estimate('가'*12000+'마지막 내용',[])

def test_bounded_history():
    history=[{'role':'user','body':'a'*2000}]*20
    r=ai.bounded_history(history);assert sum(len(x['body']) for x in r)<=6500 and len(r)<=8

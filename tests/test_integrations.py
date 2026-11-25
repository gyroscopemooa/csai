from integrations.channels import naver_in,naver_out,kakao_in,kakao_out

def test_naver_contract():
    p={'event':'send','user':'visitor-a','textContent':{'text':'문의'}};assert naver_in(p).text=='문의';assert naver_out('visitor-a','답변')['textContent']['text']=='답변';assert naver_in({'event':'open'}) is None

def test_kakao_contract():
    p={'userRequest':{'user':{'id':'visitor-b'},'utterance':'문의'}};assert kakao_in(p).user=='visitor-b';assert kakao_out('답변')['template']['outputs'][0]['simpleText']['text']=='답변';assert kakao_in({}) is None

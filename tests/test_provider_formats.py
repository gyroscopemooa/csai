import hashlib
import hmac
import base64
from integrations.provider_formats import (
    telegram_verify, meta_verify, line_verify, telegram_in, meta_in,
    line_in, telegram_out, meta_out, line_out,
)

def test_provider_authentication_rejects_tampering():
    raw=b'{"message":"hello"}'
    sig=hmac.new(b'test-secret',raw,hashlib.sha256)
    meta='sha256='+sig.hexdigest()
    line=base64.b64encode(sig.digest()).decode()
    assert meta_verify('test-secret',raw,meta)
    assert line_verify('test-secret',raw,line)
    assert not meta_verify('test-secret',raw+b' ',meta)
    assert not line_verify('other',raw,line)
    assert not meta_verify('',raw,meta)
    assert not line_verify('test-secret',raw,None)
    assert telegram_verify('secret','secret')
    assert not telegram_verify('secret','wrong')
    assert not telegram_verify('','')

def test_telegram_private_text_only():
    p={'update_id':123,'message':{'chat':{'id':7,'type':'private'},'from':{'id':7,'is_bot':False},'text':'Hi'}}
    m=telegram_in(p,'bot-1')[0]
    assert (m.user,m.event_id,m.account,m.text)==('7','123','bot-1','Hi')
    assert telegram_out(m.user,'hello')=={'chat_id':'7','text':'hello'}
    p['message']['chat']['type']='group'
    assert telegram_in(p,'bot-1')==[]
    assert telegram_in({'edited_message':{}},'bot-1')==[]

def test_meta_account_binding_and_echo_exclusion():
    item={'sender':{'id':'customer'},'recipient':{'id':'owner'},'message':{'mid':'m1','text':'Hi'}}
    for channel,kind in [('instagram','instagram'),('messenger','page')]:
        p={'object':kind,'entry':[{'id':'owner','messaging':[item]}]}
        m=meta_in(p,channel,'owner')[0]
        assert (m.user,m.event_id,m.account)==('customer','m1','owner')
        assert meta_in(p,channel,'another')==[]
        assert meta_out(m.user,'reply',channel)['recipient']=={'id':'customer'}
        item['message']['is_echo']=True
        assert meta_in(p,channel,'owner')==[]
        del item['message']['is_echo']
        item['recipient']['id']='another'
        assert meta_in(p,channel,'owner')==[]
        item['recipient']['id']='owner'
    assert meta_in(None,'instagram','owner')==[]

def test_line_active_direct_text_and_reply():
    event={'type':'message','mode':'active','webhookEventId':'evt','replyToken':'token','source':{'type':'user','userId':'u1'},'message':{'type':'text','text':'Hi'}}
    p={'destination':'bot','events':[event]}
    m=line_in(p,'bot')[0]
    assert m.user=='u1' and m.event_id=='evt'
    assert line_out(m.reply_token,'hello')=={'replyToken':'token','messages':[{'type':'text','text':'hello'}]}
    assert line_in(p,'other')==[]
    event['mode']='standby'
    assert line_in(p,'bot')==[]
    event['mode']='active'
    event['source']['type']='group'
    assert line_in(p,'bot')==[]

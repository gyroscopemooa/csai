"""Regression cases for paid quota and operator/invitation entitlements.
Use the existing isolated SQLite test fixture; no OAuth or live AI calls.
"""
import store
from test_app import owner, post, patch, public, future, TestClient, app
from app import session_response

def google_owner(name):
    c=TestClient(app)
    response=session_response("google:"+name)
    # Response is a redirect; extract only the cookie value, not a live OAuth credential.
    c.cookies.set("csai_session",response.headers["set-cookie"].split(";",1)[0].split("=",1)[1])
    return c

def test_paid_quota_blocks_next_message():
    c=owner()
    post(c,"/api/demo/billing",{"plan":"mini"})
    patch(c,{"price":"100원"})
    with store.db(True) as db:
        ws=store.one(db,"SELECT ws FROM session WHERE token=?",(c.cookies.get("csai_session"),))["ws"]
        w=store.getw(db,ws)
        db.execute("INSERT INTO usage VALUES(?,?,99) ON CONFLICT(ws,period) DO UPDATE SET n=99",(ws,store.usage_period(w)))
    token=post(c,"/api/session",{"test":True})["token"]
    p={"token":token,"message":"가격은?","clientMessageId":"last"}
    assert post(c,"/api/chat",p)["remaining"]==0
    assert c.post("/api/chat",json=p|{"clientMessageId":"over"}).status_code==402
    assert post(c,"/api/chat",p)["remaining"]==0

def test_operator_public_access_without_paid_plan(monkeypatch):
    monkeypatch.setattr(store,"OPERATOR_OWNERS",{"google:regression-operator"})
    c=google_owner("regression-operator")
    me=c.get("/api/me").json()
    assert me["operator"] and me["public_access"] and me["quota"]==10000
    patch(c,{"enabled":True})
    assert c.get("/api/qr").status_code==200
    public(c)

def test_invite_entitlements_and_sandbox_lock(monkeypatch):
    monkeypatch.setattr(store,"OPERATOR_OWNERS",{"google:regression-invite-operator"})
    op=google_owner("regression-invite-operator")
    c=google_owner("regression-invited")
    invite=post(op,"/api/operator/invites",{"chat_limit":50,"credit_limit":100,"days":14})
    post(c,"/api/invites/accept",{"code":invite["code"]})
    me=c.get("/api/me").json()
    assert me["remaining"]==50 and me["credits"]==100 and me["quota"]==50
    assert set(me["entitlements"])=={"calendar","auto_booking","change_booking"}
    assert me["public_access"] and not me["sandbox_allowed"]
    assert c.post("/api/demo/billing",json={"plan":"enterprise"}).status_code==403
    assert c.post("/api/billing/orders",json={"kind":"subscription","plan":"enterprise","client":"trial-bypass"}).status_code==403
    patch(c,{"enabled":True,"price":"100원","fields":[{"key":"name","label":"이름","type":"text","required":True}]})
    u,token=public(c)
    assert post(u,"/api/chat",{"token":token,"message":"가격은?","clientMessageId":"trial-one"})["remaining"]==49
    assert c.get("/api/qr").status_code==200
    assert c.get("/api/stats").status_code==403
    # Cancelled reservations count toward the 10-booking lifetime allowance.
    with store.db(True) as db:
        ws=store.one(db,"SELECT ws FROM session WHERE token=?",(c.cookies.get("csai_session"),))["ws"]
        for _ in range(10):
            db.execute("INSERT INTO booking VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(store.uid(),ws,"staff","2030-01-01T00:00:00+00:00","2030-01-01T01:00:00+00:00","default","{}",1,"[]","cancelled",1,0,store.uid(),store.now()))
    assert c.get("/api/me").json()["trial"]["bookings_remaining"]==0
    assert c.post("/api/bookings",json={"start":future(),"payload":{"name":"테스트"}}).status_code==402
    post(op,"/api/operator/invites/"+invite["id"]+"/revoke",{})
    assert not c.get("/api/me").json()["public_access"]
    assert c.get("/api/public/"+me["slug"]).status_code==404
    assert c.get("/api/me").json()["remaining"]==0
    assert c.post("/api/demo/billing",json={"plan":"enterprise"}).status_code==403

def test_shared_sandbox_is_operator_only(monkeypatch):
    c=owner()
    monkeypatch.setattr(store,"SHARED_TEST",True)
    assert c.post("/api/billing/orders",json={"kind":"subscription","plan":"lite","client":"shared-test"}).status_code==403
    assert c.post("/api/demo/billing",json={"plan":"lite"}).status_code==403

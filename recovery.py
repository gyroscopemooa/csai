"""One-time booking recovery capability; no phone identity verification or chat disclosure."""
from app import app, visitor, require, limit
from store import *
from fastapi import Request
import hashlib
from datetime import datetime, timezone

def digest(code): return hashlib.sha256(code.encode()).hexdigest()
with db(True) as c:
    c.execute('CREATE TABLE IF NOT EXISTS booking_recovery(booking TEXT PRIMARY KEY REFERENCES booking(id) ON DELETE CASCADE, ws TEXT NOT NULL, secret_hash TEXT NOT NULL UNIQUE, expires INTEGER NOT NULL)')

@app.post('/api/customer/bookings/{i}/recovery-code')
def issue(i:str, body:dict, req:Request):
    limit('recover-issue:'+str(req.client.host if req.client else 'unknown'),30)
    with db(True) as c:
        v=visitor(c,body.get('token',''),kind='public');require(not v.get('agent'),'브랜드별 예약 분리 준비 중',409);w=getw(c,v['ws']);require('calendar' in entitlements(w),'일정 기능 비활성화');b=one(c,"SELECT * FROM booking WHERE id=? AND ws=? AND visitor=? AND status IN ('confirmed','pending','pending_payment')",(i,v['ws'],v['token']));require(b,'내 예약이 없습니다.',404)
        end=int(datetime.fromisoformat(b['end']).timestamp());require(end>now(),'지난 일정은 복구 코드를 발급할 수 없습니다.',409)
        code=secrets.token_urlsafe(24);expires=min(end+86400*7,now()+86400*365)
        c.execute('INSERT INTO booking_recovery VALUES(?,?,?,?) ON CONFLICT(booking) DO UPDATE SET secret_hash=excluded.secret_hash,expires=excluded.expires',(i,v['ws'],digest(code),expires))
    return {'code':code,'expires':expires}

@app.post('/api/customer/bookings/recover')
def recover(body:dict,req:Request):
    limit('recover:'+str(req.client.host if req.client else 'unknown'),15)
    code=body.get('code');require(isinstance(code,str) and 24<=len(code)<=100,'유효하지 않은 복구 코드',422)
    with db(True) as c:
        v=visitor(c,body.get('token',''),kind='public');require(not v.get('agent'),'브랜드별 예약 분리 준비 중',409);w=getw(c,v['ws']);require(w['enabled'] and 'calendar' in entitlements(w),'일정 기능 비활성화')
        r=one(c,'SELECT * FROM booking_recovery WHERE ws=? AND secret_hash=? AND expires>?',(v['ws'],digest(code.strip()),now()));require(r,'유효하지 않거나 사용된 복구 코드입니다.',404)
        b=one(c,"SELECT * FROM booking WHERE ws=? AND id=? AND status IN ('confirmed','pending','pending_payment')",(v['ws'],r['booking']));require(b,'복구 가능한 예약 없음',404)
        c.execute('UPDATE booking SET visitor=? WHERE ws=? AND id=?',(v['token'],v['ws'],b['id']))
        c.execute('UPDATE booking_change SET visitor=? WHERE ws=? AND booking=?',(v['token'],v['ws'],b['id']))
        c.execute('DELETE FROM booking_recovery WHERE booking=?',(b['id'],))
    return {'ok':True,'booking':b['id']}

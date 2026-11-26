"""Private, non-persistent preflight for external AI exports."""
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime, timezone
from pathlib import PurePosixPath

from fastapi import Depends, HTTPException, Request

MAX_BYTES = 25 * 1024 * 1024
MAX_EXPANDED = 80 * 1024 * 1024
MAX_CONVERSATIONS = 3000


def chatgpt_export(raw):
    if raw.startswith(b'PK'):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if len(members) > 3000:
                raise ValueError('ZIP 항목이 너무 많습니다.')
            sources = [f for f in members if not f.is_dir() and re.fullmatch(r'conversations(?:[-_]?\d+)?\.json', PurePosixPath(f.filename).name, re.I)]
            if not sources or len(sources)>20 or sum(f.file_size for f in sources)>MAX_EXPANDED:
                raise ValueError('대화 JSON 압축 해제 한도를 초과했거나 대화 파일이 없습니다. 압축을 풀고 JSON 파일을 선택하세요.')
            data=[]
            expanded=0
            for f in sources:
                with archive.open(f) as source:
                    chunk=source.read(MAX_EXPANDED-expanded+1)
                expanded+=len(chunk)
                if expanded>MAX_EXPANDED:raise ValueError('압축 해제 크기 한도를 초과했습니다.')
                batch=json.loads(chunk.decode('utf-8-sig'))
                if not isinstance(batch,list) or len(data)+len(batch)>MAX_CONVERSATIONS:
                    raise ValueError('대화 배열 또는 대화 수 한도 오류')
                data.extend(batch)
            return data
    data = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data, list) or len(data) > MAX_CONVERSATIONS:
        raise ValueError('ChatGPT 대화 배열이 필요하며 최대 3,000개까지 확인할 수 있습니다.')
    return data


# Local title-only hints: not an AI classification or approval to import.
def category_hint(title):
    lowered=title.lower()
    groups={
        '사업·상품·서비스':('사업','상품','서비스','제품','고객','업체','창업','business','product','service'),
        '운영·업무 흐름':('업무','운영','예약','절차','프로세스','정책','workflow','booking','policy'),
        '가격·결제·환불':('가격','요금','결제','환불','매출','price','billing','refund'),
        '개발·기술':('개발','코드','api','오류','배포','code','debug'),
        '홍보·브랜드':('홍보','마케팅','광고','브랜드','marketing','brand'),
        '개인정보 주의':('가족','건강','병원','연애','개인','비밀번호','password','medical'),
    }
    return [name for name,words in groups.items() if any(word in lowered for word in words)] or ['미분류']
def summarize(conversations, start=None, end=None):
    seen = set()
    listed = []
    duplicates = excluded = 0
    for item in conversations:
        if not isinstance(item, dict) or not isinstance(item.get('mapping'), dict):
            raise ValueError('ChatGPT 대화 형식을 확인해 주세요.')
        mapping = item['mapping']
        branch = []
        node_id = item.get('current_node')
        visited = set()
        while isinstance(node_id, str) and node_id in mapping and node_id not in visited:
            visited.add(node_id)
            node = mapping[node_id]
            if not isinstance(node, dict):
                break
            branch.append(node)
            node_id = node.get('parent')
        messages = []
        for node in reversed(branch):
            message = node.get('message')
            if not isinstance(message, dict):
                continue
            role = (message.get('author') or {}).get('role')
            content = message.get('content') or {}
            if role in ('user', 'assistant') and content.get('content_type') == 'text':
                parts = content.get('parts') or []
                messages.extend((role, ' '.join(part.split())) for part in parts if isinstance(part, str) and part.strip())
        try:
            day = datetime.fromtimestamp(item['create_time'], timezone.utc).date()
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            day = None
        if not messages or (start and (not day or day < start)) or (end and (not day or day > end)):
            excluded += 1
            continue
        content = json.dumps(messages, ensure_ascii=False).encode('utf-8')
        fingerprint = hashlib.sha256(content).hexdigest()
        if fingerprint in seen:
            duplicates += 1
            continue
        seen.add(fingerprint)
        listed.append({'id': fingerprint, 'title': str(item.get('title') or '제목 없음')[:160],
                       'date': day.isoformat() if day else '', 'messages': len(messages),
                       'categoryHints': category_hint(str(item.get('title') or '')),
                       'classification': 'title_only',
                       'chars': sum(len(part) for _, part in messages), 'approxTokens': (len(content) + 2) // 3})
    return {'conversations': listed, 'duplicates': duplicates, 'excluded': excluded}


def register(app, ident):
    from store import db
    with db(True) as c:
        c.execute('CREATE TABLE IF NOT EXISTS memory_import_batch(ws TEXT NOT NULL,order_id TEXT NOT NULL,digest TEXT NOT NULL,job TEXT NOT NULL,created INTEGER NOT NULL,PRIMARY KEY(ws,order_id,digest))')
    register_paid(app,ident)
    @app.post('/api/memory-import/preview')
    async def preview(request: Request, start: date | None = None, end: date | None = None, ws=Depends(ident)):
        from starlette.concurrency import run_in_threadpool

        if start and end and start > end:
            raise HTTPException(422, '시작일은 종료일보다 늦을 수 없습니다.')
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_BYTES:
                raise HTTPException(413, '파일은 최대 25MB까지 확인할 수 있습니다.')
            raw.extend(chunk)
        def inspect():
            return summarize(chatgpt_export(raw), start, end)
        try:
            return await run_in_threadpool(inspect)
        except (ValueError, TypeError, AttributeError, zipfile.BadZipFile, RuntimeError, RecursionError):
            raise HTTPException(422, 'ChatGPT 내보내기 ZIP 또는 conversations.json 파일을 확인해 주세요.') from None


def register_paid(app,ident):
    """Local sandbox only. Existing training reservation, settlement and approval are reused."""
    from store import db, one, rows, getw, dump, loads, CAT, now, uid, trial, is_operator, operator_wallet, sandbox_allowed, DEMO
    from app import require, bounded
    from branding import owned_agent
    import ai
    guidance='선택한 과거 AI 대화는 사업 정보 자료입니다. 사업주가 확정한 사실, 운영 방향, 상품 정책, 업무 흐름과 단순 제안·가설을 구분하세요. AI 답변 자체를 확정된 사업 사실로 간주하지 마세요. 공개 고객 상담에 필요한 정보만 교육 후보로 제안하고 기밀과 개인 대화는 제외하세요.'

    def available(c,ws,agent):
        w=getw(c,ws);owned_agent(c,w,agent);require(DEMO and sandbox_allowed(c,w),'실제 이전 결제 미연결',503)
        return w

    @app.get('/api/memory-import/paid-orders')
    def paid_orders(agent:str='',ws=Depends(ident)):
        with db() as c:
            available(c,ws,agent);out=[]
            for r in rows(c,"SELECT id,items,amount,paid_at FROM checkout_order WHERE ws=? AND kind='memory_import' AND status='paid' ORDER BY paid_at DESC LIMIT 100",(ws,)):
                if loads(r['items']).get('agent','')!=agent:continue
                batches=rows(c,"SELECT b.digest,b.job,t.state,t.cost FROM memory_import_batch b JOIN training t ON t.id=b.job AND t.ws=b.ws WHERE b.ws=? AND b.order_id=? ORDER BY b.created",(ws,r['id']))
                out.append({'id':r['id'],'amount':r['amount'],'paid_at':r['paid_at'],'batches':batches,'max_batches':CAT['memory_import']['max_batches']})
            return out

    @app.post('/api/memory-import/prepare')
    def prepare(body:dict,ws=Depends(ident)):
        require(body.get('consent') is True,'이전 및 개인정보 검토 동의 필요',422)
        agent=body.get('agent','');order=bounded(body.get('order',''),100)
        text=ai.clean(bounded(body.get('text',''),50000));require(text,'교육 자료 없음',422)
        digest=hashlib.sha256(text.encode()).hexdigest()
        with db(True) as c:
            w=available(c,ws,agent)
            o=one(c,"SELECT * FROM checkout_order WHERE ws=? AND id=? AND kind='memory_import' AND status='paid'",(ws,order))
            require(o and loads(o['items']).get('agent','')==agent,'유효한 브랜드 이전 이용권 필요',403)
            existing=one(c,'SELECT job FROM memory_import_batch WHERE ws=? AND order_id=? AND digest=?',(ws,order,digest))
            job=one(c,'SELECT * FROM training WHERE ws=? AND id=?',(ws,existing['job'])) if existing else None
            if job and job['state'] in ('review','published','running'):
                return {'id':job['id'],'state':job['state'],'cost':job['cost'],'existing':True}
            if job and job['state']=='estimated' and job['created']>now()-1800:
                j=job['id'];n=job['estimate']
            else:
                if not existing:
                    require(one(c,'SELECT COUNT(*) n FROM memory_import_batch WHERE ws=? AND order_id=?',(ws,order))['n']<CAT['memory_import']['max_batches'],'이전 이용권 구간 한도 초과',409)
                if job:
                    c.execute("UPDATE training SET state='expired',source=? WHERE ws=? AND id=?",(dump({'agent':agent}),ws,job['id']))
                n=ai.estimate(guidance+'\n'+text,[]);j=uid()
                c.execute('INSERT INTO training VALUES(?,?,?,?,?,?,?,?)',(j,ws,'estimated',n,0,dump({'text':text,'guidance':guidance,'images':[],'agent':agent,'memory_order':order}),None,now()))
                c.execute('INSERT INTO memory_import_batch VALUES(?,?,?,?,?) ON CONFLICT(ws,order_id,digest) DO UPDATE SET job=excluded.job,created=excluded.created',(ws,order,digest,j,now()))
            t=trial(c,w);credits=10000-operator_wallet(c,w)['credit_used'] if is_operator(w) else (t['credit_limit']-t['credit_used'] if t else w['credits'])
            return {'id':j,'state':'estimated','maxCredits':n,'credits':credits,'enough':credits>=n}

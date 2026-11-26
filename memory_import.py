"""Private, non-persistent preflight for external AI exports."""
import hashlib
import io
import json
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
            sources = [f for f in members if not f.is_dir() and PurePosixPath(f.filename).name == 'conversations.json']
            if len(sources) != 1 or sources[0].file_size > MAX_EXPANDED:
                raise ValueError('ZIP에 처리 가능한 conversations.json이 하나 있어야 합니다.')
            with archive.open(sources[0]) as source:
                raw = source.read(MAX_EXPANDED + 1)
            if len(raw) > MAX_EXPANDED:
                raise ValueError('압축 해제 크기 한도를 초과했습니다.')
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

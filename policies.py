"""Versioned development policy drafts and auditable workspace acknowledgements."""
import html
import os
from fastapi import HTTPException, Depends
from fastapi.responses import HTMLResponse
from store import db, one, now
from policy_content import DOCUMENTS, business_info, launch_identity_complete

VERSION = 'draft-2026-11-26-3'
APPROVED = os.getenv('POLICY_APPROVED_VERSION') == VERSION and launch_identity_complete() and os.getenv('CSAI_PRIVACY_FLOW_APPROVED') == '1' and os.getenv('CSAI_REFUND_RULES_APPROVED') == '1'
if os.getenv('POLICY_ENFORCE') == '1' and not APPROVED:
    raise RuntimeError('Approve and version the final policy text before POLICY_ENFORCE=1')
ENFORCED = os.getenv('POLICY_ENFORCE') == '1' and APPROVED

def status(c, ws):
    accepted = one(c, 'SELECT * FROM policy_acceptance WHERE ws=? AND version=?', (ws, VERSION))
    ack = one(c, 'SELECT * FROM automation_ack WHERE ws=?', (ws,))
    return {'version': VERSION, 'draft': not APPROVED, 'accepted': bool(accepted),
            'required': ENFORCED and not accepted,
            'automation_accepted': bool(ack and ack['version'] == VERSION)}

def register(app, ident, require):
    @app.get('/api/policies')
    def list_policies():
        return {'version': VERSION, 'draft': not APPROVED,
                'business': business_info(),
                'documents': [{'slug': k, 'title': v[0], 'url': '/policies/'+k} for k, v in DOCUMENTS.items()]}

    @app.get('/policies/{slug}', response_class=HTMLResponse)
    def policy_page(slug: str):
        if slug not in DOCUMENTS:
            raise HTTPException(404, '정책을 찾을 수 없습니다.')
        title, sections = DOCUMENTS[slug]
        body = ''.join('<section><h2>'+html.escape(heading)+'</h2>'+''.join('<p>'+html.escape(paragraph)+'</p>' for paragraph in paragraphs)+'</section>' for heading, paragraphs in sections)
        info = business_info()
        contact = '<footer><strong>CS AI 운영 사업자</strong><p>'+html.escape(info['name'] or '사업자 정보 확정 전')+'</p>'+(('<p>문의: <a href="mailto:'+html.escape(info['email'], quote=True)+'">'+html.escape(info['email'])+'</a></p>') if info['email'] else '')+'</footer>'
        links = '<nav aria-label="다른 정책">'+''.join('<a href="/policies/'+html.escape(key, quote=True)+'">'+html.escape(value[0])+'</a>' for key,value in DOCUMENTS.items())+'</nav>'
        style='body{font:16px/1.75 system-ui,sans-serif;color:#202632;max-width:780px;padding:24px;margin:auto}a{color:#2879e5}h1{line-height:1.25}h2{font-size:21px;margin:0 0 12px}section{padding:20px 0;border-top:1px solid #e5e8eb}p{margin:12px 0}nav{display:flex;flex-wrap:wrap;gap:8px 16px;margin:18px 0 36px}footer{border-top:1px solid #e5e8eb;margin-top:28px;padding:20px 0;color:#596579}.draft{padding:12px 16px;border-radius:10px;background:#fff5df;color:#7a5300}'
        draft = '<p class="draft"><strong>개발용 초안 · 법률 검토 및 운영 정보 확정 전</strong><br>실제 결제·정식 서비스에 적용되는 최종 조건이 아닙니다.</p>' if not APPROVED else ''
        return HTMLResponse('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · CS AI</title><style>'+style+'</style><a href="/">CS AI로 돌아가기</a><h1>'+html.escape(title)+'</h1>'+draft+links+body+contact+'</html>')

    @app.get('/api/policies/status')
    def policy_status(ws=Depends(ident)):
        with db() as c:
            return status(c, ws)

    @app.post('/api/policies/accept')
    def policy_accept(body: dict, ws=Depends(ident)):
        require(body.get('version') == VERSION, '정책 버전이 변경되었습니다. 다시 확인하세요.', 409)
        require(all(body.get(k) is True for k in ('terms', 'privacy', 'ai', 'dpa')), '필수 정책을 각각 확인하세요.', 422)
        with db(True) as c:
            c.execute('INSERT INTO policy_acceptance(ws,version,terms,privacy,ai,dpa,marketing,accepted) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(ws,version) DO UPDATE SET terms=excluded.terms,privacy=excluded.privacy,ai=excluded.ai,dpa=excluded.dpa,marketing=excluded.marketing,accepted=excluded.accepted', (ws, VERSION, 1, 1, 1, 1, int(body.get('marketing') is True), now()))
            return status(c, ws)

    @app.post('/api/policies/automation-ack')
    def automation_accept(body: dict, ws=Depends(ident)):
        require(body.get('version') == VERSION and all(body.get(k) is True for k in ('errors', 'accuracy', 'approval')), '자동화 위험과 승인 범위를 각각 확인하세요.', 422)
        with db(True) as c:
            c.execute('INSERT INTO automation_ack(ws,version,accepted) VALUES(?,?,?) ON CONFLICT(ws) DO UPDATE SET version=excluded.version,accepted=excluded.accepted', (ws, VERSION, now()))
            return status(c, ws)

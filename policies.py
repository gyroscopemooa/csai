"""Versioned development policy drafts and auditable workspace acknowledgements."""
import html
import os
from fastapi import HTTPException, Depends
from fastapi.responses import HTMLResponse
from store import db, one, now

VERSION = 'draft-2026-11-26-2'
APPROVED = os.getenv('POLICY_APPROVED_VERSION') == VERSION
if os.getenv('POLICY_ENFORCE') == '1' and not APPROVED:
    raise RuntimeError('Approve and version the final policy text before POLICY_ENFORCE=1')
ENFORCED = os.getenv('POLICY_ENFORCE') == '1' and APPROVED
DOCUMENTS = {
    'terms': ('서비스 이용약관', [
        '서비스 역할: CS AI는 업체의 고객 상담과 관련 업무를 지원하는 소프트웨어를 제공합니다. 업체와 고객 사이의 상품 판매·서비스 제공 계약은 원칙적으로 해당 업체가 체결·이행합니다. CS AI가 직접 판매자 또는 결제 당사자가 되는 거래는 별도로 표시하고 해당 법적 의무를 부담합니다.',
        'AI 결과: AI 답변·분석·자동화 결과에는 오류, 누락 또는 부정확한 정보가 포함될 수 있습니다. 업체는 교육 자료, 가격, 예약 조건과 환불 정책을 정확하게 관리하고 중요한 계약·견적·결제·환불·보상 결정을 담당자가 검토해야 합니다.',
        '책임 판단: 업체가 입력·승인한 정보나 설정에 따른 문제와 CS AI의 시스템 결함, 개인정보 사고 또는 구독료 결제 오류는 원인별로 구분합니다. 각 당사자의 귀책사유와 적용 법령에 따라 손해배상 범위를 판단합니다.',
        '책임 제한 검토: 일반적인 과실에 대한 합리적인 배상 한도는 유료 이용료, 청구 기간, 예상 가능한 손해와 서비스 위험을 고려하여 출시 전 별도로 정합니다. 이 초안은 한도액을 정하거나 고객의 법정 권리를 제한하지 않습니다. 고의·중대한 과실 및 법령상 제한할 수 없는 책임은 한도 적용 대상에서 제외합니다.',
        '베타·외부 연동: 시험 기능의 제한과 제3자 서비스 장애 가능성을 사전에 알립니다. CS AI 자신의 귀책사유로 발생한 책임을 외부 서비스 이용 사실만으로 면제하지 않습니다.',
        '요금, 해지, 환불, 장애 보상 및 분쟁 접수 절차는 실제 결제·운영 방식에 맞춰 출시 전 별도 확정이 필요합니다.'
    ]),
    'privacy': ('개인정보처리방침', [
        '업체 계정 식별정보, 교육 자료, 상담 기록, 예약 정보 및 사용량을 서비스 제공·보안·고객 지원을 위해 처리합니다.',
        '업체의 최종 고객 정보에 대해서는 업체와 CS AI의 역할을 구분하고 처리위탁 조건을 별도로 정합니다.',
        '보관 기간, 삭제 절차, 국외 이전 대상·국가·방법, 문의처는 실제 인프라와 계약을 확인한 뒤 출시 전에 명시해야 합니다.',
        '선택적 마케팅 수신은 서비스 이용과 분리해 동의를 받습니다.'
    ]),
    'ai': ('AI 이용 및 책임 안내', [
        '상담은 생성형 AI가 업체가 입력한 자료와 설정을 기반으로 수행할 수 있습니다. 사실관계가 불명확한 경우 담당자 확인으로 전환해야 합니다.',
        'AI 결과에는 부정확하거나 누락된 내용이 있을 수 있습니다. 업체는 제공 자료와 설정을 최신 상태로 유지하고 중요한 결과를 검토합니다.',
        '등록되지 않은 할인, 환불, 보상, 법적 약속 또는 금전 지급은 AI가 확정할 수 없습니다. 관련 요청은 담당자가 결정합니다.',
        '고객에게 AI 사용 사실을 상담 전에 알리고, 필요한 경우 생성 결과임을 표시합니다.'
    ]),
    'dpa': ('개인정보 처리위탁 조건 초안', [
        '업체는 고객정보의 처리 목적과 범위를 결정하고, CS AI는 계약된 상담·예약·기록 관리 목적에 한해 해당 정보를 처리합니다.',
        '접근 통제, 사고 통지, 재위탁, 국외 이전, 보관·반환·삭제, 감사 및 계약 종료 조항은 실제 공급업체와 데이터 흐름을 확인해 별도 계약으로 확정해야 합니다.'
    ]),
    'automation': ('AI 자동화 및 승인 정책', [
        '일반 문의와 등록 정보 안내는 업체 설정에 따라 자동 처리할 수 있습니다.',
        '예약 자동 확정은 업체가 별도 위험 안내를 확인하고 기능을 켠 경우에만 허용됩니다. 예약 조건과 재고·중복 여부를 업체가 관리합니다.',
        '견적 확정, 실제 환불, 할인·보상 약속 및 손해배상 합의는 담당자 승인 전 자동으로 실행하지 않습니다.',
        '자동화로 생긴 손해의 책임은 입력 정보, 승인·운영 과정, 시스템 결함 및 적용 법령을 함께 검토해 판단합니다.'
    ])
}

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
                'documents': [{'slug': k, 'title': v[0], 'url': '/policies/'+k} for k, v in DOCUMENTS.items()]}

    @app.get('/policies/{slug}', response_class=HTMLResponse)
    def policy_page(slug: str):
        if slug not in DOCUMENTS:
            raise HTTPException(404, '정책을 찾을 수 없습니다.')
        title, paragraphs = DOCUMENTS[slug]
        body = ''.join('<p>'+html.escape(p)+'</p>' for p in paragraphs)
        return HTMLResponse('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · CS AI</title><style>body{font:16px/1.75 system-ui,sans-serif;color:#202632;max-width:760px;padding:24px;margin:auto}a{color:#3182f6}p{margin:18px 0}</style><a href="/">CS AI로 돌아가기</a><h1>'+html.escape(title)+'</h1>'+(('<p><strong>개발용 초안 · 법률 검토 및 운영 정보 확정 전</strong></p>') if not APPROVED else '')+body+'</html>')

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

"""Opt-in, deterministic FAQ candidate retrieval. No network, storage or model calls."""
import os
import re
import unicodedata

# These are domain-specific query expansions, not semantic embeddings.
_CONCEPTS = {
    'delivery_time': ('배송기간', '배송소요', '배송언제', '언제와', '언제도착', '며칠걸', '도착예정', '배송일정', '언제받', '언제오'),
    'delivery_fee': ('배송비', '택배비', '배송요금', '무료배송', '운송비'),
    'refund': ('환불', '반품', '돈돌려', '결제취소', '환급'),
    'exchange': ('교환', '바꿔주', '사이즈변경'),
    'opening': ('영업시간', '운영시간', '몇시오픈', '몇시열', '몇시닫', '문여는시간'),
    'location': ('위치', '주소', '어디에있', '어디로가', '찾아가는길'),
    'reservation': ('예약', '방문신청', '일정신청'),
    'stock': ('재고', '품절', '남아있', '구매가능'),
}
_INCOMPATIBLE = (frozenset(('delivery_time', 'delivery_fee')), frozenset(('refund', 'exchange')))


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', str(value)).casefold() if c.isalnum())


def concepts(value):
    text = normalize(value)
    return frozenset(key for key, terms in _CONCEPTS.items() if any(term in text for term in terms))


def grams(value):
    value = normalize(value)
    return {value[i:i + 2] for i in range(len(value) - 1)}


def similarity(query, question):
    a, b = grams(query), grams(question)
    return len(a & b) / max(1, len(a))


def identity(faq):
    return normalize(faq['q']), str(faq['a'])


def select_faq(query, candidates, legacy, limit=5):
    """Rank approved FAQ candidates only; never produce a customer answer.

    Preserve the first two legacy candidates and fail conservatively on weak or
    conflicting intent matches. The existing model and policy checks remain authoritative.
    """
    limit = max(0, min(int(limit), 5))
    if not limit:
        return []
    old = list(legacy)[:limit]
    q = normalize(query)
    intent = concepts(query)
    if len(q) < 2 or not intent:
        return old
    # Specific numeric identifiers must not be broadened to another item.
    if re.search(r'\d', q):
        return old
    ranked = []
    seen = set()
    for index, row in enumerate(candidates):
        if not isinstance(row, dict) or not isinstance(row.get('q'), str) or not isinstance(row.get('a'), str):
            continue
        if not row['q'].strip() or not row['a'].strip():
            continue
        key = identity(row)
        if key in seen:
            continue
        seen.add(key)
        other = concepts(row['q'])
        if not (intent & other):
            continue
        if any((intent & pair) and (other & pair) and (intent & pair) != (other & pair) for pair in _INCOMPATIBLE):
            continue
        overlap = similarity(query, row['q'])
        rank = (len(intent & other) / len(intent), overlap, -index)
        ranked.append((rank, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked:
        return old
    # Never replace an exact approved question with a paraphrase candidate.
    if any(normalize(row['q']) == q for row in old):
        return old
    out, keys = [], set()
    def add(row):
        key = identity(row)
        if len(out) < limit and key not in keys:
            out.append(row)
            keys.add(key)
    for row in old[:2]:
        add(row)
    for _, row in ranked[:2]:
        add(row)
    for row in old[2:]:
        add(row)
    return out


def maybe_select_faq(query, candidates, legacy, *, live_model):
    """Off by default; preserve legacy output on failure. No added API usage."""
    if os.getenv('CSAI_KNOWLEDGE_RETRIEVAL', 'off') != 'pilot' or not live_model:
        return legacy
    try:
        return select_faq(query, candidates, legacy)
    except Exception:
        return legacy

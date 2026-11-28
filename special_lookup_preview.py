"""Local-only approved FAQ retrieval comparison; never answers a customer."""
from knowledge_retrieval import select_faq, normalize, similarity


def compare_lookup(published, query):
    if not isinstance(query, str) or not normalize(query) or len(query) > 200:
        raise ValueError('invalid query')
    rows = published.get('faq', []) if isinstance(published, dict) else None
    if not isinstance(rows, list) or len(rows) > 500:
        return {'status': 'unavailable', 'legacy': [], 'pilot': []}
    approved = [dict(q=r['q'], a=r['a']) for r in rows if isinstance(r, dict)
                and all(isinstance(r.get(k), str) and r[k].strip() for k in ('q', 'a'))
                and len(r['q']) <= 1200 and len(r['a']) <= 4000 and normalize(r['q'])]
    ranked = sorted(approved, key=lambda row: similarity(query, row['q']), reverse=True)[:5]
    legacy = [row for row in ranked if similarity(query, row['q']) > .12]
    exact = [row for row in approved if normalize(query) == normalize(row['q'])]
    pilot = exact[:5] if exact else select_faq(query, approved, legacy)
    # Only source questions are shown, not the answers or generated customer text.
    return {'status': 'compared', 'legacy': [row['q'] for row in legacy],
            'pilot': [row['q'] for row in pilot], 'approved_count': len(approved)}

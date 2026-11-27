"""Conservative contextual FAQ selection and offline knowledge diagnostics."""
import os
import re
from knowledge_retrieval import concepts, normalize, select_faq

_FOLLOWUP = re.compile(r'^(그럼|그러면|그건|그거|그것|거기|그리고|그 경우)')
_BLOCK = re.compile(r'\d|아니|말고|취소|환불|변경|결제|주문|개인정보|전화번호|주소|예약|가격|금액')


def contextual_candidates(query, history, approved, legacy, *, enabled=False):
    """Only augment evidence for short follow-ups; never change the actual message."""
    if not enabled or not isinstance(query, str) or len(query) > 60:
        return legacy
    if not _FOLLOWUP.match(query.strip()) or _BLOCK.search(query) or concepts(query):
        return legacy
    try:
        # Use only the most recent previous customer message, not model output.
        prior = next((h['body'] for h in reversed(history[-6:]) if h['role'] == 'user'), '')
        if not isinstance(prior, str) or len(prior) > 200 or _BLOCK.search(prior):
            return legacy
        intent = concepts(prior)
        if len(intent) != 1 or not intent <= {'delivery_time', 'delivery_fee', 'opening', 'stock'}:
            return legacy
        return select_faq(prior + ' ' + query, approved, legacy)
    except (KeyError, TypeError, ValueError, AttributeError):
        return legacy


def maybe_contextual_candidates(query, history, approved, legacy, *, live_model):
    if not live_model or os.getenv('CSAI_CONTEXT_RETRIEVAL', 'off') != 'pilot':
        return legacy
    return contextual_candidates(query, history, approved, legacy, enabled=True)


def knowledge_diagnostics(approved):
    """Offline review candidates, not proof of contradiction or auto-edit actions."""
    if len(approved) > 500:
        raise ValueError('FAQ limit exceeded')
    groups, invalid, duplicate = {}, [], 0
    for i, row in enumerate(approved):
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip() for k in ('q', 'a')):
            invalid.append(i)
            continue
        key = normalize(row['q'])
        if not key:
            invalid.append(i)
            continue
        answers = groups.setdefault(key, {})
        # Preserve punctuation and case in answers (e.g. prices and URLs).
        answer = row['a'].strip()
        if answer in answers:
            duplicate += 1
        answers.setdefault(answer, []).append(i)
    conflicts = [tuple(i for indices in answers.values() for i in indices)
                 for answers in groups.values() if len(answers) > 1]
    return {'total': len(approved), 'distinct_questions': len(groups),
            'duplicate_count': duplicate, 'invalid_indices': invalid,
            'review_groups': conflicts}

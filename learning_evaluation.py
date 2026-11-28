"""Offline evaluation of curated cases and aggregate knowledge gaps."""
from dataclasses import dataclass
from collections import Counter
import hashlib
import json


@dataclass(frozen=True)
class Case:
    id: str
    topic: str
    expected_unknown: bool
    required_evidence: tuple = ()


@dataclass(frozen=True)
class Observation:
    case_id: str
    unknown: bool
    evidence: tuple = ()


def evaluate(cases, observations):
    """Missing cases count as failures; no generated text quality claims."""
    if not 1 <= len(cases) <= 500 or len(observations) > 500:
        raise ValueError('invalid suite bounds')
    by_id = {}
    for c in cases:
        if not isinstance(c, Case) or not c.id or not c.topic or c.id in by_id or type(c.expected_unknown) is not bool:
            raise ValueError('invalid case')
        by_id[c.id] = c
    seen, passed, gaps, failed = set(), 0, Counter(), []
    for o in observations:
        if not isinstance(o, Observation) or o.case_id not in by_id or o.case_id in seen or type(o.unknown) is not bool:
            raise ValueError('invalid observation')
        seen.add(o.case_id)
        c = by_id[o.case_id]
        if o.unknown == c.expected_unknown and set(c.required_evidence) <= set(o.evidence):
            passed += 1
        else:
            failed.append(c.id)
            if o.unknown and not c.expected_unknown:
                gaps[c.topic] += 1
    missing = sorted(set(by_id) - seen)
    suite = hashlib.sha256(json.dumps(sorted((c.id, c.topic, c.expected_unknown, sorted(set(c.required_evidence))) for c in cases), ensure_ascii=False).encode()).hexdigest()
    return {'suite': suite, 'total': len(cases), 'observed': len(seen), 'passed': passed,
            'failed': sorted(failed + missing), 'missing': missing, 'gap_candidates': dict(sorted(gaps.items())),
            'check_pass_rate': passed / len(cases)}


def compare(before, after):
    if before['suite'] != after['suite'] or before['total'] != after['total']:
        raise ValueError('incomparable suites')
    if before['observed'] != before['total'] or after['observed'] != after['total']:
        raise ValueError('incomplete evaluation')
    old, new = set(before['failed']), set(after['failed'])
    return {'delta': after['check_pass_rate'] - before['check_pass_rate'],
            'regressions': sorted(new - old), 'improved': sorted(old - new)}

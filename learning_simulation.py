"""Isolated simulation runner and human-reviewed learning suggestions."""
from dataclasses import dataclass
from collections import Counter
import hashlib
import json


@dataclass(frozen=True)
class Scenario:
    id: str
    topic: str
    prompt: str
    expected_unknown: bool
    evidence: tuple = ()
    forbidden_evidence: tuple = ()


def run_simulation(scenarios, *, workspace, revision, evaluator_version, evaluate=None,
                   enabled=False, max_cases=0, max_bytes=0):
    if enabled is not True:
        return None
    if not all(isinstance(x, str) and 0 < len(x) <= 256 for x in (workspace, revision, evaluator_version)):
        raise ValueError('scope required')
    if type(max_cases) is not int or type(max_bytes) is not int or not 1 <= max_cases <= 100 or not 1 <= max_bytes <= 100000:
        raise ValueError('invalid budget')
    if not 1 <= len(scenarios) <= max_cases or not callable(evaluate):
        raise ValueError('invalid simulation request')
    ids = set()
    size = 0
    for s in scenarios:
        if not isinstance(s, Scenario) or not all(isinstance(x, str) and x.strip() for x in (s.id, s.topic, s.prompt)):
            raise ValueError('invalid scenario')
        if s.id in ids or type(s.expected_unknown) is not bool or not isinstance(s.evidence, tuple) or not all(isinstance(e, str) and e for e in s.evidence):
            raise ValueError('invalid scenario metadata')
        if not isinstance(s.forbidden_evidence, tuple) or not all(isinstance(e, str) and e for e in s.forbidden_evidence) or set(s.evidence) & set(s.forbidden_evidence):
            raise ValueError('invalid forbidden evidence')
        ids.add(s.id)
        size += len(s.prompt.encode('utf-8'))
    if size > max_bytes:
        raise ValueError('input budget exceeded')
    suite = hashlib.sha256(json.dumps(sorted((s.id, s.topic, s.prompt, s.expected_unknown, sorted(set(s.evidence)), sorted(set(s.forbidden_evidence))) for s in scenarios), ensure_ascii=False).encode()).hexdigest()
    outcomes, gaps = [], Counter()
    for s in scenarios:
        try:
            result = evaluate(s.prompt)
            if not isinstance(result, dict) or type(result.get('unknown')) is not bool:
                raise ValueError('invalid result')
            evidence = result.get('evidence', ())
            if not isinstance(evidence, (list, tuple)) or not all(isinstance(e, str) for e in evidence):
                raise ValueError('invalid evidence')
            passed = (result['unknown'] == s.expected_unknown and set(s.evidence) <= set(evidence)
                      and not set(s.forbidden_evidence) & set(evidence))
            status = 'passed' if passed else 'failed'
            if result['unknown'] and not s.expected_unknown:
                gaps[s.topic] += 1
        except Exception:
            # Stop on execution errors; do not retry or spend on remaining cases.
            outcomes.append((s.id, 'error'))
            break
        outcomes.append((s.id, status))
    complete = len(outcomes) == len(scenarios) and all(status != 'error' for _, status in outcomes)
    return {'workspace': workspace, 'revision': revision, 'evaluator_version': evaluator_version,
            'suite': suite, 'total': len(scenarios), 'outcomes': outcomes, 'complete': complete,
            'passed': sum(status == 'passed' for _, status in outcomes),
            'gap_candidates': dict(gaps) if complete else {}}


def review_suggestions(report, *, workspace, revision):
    if not report or report.get('complete') is not True or (report.get('workspace'), report.get('revision')) != (workspace, revision):
        return []
    return [{'topic': topic, 'failed_cases': count, 'status': 'owner_review_required'}
            for topic, count in sorted(report['gap_candidates'].items(), key=lambda item: (-item[1], item[0]))]

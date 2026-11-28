"""Offline, opt-in memory selection; never automatically extract or persist PII."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryFact:
    workspace: str
    customer: str
    key: str
    value: str
    approved_at: int
    expires_at: int
    approved: bool = False


def current_memory(facts, *, workspace, customer, now, consent=False, enabled=False):
    if not enabled or consent is not True or not workspace or not customer:
        return {}
    if len(facts) > 500 or type(now) is not int:
        return {}
    latest = {}
    for fact in facts:
        if not isinstance(fact, MemoryFact) or (fact.workspace, fact.customer) != (workspace, customer):
            continue
        if fact.approved is not True or fact.key not in {'language', 'response_length'}:
            continue
        if type(fact.approved_at) is not int or type(fact.expires_at) is not int:
            continue
        if fact.approved_at > now or fact.expires_at <= fact.approved_at:
            continue
        # Keep newest record even if expired, so old values cannot resurrect.
        previous = latest.get(fact.key)
        if previous is None or fact.approved_at > previous.approved_at:
            latest[fact.key] = fact
        elif fact.approved_at == previous.approved_at and fact != previous:
            return {}  # ambiguous revision: fail closed
    allowed = {'language': {'ko', 'en', 'ja', 'zh', 'es'}, 'response_length': {'short', 'normal', 'detailed'}}
    return {k: f.value for k, f in latest.items() if now < f.expires_at and isinstance(f.value, str) and f.value in allowed[k]}

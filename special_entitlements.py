"""Disabled SPECIAL pricing and entitlement foundation; no checkout or live grants."""
from dataclasses import dataclass
from types import MappingProxyType

PRICES = MappingProxyType({
    'special_intelligence': 39900,
    'special_learning': 39900,
    'special_automation': 49900,
    'special_all': 99000,
})
_FEATURES = MappingProxyType({
    'special_intelligence': frozenset(('advanced_retrieval', 'scoped_memory', 'knowledge_graph')),
    'special_learning': frozenset(('learning_evaluation', 'learning_simulation', 'learning_review')),
    'special_automation': frozenset(('advanced_workflow', 'role_collaboration', 'external_tools')),
})
_ALL = frozenset().union(*_FEATURES.values(), {'combined_report'})


def normalize_selection(selection):
    if not isinstance(selection, (list, tuple)) or len(selection) > 10:
        raise ValueError('invalid selection')
    if not all(isinstance(p, str) and p in PRICES for p in selection):
        raise ValueError('unknown SPECIAL package')
    chosen = set(selection)
    if 'special_all' in chosen:
        chosen = {'special_all'}
    return tuple(sorted(chosen))


def quote(selection):
    chosen = normalize_selection(selection)
    return {'items': list(chosen), 'monthly_krw': sum(PRICES[p] for p in chosen),
            'available_for_purchase': False}


@dataclass(frozen=True)
class Grant:
    workspace: str
    package: str
    starts_at: int
    ends_at: int
    status: str
    payment_ref: str


def entitled_features(grants, *, workspace, now, enabled=False):
    """Only consume server-verified grants. No client grants or checkout integration."""
    if enabled is not True or not isinstance(workspace, str) or not workspace.strip() or type(now) is not int:
        return frozenset()
    if len(grants) > 100:
        return frozenset()
    features = set()
    for grant in grants:
        if not isinstance(grant, Grant) or grant.workspace != workspace or grant.status != 'paid':
            continue
        if not isinstance(grant.payment_ref, str) or not grant.payment_ref.strip():
            continue
        if type(grant.starts_at) is not int or type(grant.ends_at) is not int or not grant.starts_at <= now < grant.ends_at:
            continue
        if grant.package == 'special_all':
            features.update(_ALL)
        elif grant.package in _FEATURES:
            features.update(_FEATURES[grant.package])
    return frozenset(features)


def remaining_cost_budget(*, net_revenue_krw, committed_cost_krw, reserved_cost_krw, margin_bps=9000):
    """Illustrative integer cost ceiling, not a guarantee or transactional ledger.

    Revenue must exclude taxes/refunds; committed costs must include payment,
    infrastructure, provider and other attributable costs. The trusted caller
    must atomically reserve spend before execution and reconcile actual costs.
    """
    amounts = (net_revenue_krw, committed_cost_krw, reserved_cost_krw)
    if any(type(v) is not int or v < 0 for v in amounts) or type(margin_bps) is not int or not 0 <= margin_bps <= 10000:
        raise ValueError('invalid cost inputs')
    limit = net_revenue_krw * (10000 - margin_bps) // 10000
    return max(0, limit - committed_cost_krw - reserved_cost_krw)

"""Disabled SPECIAL job orchestration and report projection for trusted adapters."""
from dataclasses import dataclass
from types import MappingProxyType
from special_entitlements import entitled_features

JOB_FEATURES = MappingProxyType({
    'retrieval_review': 'advanced_retrieval',
    'graph_review': 'knowledge_graph',
    'learning_evaluation': 'learning_evaluation',
    'learning_simulation': 'learning_simulation',
    'workflow_review': 'advanced_workflow',
})


@dataclass(frozen=True)
class JobResult:
    completed: bool
    charged_credits: int
    actual_cost: int


def run_job(*, ledger, grants, workspace, period, job_id, kind, now,
            credit_limit, cost_limit, adapters, enabled=False):
    """Server-only pilot. Adapters must be read-only and pre-authorized.

    A reservation is retained on uncertain execution or settlement failure.
    Reconciliation must use provider evidence, not a client-supplied result.
    """
    if enabled is not True:
        return {'status': 'disabled'}
    feature = JOB_FEATURES.get(kind)
    if feature is None or feature not in entitled_features(grants, workspace=workspace, now=now, enabled=True):
        return {'status': 'forbidden'}
    adapter = adapters.get(kind)
    if not callable(adapter):
        return {'status': 'unavailable'}
    if type(credit_limit) is not int or type(cost_limit) is not int or credit_limit <= 0 or cost_limit <= 0:
        raise ValueError('positive reservation required')
    # The stable job identifier must come from the authorized server request.
    if not ledger.reserve(workspace, period, job_id, credit_limit, cost_limit):
        return {'status': 'already_reserved'}
    try:
        result = adapter(workspace=workspace, job_id=job_id)
        if not isinstance(result, JobResult) or type(result.completed) is not bool:
            raise ValueError('invalid adapter result')
        if type(result.charged_credits) is not int or not 0 <= result.charged_credits <= credit_limit:
            raise ValueError('invalid charged credits')
        if type(result.actual_cost) is not int or not 0 <= result.actual_cost <= 10**12:
            raise ValueError('invalid actual cost')
        if not result.completed and result.charged_credits:
            raise ValueError('failed job cannot charge customer credits')
        ledger.settle(workspace, period, job_id, result.charged_credits, result.actual_cost)
    except Exception:
        return {'status': 'reconciliation_required'}
    return {'status': 'completed' if result.completed else 'failed',
            'charged_credits': result.charged_credits}


def learning_report(report, *, workspace, revision, grants, now, enabled=False):
    """Project a server-verified simulation report into customer-safe metrics."""
    if 'learning_simulation' not in entitled_features(grants, workspace=workspace, now=now, enabled=enabled):
        return None
    if not isinstance(report, dict) or (report.get('workspace'), report.get('revision')) != (workspace, revision):
        return None
    total, passed = report.get('total'), report.get('passed')
    outcomes = report.get('outcomes')
    if type(total) is not int or not 1 <= total <= 100 or type(passed) is not int or not 0 <= passed <= total:
        return None
    if report.get('complete') is not True or not isinstance(outcomes, list) or len(outcomes) != total:
        return None
    ids = set()
    count = 0
    for outcome in outcomes:
        if not isinstance(outcome, (tuple, list)) or len(outcome) != 2:
            return None
        ident, status = outcome
        if not isinstance(ident, str) or not ident or ident in ids or status not in ('passed', 'failed'):
            return None
        ids.add(ident)
        count += status == 'passed'
    if count != passed:
        return None
    return {'evaluated_cases': total, 'passed_cases': passed, 'failed_cases': total-passed,
            'check_pass_rate': passed/total, 'metric': 'curated_case_checks'}

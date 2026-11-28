"""Customer-safe dashboard projection of trusted, completed evaluation records."""
from special_entitlements import entitled_features
from special_orchestration import learning_report


def dashboard(runs, *, workspace, grants, now, enabled=False):
    """No storage, fabricated results or automatic publication.

    The caller must load authenticated server-owned records only.
    Comparisons require the same suite, evaluator and case identifiers.
    """
    features = entitled_features(grants, workspace=workspace, now=now, enabled=enabled)
    if 'learning_simulation' not in features:
        return None
    if len(runs) > 500:
        raise ValueError('too many evaluation records')
    accepted = []
    seen = set()
    for run in runs:
        if not isinstance(run, dict) or run.get('workspace') != workspace:
            continue
        ident, revision, suite, version = (run.get(k) for k in ('run_id', 'revision', 'suite', 'evaluator_version'))
        timestamp = run.get('finished_at')
        if not all(isinstance(x, str) and 0 < len(x) <= 256 for x in (ident, revision, suite, version)):
            continue
        if type(timestamp) is not int or not 0 <= timestamp <= now:
            continue
        metrics = learning_report(run, workspace=workspace, revision=revision,
                                  grants=grants, now=now, enabled=enabled)
        if metrics is None:
            continue
        if ident in seen:
            raise ValueError('duplicate evaluation run')
        seen.add(ident)
        outcomes = dict(run['outcomes'])
        accepted.append((timestamp, ident, suite, version, outcomes, metrics))
    accepted.sort(key=lambda r: (r[0], r[1]))
    if not accepted:
        return {'status': 'no_verified_results', 'latest': None, 'trend': [], 'comparison': None}
    latest = accepted[-1]
    comparable = [r for r in accepted if r[2:4] == latest[2:4] and r[4].keys() == latest[4].keys()]
    # Same-second evaluations cannot establish temporal order reliably.
    previous = next((r for r in reversed(comparable[:-1]) if r[0] < latest[0]), None)
    trend = [{'finished_at': r[0], 'passed': r[5]['passed_cases'],
              'total': r[5]['evaluated_cases']} for r in comparable[-30:]]
    comparison = None
    if previous is not None:
        old, new = previous[4], latest[4]
        comparison = {'previous_at': previous[0],
                      'pass_rate_change': latest[5]['check_pass_rate'] - previous[5]['check_pass_rate'],
                      'improved_cases': sum(old[k] == 'failed' and new[k] == 'passed' for k in new),
                      'regressed_cases': sum(old[k] == 'passed' and new[k] == 'failed' for k in new)}
    return {'status': 'verified_case_checks', 'latest': latest[5], 'trend': trend, 'comparison': comparison}

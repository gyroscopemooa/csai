"""Local-only SPECIAL synthetic evaluation using actual deterministic retrieval checks."""
from learning_simulation import Scenario, run_simulation
from knowledge_retrieval import select_faq
from special_entitlements import Grant

FIXTURE = (
    {'q': '배송 기간', 'a': '테스트 배송 기간'},
    {'q': '영업시간', 'a': '테스트 영업시간'},
    {'q': '환불 규정', 'a': '테스트 환불 규정'},
)
IDS = ('shipping', 'hours', 'refund')
SCENARIOS = (
    Scenario('shipping', 'shipping', '물건 언제 와요?', False, ('shipping',)),
    Scenario('hours', 'hours', '몇 시 열어요?', False, ('hours',)),
    Scenario('refund', 'refund', '돈 돌려받나요?', False, ('refund',)),
    Scenario('unknown', 'unknown', '외계 행성은?', True),
)
REVISION = 'synthetic-fixture-v1'
VERSION = 'lexical-retrieval-v1'


def evaluate_fixture(prompt):
    rows = select_faq(prompt, list(FIXTURE), [])
    evidence = [IDS[FIXTURE.index(row)] for row in rows]
    return {'unknown': not bool(rows), 'evidence': evidence}


def execute_fixture(workspace):
    return run_simulation(SCENARIOS, workspace=workspace, revision=REVISION,
                          evaluator_version=VERSION, evaluate=evaluate_fixture,
                          enabled=True, max_cases=4, max_bytes=1000)


def preview_dashboard(store, workspace, now):
    # Synthetic, request-local permission only. Never persists a paid grant.
    grants = [Grant(workspace, 'special_learning', 0, now + 1, 'paid', 'local-fixture-only')]
    return store.read_dashboard(workspace=workspace, grants=grants, now=now, enabled=True)


def approved_diagnostics(published):
    """Read only the published FAQ snapshot; return counts, not raw education data."""
    from contextual_knowledge import knowledge_diagnostics
    if not isinstance(published, dict):
        return {'status': 'unavailable'}
    rows = published.get('faq', [])
    if not isinstance(rows, list) or len(rows) > 500:
        return {'status': 'unavailable'}
    result = knowledge_diagnostics(rows)
    return {'status': 'measured', 'total': result['total'],
            'distinct_questions': result['distinct_questions'],
            'duplicate_count': result['duplicate_count'],
            'invalid_count': len(result['invalid_indices']),
            'review_group_count': len(result['review_groups'])}

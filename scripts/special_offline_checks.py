"""Run isolated SPECIAL tests; fail if any expected suite is missing or empty."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
NAMES = ('knowledge_retrieval', 'hybrid_retrieval', 'knowledge_indexing', 'retrieval_cache',
         'contextual_knowledge', 'graph_memory', 'learning_evaluation', 'learning_simulation',
         'workflow_pilot', 'special_entitlements', 'special_usage', 'special_orchestration',
         'special_dashboard', 'special_evaluation_store', 'special_local_fixture', 'retrieval_pipeline',
         'special_lookup_preview', 'special_fixture_identity', 'special_job_integration')


def collect_tests(root, names):
    suite = unittest.TestSuite()
    for name in names:
        filename = 'test_' + name + '.py'
        if not (root / 'tests' / filename).is_file():
            raise RuntimeError('Missing expected test file: ' + filename)
        group = unittest.TestLoader().discover(str(root / 'tests'), pattern=filename)
        if not group.countTestCases():
            raise RuntimeError('Empty expected test suite: ' + filename)
        print(filename + ': ' + str(group.countTestCases()), flush=True)
        suite.addTests(group)
    return suite


if __name__ == '__main__':
    suite = collect_tests(ROOT, NAMES)
    print('Total collected: ' + str(suite.countTestCases()), flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)

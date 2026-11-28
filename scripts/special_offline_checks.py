"""Run the isolated SPECIAL unit test files without loading the live app."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
NAMES = ('knowledge_retrieval', 'hybrid_retrieval', 'knowledge_indexing', 'retrieval_cache',
         'contextual_knowledge', 'graph_memory', 'learning_evaluation', 'learning_simulation',
         'workflow_pilot', 'special_entitlements', 'special_usage', 'special_orchestration',
         'special_dashboard', 'special_evaluation_store', 'special_local_fixture', 'retrieval_pipeline')

if __name__ == '__main__':
    suite = unittest.TestSuite()
    for name in NAMES:
        suite.addTests(unittest.TestLoader().discover(str(ROOT / 'tests'), pattern='test_' + name + '.py'))
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)

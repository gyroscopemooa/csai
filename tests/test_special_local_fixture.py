import unittest
import tempfile
from pathlib import Path
from special_local_fixture import execute_fixture, preview_dashboard
from special_evaluation_store import EvaluationStore


class FixtureTests(unittest.TestCase):
    def test_fixture_complete(self):
        result = execute_fixture('demo')
        self.assertTrue(result['complete'])
        self.assertEqual(result['total'], 4)
        self.assertEqual(result['passed'], 4)

    def test_store_and_scoped_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EvaluationStore(str(Path(directory) / 'fixture.db'))
            self.assertEqual(preview_dashboard(store, 'a', 100)['status'], 'no_verified_results')
            store.save('a', 'fixture', execute_fixture('a'), 10)
            self.assertEqual(preview_dashboard(store, 'a', 100)['latest']['passed_cases'], 4)
            self.assertEqual(preview_dashboard(store, 'b', 100)['status'], 'no_verified_results')

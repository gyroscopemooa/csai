import tempfile
import unittest
from pathlib import Path
from special_evaluation_store import EvaluationStore
from special_entitlements import Grant


class StoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / 'eval.db')
        self.store = EvaluationStore(self.path)
        self.report = dict(workspace='w', revision='r', suite='s', evaluator_version='v',
                           complete=True, total=1, passed=1, outcomes=[('a', 'passed')],
                           prompt='not stored', actual_cost=123)
        self.grants = [Grant('w', 'special_learning', 0, 100, 'paid', 'ref')]
        self.args = dict(workspace='w', grants=self.grants, now=90, enabled=True)

    def test_persistence(self):
        self.assertTrue(self.store.save('w', '1', self.report, 20))
        result = EvaluationStore(self.path).read_dashboard(**self.args)
        self.assertEqual(result['latest']['passed_cases'], 1)
        self.assertNotIn('actual_cost', str(result))

    def test_replay(self):
        self.store.save('w', '1', self.report, 20)
        self.assertFalse(self.store.save('w', '1', self.report, 20))
        with self.assertRaises(ValueError):
            self.store.save('w', '1', self.report, 21)

    def test_scope(self):
        with self.assertRaises(ValueError):
            self.store.save('other', '1', self.report, 20)
        self.store.save('w', '1', self.report, 20)
        self.assertIsNone(self.store.read_dashboard(**(self.args | {'workspace': 'other'})))

    def test_default_off(self):
        self.assertIsNone(self.store.read_dashboard(**(self.args | {'enabled': False})))

    def test_reject_incomplete_or_invalid(self):
        for change in [{'complete': False}, {'passed': 0}, {'total': 2}, {'outcomes': [('a', 'error')]}]:
            with self.assertRaises(ValueError):
                self.store.save('w', '1', self.report | change, 20)

    def test_future_excluded(self):
        self.store.save('w', '1', self.report, 91)
        self.assertEqual(self.store.read_dashboard(**self.args)['status'], 'no_verified_results')

    def test_purge_scope(self):
        self.store.save('w', '1', self.report, 20)
        self.store.save('other', '1', self.report | {'workspace': 'other'}, 20)
        self.assertEqual(self.store.purge_workspace('other'), 1)
        self.assertEqual(self.store.read_dashboard(**self.args)['latest']['passed_cases'], 1)
        self.assertEqual(self.store.purge_workspace('w'), 1)
        self.assertEqual(self.store.read_dashboard(**self.args)['status'], 'no_verified_results')

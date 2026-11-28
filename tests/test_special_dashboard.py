import unittest
from special_entitlements import Grant
from special_dashboard import dashboard


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.grants = [Grant('w', 'special_learning', 0, 100, 'paid', 'ref')]
        self.args = dict(workspace='w', grants=self.grants, now=90, enabled=True)
        self.old = dict(workspace='w', run_id='a', revision='r1', suite='s', evaluator_version='v',
                        finished_at=10, complete=True, total=2, passed=1,
                        outcomes=[('1', 'passed'), ('2', 'failed')])
        self.new = dict(self.old, run_id='b', revision='r2', finished_at=20, passed=2,
                        outcomes=[('1', 'passed'), ('2', 'passed')])

    def test_disabled(self):
        self.assertIsNone(dashboard([self.old], **(self.args | {'enabled': False})))

    def test_empty_no_fake_data(self):
        self.assertEqual(dashboard([], **self.args)['status'], 'no_verified_results')

    def test_comparison(self):
        result = dashboard([self.new, self.old], **self.args)
        self.assertEqual(result['comparison']['improved_cases'], 1)
        self.assertEqual(result['comparison']['pass_rate_change'], .5)
        self.assertEqual(len(result['trend']), 2)

    def test_incomparable(self):
        for change in [{'suite': 'new'}, {'evaluator_version': 'new'}, {'outcomes': [('x', 'passed'), ('y', 'passed')]}]:
            self.assertIsNone(dashboard([self.old, self.new | change], **self.args)['comparison'])

    def test_cross_scope_and_invalid_metrics(self):
        result = dashboard([self.old | {'workspace': 'other'}, self.new | {'passed': 1}], **self.args)
        self.assertEqual(result['status'], 'no_verified_results')

    def test_duplicate(self):
        with self.assertRaises(ValueError):
            dashboard([self.old, self.old], **self.args)

    def test_no_internal_cost(self):
        result = dashboard([self.old | {'actual_cost': 999}], **self.args)
        self.assertNotIn('actual_cost', str(result))

    def test_equal_time_not_compared(self):
        self.assertIsNone(dashboard([self.old, self.new | {'finished_at': 10}], **self.args)['comparison'])

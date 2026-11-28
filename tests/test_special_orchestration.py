import unittest
from unittest.mock import Mock
from special_entitlements import Grant
from special_orchestration import JobResult, run_job, learning_report


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.grants = [Grant('w', 'special_learning', 10, 30, 'paid', 'payment')]
        self.ledger = Mock()
        self.ledger.reserve.return_value = True
        self.adapter = Mock(return_value=JobResult(True, 2, 30))
        self.args = dict(ledger=self.ledger, grants=self.grants, workspace='w', period='p',
                         job_id='j', kind='learning_simulation', now=20, credit_limit=3,
                         cost_limit=50, adapters={'learning_simulation': self.adapter}, enabled=True)

    def test_default_off(self):
        args = dict(self.args)
        args.pop('enabled')
        self.assertEqual(run_job(**args)['status'], 'disabled')
        self.ledger.reserve.assert_not_called()

    def test_forbidden(self):
        self.assertEqual(run_job(**(self.args | {'workspace': 'other'}))['status'], 'forbidden')
        self.ledger.reserve.assert_not_called()

    def test_success(self):
        self.assertEqual(run_job(**self.args), {'status': 'completed', 'charged_credits': 2})
        self.ledger.reserve.assert_called_once_with('w', 'p', 'j', 3, 50)
        self.ledger.settle.assert_called_once_with('w', 'p', 'j', 2, 30)

    def test_duplicate(self):
        self.ledger.reserve.return_value = False
        self.assertEqual(run_job(**self.args)['status'], 'already_reserved')
        self.adapter.assert_not_called()

    def test_error_retains_reservation(self):
        self.adapter.side_effect = RuntimeError('private')
        self.assertEqual(run_job(**self.args)['status'], 'reconciliation_required')
        self.ledger.settle.assert_not_called()

    def test_failed_job_zero_charge(self):
        self.adapter.return_value = JobResult(False, 0, 20)
        self.assertEqual(run_job(**self.args)['status'], 'failed')
        self.ledger.settle.assert_called_once_with('w', 'p', 'j', 0, 20)

    def test_invalid_result(self):
        self.adapter.return_value = JobResult(True, 4, 30)
        self.assertEqual(run_job(**self.args)['status'], 'reconciliation_required')
        self.ledger.settle.assert_not_called()

    def test_report(self):
        report = dict(workspace='w', revision='r', total=2, passed=1, complete=True,
                      outcomes=[('1', 'passed'), ('2', 'failed')], actual_cost=20)
        args = dict(workspace='w', revision='r', grants=self.grants, now=20, enabled=True)
        self.assertEqual(learning_report(report, **args), dict(evaluated_cases=2, passed_cases=1,
            failed_cases=1, check_pass_rate=.5, metric='curated_case_checks'))
        self.assertIsNone(learning_report(report, **(args | {'revision': 'new'})))
        self.assertIsNone(learning_report(report | {'passed': 2}, **args))
        self.assertIsNone(learning_report(report | {'complete': False}, **args))

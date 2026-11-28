"""Offline integration of entitlement checks, execution and real SQLite accounting."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

from special_entitlements import Grant
from special_orchestration import JobResult, run_job
from special_usage import UsageLedger


class JobIntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger = UsageLedger(str(Path(tmp.name) / 'ledger.db'))
        self.ledger.provision('w', 'p', 10, 100)
        self.grant = Grant('w', 'special_learning', 10, 30, 'paid', 'order')
        self.adapter = Mock(return_value=JobResult(True, 2, 30))
        self.args = dict(ledger=self.ledger, grants=[self.grant], workspace='w',
                         period='p', job_id='j', kind='learning_simulation',
                         now=20, credit_limit=3, cost_limit=50,
                         adapters={'learning_simulation': self.adapter}, enabled=True)

    def test_completed_and_replay(self):
        self.assertEqual(run_job(**self.args)['status'], 'completed')
        self.assertEqual(run_job(**self.args)['status'], 'already_reserved')
        self.adapter.assert_called_once()
        state = self.ledger.snapshot('w', 'p')
        self.assertEqual((state['charged_credits'], state['actual_cost'], state['pending_jobs']), (2, 30, 0))

    def test_refunded_grant_prevents_reservation(self):
        args = self.args | {'grants': [self.grant, replace(self.grant, status='refunded')]}
        self.assertEqual(run_job(**args)['status'], 'forbidden')
        self.adapter.assert_not_called()
        self.assertEqual(self.ledger.snapshot('w', 'p')['remaining_credits'], 10)

    def test_concurrent_duplicate(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: run_job(**self.args)['status'], range(2)))
        self.assertCountEqual(statuses, ['completed', 'already_reserved'])
        self.adapter.assert_called_once()
        self.assertEqual(self.ledger.snapshot('w', 'p')['charged_credits'], 2)

    def test_unknown_execution_keeps_reservation(self):
        self.adapter.side_effect = RuntimeError('unknown provider outcome')
        self.assertEqual(run_job(**self.args)['status'], 'reconciliation_required')
        state = self.ledger.snapshot('w', 'p')
        self.assertEqual((state['pending_jobs'], state['reserved_credits'], state['reserved_cost']), (1, 3, 50))
        self.assertEqual(run_job(**self.args)['status'], 'already_reserved')
        self.adapter.assert_called_once()

    def test_failed_job_zero_customer_charge(self):
        self.adapter.return_value = JobResult(False, 0, 20)
        self.assertEqual(run_job(**self.args)['status'], 'failed')
        state = self.ledger.snapshot('w', 'p')
        self.assertEqual((state['charged_credits'], state['actual_cost'], state['pending_jobs']), (0, 20, 0))

    def test_overrun_blocks_next_job(self):
        self.adapter.return_value = JobResult(True, 2, 101)
        self.assertEqual(run_job(**self.args)['status'], 'completed')
        self.assertEqual(self.ledger.snapshot('w', 'p')['cost_overrun'], 1)
        with self.assertRaises(ValueError):
            run_job(**(self.args | {'job_id': 'next'}))
        self.adapter.assert_called_once()

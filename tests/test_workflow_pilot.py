import unittest
from unittest.mock import Mock
from workflow_pilot import Step, ToolSpec, validate_plan, run_read_only, approval_preview


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'lookup': ToolSpec('support', True), 'check': ToolSpec('review', True), 'send': ToolSpec('support', False)}
        self.steps = [Step('a', 'lookup', 'support'), Step('b', 'check', 'review', ('a',))]
        self.execute = Mock(return_value={'ok': True})
        self.verify = Mock(return_value=True)
        self.args = dict(workspace='w', enabled=True, max_steps=2, execute=self.execute, verify=self.verify)

    def test_default_off(self):
        self.assertIsNone(run_read_only(self.steps, self.registry, **(self.args | {'enabled': False})))
        self.execute.assert_not_called()

    def test_verified(self):
        result = run_read_only(self.steps, self.registry, **self.args)
        self.assertTrue(result['complete'])
        self.assertEqual(self.execute.call_count, 2)

    def test_write_blocked_before_execution(self):
        with self.assertRaises(ValueError):
            run_read_only([self.steps[0], Step('b', 'send', 'support')], self.registry, **self.args)
        self.execute.assert_not_called()

    def test_role_mismatch(self):
        with self.assertRaises(ValueError):
            validate_plan([Step('a', 'lookup', 'review')], self.registry)

    def test_dependency_order(self):
        with self.assertRaises(ValueError):
            validate_plan(self.steps[::-1], self.registry)

    def test_budget(self):
        with self.assertRaises(ValueError):
            run_read_only(self.steps, self.registry, **(self.args | {'max_steps': 1}))
        self.execute.assert_not_called()

    def test_stop_on_failed_verification(self):
        self.verify.return_value = False
        self.assertFalse(run_read_only(self.steps, self.registry, **self.args)['complete'])
        self.execute.assert_called_once()

    def test_stop_on_error(self):
        self.execute.side_effect = RuntimeError('private')
        result = run_read_only(self.steps, self.registry, **self.args)
        self.assertEqual(result['outcomes'], [('a', 'error')])

    def test_approval_preview_not_execution(self):
        result = approval_preview([Step('a', 'send', 'support')], self.registry, workspace='w')
        self.assertEqual(result['review_required'], ['a'])
        self.execute.assert_not_called()

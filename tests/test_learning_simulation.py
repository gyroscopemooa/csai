import unittest
from unittest.mock import Mock
from dataclasses import replace
from learning_simulation import Scenario, run_simulation, review_suggestions


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.s = Scenario('1', 'delivery', '배송 기간?', False, ('faq1',))
        self.mock = Mock(return_value={'unknown': False, 'evidence': ['faq1']})
        self.args = dict(workspace='w', revision='r', evaluator_version='fixture', evaluate=self.mock,
                         enabled=True, max_cases=2, max_bytes=100)

    def test_off(self):
        self.assertIsNone(run_simulation([self.s], **(self.args | {'enabled': False})))
        self.mock.assert_not_called()

    def test_pass(self):
        r = run_simulation([self.s], **self.args)
        self.assertTrue(r['complete'])
        self.assertEqual(r['passed'], 1)

    def test_budget(self):
        with self.assertRaises(ValueError):
            run_simulation([self.s], **(self.args | {'max_bytes': 1}))
        self.mock.assert_not_called()

    def test_duplicate(self):
        with self.assertRaises(ValueError):
            run_simulation([self.s, self.s], **self.args)
        self.mock.assert_not_called()

    def test_gap(self):
        self.mock.return_value = {'unknown': True}
        r = run_simulation([self.s], **self.args)
        self.assertEqual(review_suggestions(r, workspace='w', revision='r'), [{'topic': 'delivery', 'failed_cases': 1, 'status': 'owner_review_required'}])
        self.assertEqual(review_suggestions(r, workspace='other', revision='r'), [])
        self.assertEqual(review_suggestions(r, workspace='w', revision='new'), [])

    def test_stop_on_error(self):
        self.mock.side_effect = RuntimeError('private details')
        r = run_simulation([self.s, replace(self.s, id='2')], **self.args)
        self.assertFalse(r['complete'])
        self.assertEqual(r['outcomes'], [('1', 'error')])
        self.mock.assert_called_once()
        self.assertEqual(review_suggestions(r, workspace='w', revision='r'), [])

    def test_missing_evidence(self):
        self.mock.return_value = {'unknown': False}
        self.assertEqual(run_simulation([self.s], **self.args)['passed'], 0)

    def test_prompt_change_versions_suite(self):
        a = run_simulation([self.s], **self.args)
        b = run_simulation([replace(self.s, prompt='다른 질문')], **self.args)
        self.assertNotEqual(a['suite'], b['suite'])

    def test_invalid_result(self):
        self.mock.return_value = {'unknown': 'false'}
        self.assertFalse(run_simulation([self.s], **self.args)['complete'])

    def test_forbidden_evidence_fails_even_with_required_evidence(self):
        scenario = replace(self.s, forbidden_evidence=('unrelated',))
        self.mock.return_value = {'unknown': False, 'evidence': ['faq1', 'unrelated']}
        report = run_simulation([scenario], **self.args)
        self.assertTrue(report['complete'])
        self.assertEqual(report['passed'], 0)

    def test_conflicting_expectations_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            run_simulation([replace(self.s, forbidden_evidence=('faq1',))], **self.args)
        self.mock.assert_not_called()

    def test_forbidden_evidence_versions_suite(self):
        a = run_simulation([self.s], **self.args)
        b = run_simulation([replace(self.s, forbidden_evidence=('other',))], **self.args)
        self.assertEqual(b['passed'], 1)
        self.assertNotEqual(a['suite'], b['suite'])

import unittest
from learning_evaluation import Case, Observation, evaluate, compare


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = [Case('a', '배송', False, ('faq1',)), Case('b', '미등록', True)]
        self.good = [Observation('a', False, ('faq1',)), Observation('b', True)]

    def test_success(self):
        self.assertEqual(evaluate(self.cases, self.good)['check_pass_rate'], 1)

    def test_missing_counts_as_failure(self):
        result = evaluate(self.cases, self.good[:1])
        self.assertEqual(result['missing'], ['b'])
        self.assertEqual(result['check_pass_rate'], .5)

    def test_gap_candidate(self):
        result = evaluate(self.cases, [Observation('a', True), self.good[1]])
        self.assertEqual(result['gap_candidates'], {'배송': 1})

    def test_missing_evidence(self):
        self.assertEqual(evaluate(self.cases, [Observation('a', False), self.good[1]])['failed'], ['a'])

    def test_duplicate_and_unknown_observation(self):
        for obs in [self.good + self.good, [Observation('x', True)]]:
            with self.assertRaises(ValueError):
                evaluate(self.cases, obs)

    def test_regression(self):
        before = evaluate(self.cases, self.good)
        after = evaluate(self.cases, [Observation('a', True), self.good[1]])
        self.assertEqual(compare(before, after), {'delta': -.5, 'regressions': ['a'], 'improved': []})

    def test_incomplete_comparison(self):
        with self.assertRaises(ValueError):
            compare(evaluate(self.cases, []), evaluate(self.cases, self.good))

    def test_changed_suite(self):
        with self.assertRaises(ValueError):
            compare(evaluate(self.cases, self.good), evaluate([Case('a', '배송', True)], [Observation('a', True)]))

    def test_order_independence(self):
        self.assertEqual(evaluate(self.cases, self.good), evaluate(self.cases[::-1], self.good[::-1]))

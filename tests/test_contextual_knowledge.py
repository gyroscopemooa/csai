import unittest
from unittest.mock import patch
from contextual_knowledge import contextual_candidates, maybe_contextual_candidates, knowledge_diagnostics


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.faq = {'q': '배송 기간', 'a': '2일'}
        self.history = [{'role': 'user', 'body': '물건 언제 와요?'}, {'role': 'assistant', 'body': '안녕하세요'}]
        self.args = ('그럼 어떻게 되나요?', self.history, [self.faq], [])

    def test_followup(self):
        self.assertEqual(contextual_candidates(*self.args, enabled=True), [self.faq])

    def test_default_off(self):
        self.assertEqual(contextual_candidates(*self.args), [])
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(maybe_contextual_candidates(*self.args, live_model=True), [])

    def test_explicit_topic_or_sensitive_request(self):
        for q in ['그럼 환불은?', '그럼 상품 123은?', '그럼 배송비는?', '안녕하세요', '그럼 아니 그거 말고']:
            self.assertEqual(contextual_candidates(q, *self.args[1:], enabled=True), [])

    def test_assistant_only(self):
        self.assertEqual(contextual_candidates(self.args[0], self.history[1:], [self.faq], [], enabled=True), [])

    def test_latest_customer_only(self):
        history = self.history + [{'role': 'user', 'body': '다른 문의'}]
        self.assertEqual(contextual_candidates(self.args[0], history, [self.faq], [], enabled=True), [])

    def test_demo_disabled(self):
        with patch.dict('os.environ', {'CSAI_CONTEXT_RETRIEVAL': 'pilot'}):
            self.assertEqual(maybe_contextual_candidates(*self.args, live_model=False), [])
            self.assertEqual(maybe_contextual_candidates(*self.args, live_model=True), [self.faq])

    def test_diagnostics(self):
        rows = [self.faq, dict(self.faq), {'q': '배송기간?', 'a': '3일'}, {}, {'q': '!!', 'a': 'a'}]
        self.assertEqual(knowledge_diagnostics(rows), {'total': 5, 'distinct_questions': 1, 'duplicate_count': 1, 'invalid_indices': [3, 4], 'review_groups': [(0, 1, 2)]})

    def test_answer_punctuation_preserved(self):
        self.assertEqual(knowledge_diagnostics([{'q': '링크', 'a': '/a'}, {'q': '링크', 'a': '/A'}])['review_groups'], [(0, 1)])

    def test_limit(self):
        with self.assertRaises(ValueError):
            knowledge_diagnostics([self.faq] * 501)

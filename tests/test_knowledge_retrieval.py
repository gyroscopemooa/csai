import unittest
from unittest.mock import patch
from knowledge_retrieval import maybe_select_faq, select_faq


def faq(q, a='승인된 답변'):
    return {'q': q, 'a': a}


class RetrievalTests(unittest.TestCase):
    def test_korean_paraphrase(self):
        delivery = faq('배송 소요 기간은?', '2~3일')
        fee = faq('배송비는 얼마인가요?', '3000원')
        self.assertEqual(select_faq('물건 언제 와요?', [fee, delivery], []), [delivery])

    def test_refund_and_exchange_are_not_equivalent(self):
        refund, exchange = faq('환불 규정'), faq('교환 규정')
        self.assertEqual(select_faq('돈 돌려받을 수 있나요?', [exchange, refund], []), [refund])

    def test_preserves_legacy_and_deduplicates(self):
        old = [faq('일반 배송 안내'), faq('상품 안내')]
        extra = faq('배송 기간')
        self.assertEqual(select_faq('언제 도착하나요?', [extra, extra], old), old + [extra])

    def test_specific_numeric_query_keeps_legacy(self):
        old = [faq('123 상품 배송')]
        self.assertEqual(select_faq('123 상품 언제 와요?', [faq('456 상품 배송 기간')], old), old)

    def test_unknown_question_keeps_legacy(self):
        old = [faq('이용 안내')]
        self.assertEqual(select_faq('외계 행성은?', [faq('배송 기간')], old), old)

    def test_exact_match_not_replaced(self):
        exact = faq('배송 기간')
        self.assertEqual(select_faq('배송 기간', [faq('배송 소요 시간')], [exact]), [exact])

    def test_limit_and_bad_records(self):
        entries = [faq('배송 기간 '+str(i)) for i in range(8)]
        self.assertLessEqual(len(select_faq('언제 도착?', [None, {}, *entries], entries, 99)), 5)

    def test_flag_default_and_demo_off(self):
        old = [faq('기존 답변')]
        with patch.dict('os.environ', {}, clear=True):
            self.assertIs(maybe_select_faq('언제 와요', [faq('배송 기간')], old, live_model=True), old)
        with patch.dict('os.environ', {'CSAI_KNOWLEDGE_RETRIEVAL': 'pilot'}):
            self.assertIs(maybe_select_faq('언제 와요', [faq('배송 기간')], old, live_model=False), old)
            self.assertEqual(len(maybe_select_faq('언제 와요', [faq('배송 기간')], old, live_model=True)), 2)

    def test_failure_falls_back(self):
        old = [faq('기존 답변')]
        with patch.dict('os.environ', {'CSAI_KNOWLEDGE_RETRIEVAL': 'pilot'}), patch('knowledge_retrieval.select_faq', side_effect=RuntimeError):
            self.assertIs(maybe_select_faq('배송', [], old, live_model=True), old)


if __name__ == '__main__':
    unittest.main()

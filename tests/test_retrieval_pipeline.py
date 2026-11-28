import unittest
from unittest.mock import Mock
from retrieval_pipeline import RetrievalPipeline
from retrieval_cache import QueryVectorCache


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{'q': '배송 기간', 'a': '2일'}, {'q': '영업시간', 'a': '9시'}]
        self.embed = Mock(return_value=[[1, 0], [0, 1]])
        self.cache = QueryVectorCache(enabled=True)
        self.p = RetrievalPipeline(workspace='w', encoder_version='fixture', embed=self.embed,
                                   enabled=True, cache=self.cache)
        self.p.refresh(self.rows, 'r1', max_new=2, max_bytes=100)
        self.embed.reset_mock()
        self.embed.return_value = [[1, 0]]
        self.auth = Mock(return_value=True)
        self.args = dict(revision='r1', authorize_query=self.auth, cacheable=True)

    def test_selection_and_cache(self):
        for _ in range(2):
            self.assertEqual(self.p.select('언제 와요?', self.rows, [], **self.args), self.rows[:1])
        self.embed.assert_called_once()
        self.auth.assert_called_once()

    def test_no_authorization_no_call(self):
        self.assertEqual(self.p.select('언제 와요?', self.rows, [], revision='r1'), [])
        self.embed.assert_not_called()

    def test_stale_revision_and_content(self):
        self.assertEqual(self.p.select('언제 와요?', self.rows, [], **(self.args | {'revision': 'r2'})), [])
        self.assertEqual(self.p.select('언제 와요?', self.rows[:1], [], **self.args), [])
        self.embed.assert_not_called()

    def test_sensitive_queries(self):
        for q in ['123 배송', '환불 문의', '예약 변경']:
            self.assertEqual(self.p.select(q, self.rows, [], **self.args), [])
        self.embed.assert_not_called()

    def test_failed_refresh_clears_index(self):
        with self.assertRaises(ValueError):
            self.p.refresh(self.rows + [{'q': '새 질문', 'a': '답변'}], 'r2', max_new=0, max_bytes=0)
        self.assertIsNone(self.p.index)

    def test_default_off(self):
        p = RetrievalPipeline(workspace='w', encoder_version='fixture', embed=self.embed)
        self.assertFalse(p.refresh(self.rows, 'r1'))
        self.embed.assert_not_called()

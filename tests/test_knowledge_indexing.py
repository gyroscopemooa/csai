import unittest
from unittest.mock import Mock
from knowledge_indexing import plan_index, refresh_index


class IndexingTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{'q': '배송 기간', 'a': '2일'}, {'q': '환불 규정', 'a': '7일'}]
        self.args = dict(workspace='a', revision='r1', encoder='fixture', approved=self.rows,
                         enabled=True, max_new=2, max_bytes=1000)
        self.embed = Mock(return_value=[[1, 0], [0, 1]])
        self.previous = refresh_index(**self.args, embed=self.embed)
        self.embed.reset_mock()

    def test_default_off(self):
        self.assertIsNone(refresh_index(**(self.args | {'enabled': False}), embed=self.embed))
        self.embed.assert_not_called()

    def test_new_revision_reuses_unchanged_vectors(self):
        result = refresh_index(**(self.args | {'revision': 'r2', 'max_new': 0}), previous=self.previous, embed=self.embed)
        self.assertEqual(result.records, self.previous.records)
        self.assertEqual(result.revision, 'r2')
        self.embed.assert_not_called()

    def test_changed_approved_answer_reindexes_only_changed(self):
        rows = [dict(self.rows[0], a='3일'), self.rows[1]]
        self.embed.return_value = [[1, 1]]
        result = refresh_index(**(self.args | {'approved': rows, 'revision': 'r2'}), previous=self.previous, embed=self.embed)
        self.embed.assert_called_once_with(['배송 기간'])
        self.assertEqual(result.rank(workspace='a', revision='r2', encoder='fixture', query_vector=[1, 1], approved=rows)[0], rows[0])

    def test_cross_workspace_and_encoder_reuse_denied(self):
        for update in [{'workspace': 'b'}, {'encoder': 'new'}]:
            plan = plan_index(**({'workspace': 'a', 'revision': 'r2', 'encoder': 'fixture', 'approved': self.rows, 'previous': self.previous} | update))
            self.assertEqual(len(plan.missing), 2)
            self.assertFalse(plan.reused)

    def test_budget_denied_before_call(self):
        for update in [{'max_new': 1}, {'max_bytes': 1}]:
            with self.assertRaises(ValueError):
                refresh_index(**(self.args | update), embed=self.embed)
        self.embed.assert_not_called()

    def test_deleted_records_not_reused(self):
        result = refresh_index(**(self.args | {'approved': self.rows[:1], 'revision': 'r2', 'max_new': 0}), previous=self.previous, embed=self.embed)
        self.assertEqual(len(result.records), 1)
        self.embed.assert_not_called()

    def test_bad_encoder_response_fails_without_partial_result(self):
        self.embed.return_value = [[1, 0]]
        with self.assertRaises(ValueError):
            refresh_index(**self.args, embed=self.embed)
        self.embed.assert_called_once()

    def test_duplicate_approved_rows_encoded_once(self):
        self.embed.return_value = [[1, 0]]
        result = refresh_index(**(self.args | {'approved': [self.rows[0], self.rows[0]]}), embed=self.embed)
        self.embed.assert_called_once_with(['배송 기간'])
        self.assertEqual(len(result.records), 1)

    def test_empty_approval_returns_no_index(self):
        self.assertIsNone(refresh_index(**(self.args | {'approved': []}), previous=self.previous, embed=self.embed))
        self.embed.assert_not_called()


if __name__ == '__main__':
    unittest.main()

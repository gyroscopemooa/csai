import unittest
from hybrid_retrieval import FAQVectorIndex, hybrid_candidates


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.delivery = {'q': '배송 소요 기간', 'a': '2일'}
        self.exchange = {'q': '교환 규정', 'a': '7일'}
        self.rows = [self.delivery, self.exchange]
        self.index = FAQVectorIndex.build('a', 'r1', 'fixture', self.rows, [[1, 0], [0, 1]])
        self.args = dict(query='물건 언제 와요?', legacy=[self.exchange], approved=self.rows,
                         index=self.index, workspace='a', revision='r1', encoder='fixture',
                         query_vector=[1, 0], enabled=True)

    def test_semantic_candidate_preserves_legacy(self):
        self.assertEqual(hybrid_candidates(**self.args), [self.exchange, self.delivery])

    def test_off_by_default(self):
        args = dict(self.args)
        del args['enabled']
        self.assertIs(hybrid_candidates(**args), self.args['legacy'])

    def test_wrong_scope(self):
        for field, value in [('workspace', 'b'), ('revision', 'r2'), ('encoder', 'other')]:
            with self.subTest(field=field):
                self.assertIs(hybrid_candidates(**(self.args | {field: value})), self.args['legacy'])

    def test_changed_answer_invalidates_index(self):
        self.assertIs(hybrid_candidates(**(self.args | {'approved': [dict(self.delivery, a='3일'), self.exchange]})), self.args['legacy'])

    def test_removed_or_added_approval_invalidates_index(self):
        for rows in [[self.delivery], self.rows + [{'q': '주소', 'a': '울산'}]]:
            self.assertIs(hybrid_candidates(**(self.args | {'approved': rows})), self.args['legacy'])

    def test_numeric_identifier_preserves_legacy(self):
        self.assertIs(hybrid_candidates(**(self.args | {'query': '상품 123 배송'})), self.args['legacy'])

    def test_invalid_or_weak_vectors(self):
        for vector in [[0, 0], [1], [float('nan'), 0], [-1, -1], ['1', '0']]:
            self.assertIs(hybrid_candidates(**(self.args | {'query_vector': vector})), self.args['legacy'])

    def test_invalid_index_build(self):
        for vectors in [[[1, 0]], [[1, 0], [0, 1, 0]], [[0, 0], [0, 1]]]:
            with self.assertRaises(ValueError):
                FAQVectorIndex.build('a', 'r1', 'fixture', self.rows, vectors)

    def test_duplicate_semantic_candidate(self):
        self.assertEqual(hybrid_candidates(**(self.args | {'legacy': [self.delivery]})), [self.delivery])


if __name__ == '__main__':
    unittest.main()

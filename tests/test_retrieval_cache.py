import unittest
from retrieval_cache import QueryVectorCache


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.now = 100
        self.cache = QueryVectorCache(capacity=2, ttl=5, enabled=True, clock=lambda: self.now)
        self.args = dict(workspace='a', revision='r1', encoder='fixture', query='배송 기간', cacheable=True)

    def test_off_by_default(self):
        cache = QueryVectorCache()
        self.assertFalse(cache.put(**self.args, vector=[1, 0]))
        self.assertIsNone(cache.get(**self.args))

    def test_explicit_cacheability_required(self):
        args = self.args | {'cacheable': False}
        self.assertFalse(self.cache.put(**args, vector=[1, 0]))
        self.assertIsNone(self.cache.get(**args))

    def test_valid_hit(self):
        self.assertTrue(self.cache.put(**self.args, vector=[2, 0]))
        self.assertEqual(self.cache.get(**self.args), (1.0, 0.0))

    def test_isolation(self):
        self.cache.put(**self.args, vector=[1, 0])
        for field, value in [('workspace', 'b'), ('revision', 'r2'), ('encoder', 'other'), ('query', '배송기간')]:
            self.assertIsNone(self.cache.get(**(self.args | {field: value})))

    def test_expiry(self):
        self.cache.put(**self.args, vector=[1, 0])
        self.now = 105
        self.assertIsNone(self.cache.get(**self.args))

    def test_capacity(self):
        self.cache.put(**self.args, vector=[1, 0])
        for query in ['주소', '예약']:
            self.cache.put(**(self.args | {'query': query}), vector=[0, 1])
        self.assertIsNone(self.cache.get(**self.args))

    def test_invalid_vector(self):
        with self.assertRaises(ValueError):
            self.cache.put(**self.args, vector=[float('nan'), 0])
        self.assertIsNone(self.cache.get(**self.args))

    def test_clear(self):
        self.cache.put(**self.args, vector=[1, 0])
        self.cache.clear()
        self.assertIsNone(self.cache.get(**self.args))

    def test_raw_query_not_retained_as_key(self):
        self.cache.put(**self.args, vector=[1, 0])
        key = next(iter(self.cache._entries))
        self.assertIsInstance(key, bytes)
        self.assertNotIn(self.args['query'].encode(), key)


if __name__ == '__main__':
    unittest.main()

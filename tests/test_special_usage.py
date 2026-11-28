import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from special_usage import UsageLedger


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.l = UsageLedger(str(Path(self.tmp.name) / 'usage.db'))
        self.l.provision('w', 'p', 10, 100)

    def test_replay(self):
        self.assertTrue(self.l.reserve('w', 'p', 'a', 5, 50))
        self.assertFalse(self.l.reserve('w', 'p', 'a', 5, 50))
        with self.assertRaises(ValueError):
            self.l.reserve('w', 'p', 'a', 4, 50)

    def test_limits(self):
        self.l.reserve('w', 'p', 'a', 9, 90)
        for credits, cost in [(2, 0), (0, 11)]:
            with self.assertRaises(ValueError):
                self.l.reserve('w', 'p', 'b', credits, cost)

    def test_release_unused(self):
        self.l.reserve('w', 'p', 'a', 10, 100)
        self.l.settle('w', 'p', 'a', 0, 0)
        self.assertTrue(self.l.reserve('w', 'p', 'b', 10, 100))

    def test_overrun_recorded(self):
        self.l.reserve('w', 'p', 'a', 1, 10)
        self.l.settle('w', 'p', 'a', 1, 101)
        with self.assertRaises(ValueError):
            self.l.reserve('w', 'p', 'b', 0, 0)

    def test_settlement_replay(self):
        self.l.reserve('w', 'p', 'a', 5, 50)
        self.assertTrue(self.l.settle('w', 'p', 'a', 4, 30))
        self.assertFalse(self.l.settle('w', 'p', 'a', 4, 30))
        with self.assertRaises(ValueError):
            self.l.settle('w', 'p', 'a', 4, 31)

    def test_scope(self):
        self.l.reserve('w', 'p', 'a', 5, 50)
        for ws, period in [('other', 'p'), ('w', 'next')]:
            with self.assertRaises(ValueError):
                self.l.settle(ws, period, 'a', 1, 1)
            with self.assertRaises(ValueError):
                self.l.reserve(ws, period, 'a', 1, 1)

    def test_concurrent_reserve(self):
        def attempt(job):
            try:
                return self.l.reserve('w', 'p', job, 10, 100)
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt, ['a', 'b'])), 1)

    def test_invalid_amount(self):
        with self.assertRaises(ValueError):
            self.l.reserve('w', 'p', 'a', -1, 0)

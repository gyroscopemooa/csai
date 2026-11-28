import unittest
from special_fixture_identity import fixture_identity


class FixtureIdentityTests(unittest.TestCase):
    def setUp(self):
        self.report = dict(complete=True, revision='r', suite='s', evaluator_version='v')

    def test_same_day(self):
        self.assertEqual(fixture_identity(self.report, 100), fixture_identity(self.report, 86399))

    def test_next_day(self):
        self.assertNotEqual(fixture_identity(self.report, 100), fixture_identity(self.report, 86400))
        self.assertEqual(fixture_identity(self.report, 86401)[1], 86400)

    def test_versions_separate(self):
        old = fixture_identity(self.report, 100)
        for key in ('revision', 'suite', 'evaluator_version'):
            self.assertNotEqual(old, fixture_identity(self.report | {key: 'new'}, 100))

    def test_invalid(self):
        for report, stamp in [(self.report | {'complete': False}, 100), (self.report | {'suite': ''}, 100), (self.report, -1), (self.report, True)]:
            with self.assertRaises(ValueError):
                fixture_identity(report, stamp)

import unittest
from dataclasses import replace
from special_entitlements import Grant, quote, entitled_features, remaining_cost_budget


class SpecialTests(unittest.TestCase):
    def setUp(self):
        self.grant = Grant('w', 'special_intelligence', 10, 30, 'paid', 'server-payment')
        self.args = dict(workspace='w', now=20, enabled=True)

    def test_prices(self):
        self.assertEqual(quote(['special_all'])['monthly_krw'], 99000)
        self.assertEqual(quote(['special_intelligence', 'special_learning', 'special_automation'])['monthly_krw'], 129700)

    def test_deduplication(self):
        self.assertEqual(quote(['special_all', 'special_learning', 'special_all'])['items'], ['special_all'])
        self.assertFalse(quote(['special_all'])['available_for_purchase'])

    def test_unknown_product(self):
        with self.assertRaises(ValueError):
            quote(['all'])

    def test_default_disabled(self):
        self.assertFalse(entitled_features([self.grant], workspace='w', now=20))

    def test_paid_grant(self):
        self.assertIn('advanced_retrieval', entitled_features([self.grant], **self.args))
        self.assertNotIn('external_tools', entitled_features([self.grant], **self.args))

    def test_all_in_one(self):
        self.assertIn('combined_report', entitled_features([replace(self.grant, package='special_all')], **self.args))

    def test_invalid_grants(self):
        for grant in [replace(self.grant, workspace='other'), replace(self.grant, status='refunded'), replace(self.grant, ends_at=20), replace(self.grant, starts_at=21), replace(self.grant, payment_ref='')]:
            self.assertFalse(entitled_features([grant], **self.args))

    def test_cost_ceiling(self):
        self.assertEqual(remaining_cost_budget(net_revenue_krw=90000, committed_cost_krw=4000, reserved_cost_krw=1000), 4000)
        self.assertEqual(remaining_cost_budget(net_revenue_krw=100, committed_cost_krw=11, reserved_cost_krw=0), 0)

    def test_invalid_cost(self):
        with self.assertRaises(ValueError):
            remaining_cost_budget(net_revenue_krw=100, committed_cost_krw=-1, reserved_cost_krw=0)

import unittest
from special_lookup_preview import compare_lookup


class LookupTests(unittest.TestCase):
    def test_approved_only(self):
        report=compare_lookup({'faq':[{'q':'배송 기간','a':'비공개 답변'}],
                               'draft':[{'q':'물건 언제 와요','a':'draft'}]},'물건 언제 와요?')
        self.assertEqual(report['pilot'],['배송 기간'])
        self.assertNotIn('비공개 답변',str(report))
        self.assertNotIn('draft',str(report))

    def test_exact(self):
        r=compare_lookup({'faq':[{'q':'배송 기간','a':'2일'}]},'배송기간?')
        self.assertEqual(r['pilot'],['배송 기간'])

    def test_invalid_and_empty(self):
        self.assertEqual(compare_lookup({'faq':'bad'},'배송')['status'],'unavailable')
        self.assertEqual(compare_lookup({},'배송')['pilot'],[])
        with self.assertRaises(ValueError):
            compare_lookup({},' ')

    def test_malformed_records(self):
        r=compare_lookup({'faq':[None,{}, {'q':'배송 기간','a':'2일'}]},'배송 기간')
        self.assertEqual(r['approved_count'],1)

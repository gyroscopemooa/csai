import unittest
from dataclasses import replace
from knowledge_graph import KnowledgeGraph, record_id
from scoped_memory import MemoryFact, current_memory


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{'q': '배송', 'a': '2일'}, {'q': '포장', 'a': '박스'}]
        self.ids = [record_id(r) for r in self.rows]
        self.graph = KnowledgeGraph.build('a', 'r1', self.rows, [self.ids])
        self.args = dict(workspace='a', revision='r1', approved=self.rows, seeds=self.ids[:1], enabled=True)

    def test_related(self):
        self.assertEqual(self.graph.related(**self.args), self.rows[1:])

    def test_scope_and_off(self):
        for update in [{'workspace': 'b'}, {'revision': 'r2'}, {'enabled': False}]:
            self.assertEqual(self.graph.related(**(self.args | update)), [])

    def test_stale_content(self):
        self.assertEqual(self.graph.related(**(self.args | {'approved': self.rows[:1]})), [])

    def test_unapproved_link(self):
        with self.assertRaises(ValueError):
            KnowledgeGraph.build('a', 'r1', self.rows, [(self.ids[0], 'unknown')])


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.fact = MemoryFact('a', 'c', 'language', 'ko', 10, 30, True)
        self.args = dict(workspace='a', customer='c', now=20, consent=True, enabled=True)

    def test_current(self):
        self.assertEqual(current_memory([self.fact], **self.args), {'language': 'ko'})

    def test_isolation_and_consent(self):
        for update in [{'workspace': 'b'}, {'customer': 'd'}, {'consent': False}, {'enabled': False}]:
            self.assertEqual(current_memory([self.fact], **(self.args | update)), {})

    def test_expired_revision_does_not_resurrect(self):
        newer = replace(self.fact, value='en', approved_at=12, expires_at=19)
        self.assertEqual(current_memory([self.fact, newer], **self.args), {})

    def test_approval_and_allowed_values(self):
        for fact in [replace(self.fact, approved=False), replace(self.fact, key='phone'), replace(self.fact, value='untrusted'), replace(self.fact, approved_at=21)]:
            self.assertEqual(current_memory([fact], **self.args), {})

    def test_conflicting_revision(self):
        self.assertEqual(current_memory([self.fact, replace(self.fact, value='en')], **self.args), {})

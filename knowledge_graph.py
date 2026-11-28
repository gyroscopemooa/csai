"""Bounded, scoped relationships between approved FAQ records; offline only."""
from dataclasses import dataclass
import hashlib
import json


def record_id(row):
    return hashlib.sha256(json.dumps([row['q'], row['a']], ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class KnowledgeGraph:
    workspace: str
    revision: str
    nodes: frozenset
    edges: tuple

    @classmethod
    def build(cls, workspace, revision, approved, links):
        if not workspace or not revision or len(approved) > 500 or len(links) > 2000:
            raise ValueError('invalid graph bounds')
        nodes = frozenset(record_id(row) for row in approved)
        edges = set()
        for a, b in links:
            if a not in nodes or b not in nodes or a == b:
                raise ValueError('invalid approved relationship')
            edges.add(tuple(sorted((a, b))))
        return cls(workspace, revision, nodes, tuple(sorted(edges)))

    def related(self, *, workspace, revision, approved, seeds, enabled=False):
        if not enabled or (workspace, revision) != (self.workspace, self.revision):
            return []
        if len(approved) > 500 or len(seeds) > 5:
            return []
        current = {record_id(row): row for row in approved}
        if self.nodes != current.keys() or not set(seeds) <= self.nodes:
            return []
        selected = set(seeds)
        neighbors = {b for a, b in self.edges if a in selected} | {a for a, b in self.edges if b in selected}
        return [current[k] for k in sorted(neighbors - selected)[:5]]

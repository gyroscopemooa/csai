"""Scoped hybrid FAQ retrieval core; no network, persistence or model calls."""
from dataclasses import dataclass
import hashlib
import json
import math
import re

MAX_RECORDS = 500
MAX_DIMENSIONS = 4096


def fingerprint(row):
    q, a = row['q'], row['a']
    if not isinstance(q, str) or not isinstance(a, str) or not q.strip() or not a.strip():
        raise ValueError('invalid approved FAQ')
    return hashlib.sha256(json.dumps([q, a], ensure_ascii=False).encode('utf-8')).hexdigest()


def unit(values):
    if not 1 <= len(values) <= MAX_DIMENSIONS:
        raise ValueError('invalid vector dimension')
    if any(type(v) not in (int, float) for v in values):
        raise ValueError('invalid vector element')
    numbers = tuple(float(v) for v in values)
    if not all(math.isfinite(v) for v in numbers):
        raise ValueError('nonfinite vector')
    norm = math.hypot(*numbers)
    if not math.isfinite(norm) or norm == 0:
        raise ValueError('invalid vector norm')
    return tuple(v / norm for v in numbers)


@dataclass(frozen=True)
class FAQVectorIndex:
    workspace: str
    revision: str
    encoder: str
    records: tuple
    dimension: int

    @classmethod
    def build(cls, workspace, revision, encoder, approved, vectors):
        if not all(isinstance(v, str) and v.strip() for v in (workspace, revision, encoder)):
            raise ValueError('scope required')
        if len(approved) != len(vectors) or not 1 <= len(approved) <= MAX_RECORDS:
            raise ValueError('invalid vector batch')
        records, seen = [], set()
        dimension = len(vectors[0])
        for row, vector in zip(approved, vectors):
            key = fingerprint(row)
            normalized = unit(vector)
            if len(normalized) != dimension:
                raise ValueError('mixed dimensions')
            if key not in seen:
                records.append((key, normalized))
                seen.add(key)
        return cls(workspace, revision, encoder, tuple(records), dimension)

    def rank(self, *, workspace, revision, encoder, query_vector, approved, threshold=0.75):
        if (workspace, revision, encoder) != (self.workspace, self.revision, self.encoder):
            return []
        if not 0.5 <= threshold <= 1 or len(approved) > MAX_RECORDS:
            raise ValueError('invalid ranking bounds')
        current = {fingerprint(row): row for row in approved}
        if set(current) != {key for key, _ in self.records}:
            return []
        vector = unit(query_vector)
        if len(vector) != self.dimension:
            return []
        ranked = []
        for key, record in self.records:
            score = sum(a * b for a, b in zip(vector, record))
            if score >= threshold:
                ranked.append((score, key))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [current[key] for _, key in ranked[:5]]


def hybrid_candidates(*, query, legacy, approved, index, workspace, revision, encoder,
                      query_vector, enabled=False):
    """Select evidence only. Scope and embeddings must come from trusted server state."""
    if not enabled or not isinstance(index, FAQVectorIndex) or not isinstance(query, str) or re.search(r'\d', query):
        return legacy
    try:
        ranked = index.rank(workspace=workspace, revision=revision, encoder=encoder,
                            query_vector=query_vector, approved=approved)
        if not ranked:
            return legacy
        result, seen = [], set()
        for row in [*legacy[:2], *ranked[:2], *legacy[2:]]:
            key = fingerprint(row)
            if key not in seen and len(result) < 5:
                result.append(row)
                seen.add(key)
        return result
    except (ValueError, TypeError, KeyError, OverflowError, AttributeError):
        return legacy

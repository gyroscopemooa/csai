"""Opt-in incremental index preparation. No default provider or persistence."""
from dataclasses import dataclass
from hybrid_retrieval import FAQVectorIndex, MAX_RECORDS, fingerprint


@dataclass(frozen=True)
class IndexPlan:
    rows: tuple
    reused: tuple
    missing: tuple
    removed: int
    input_bytes: int


def plan_index(*, workspace, revision, encoder, approved, previous=None):
    if not all(isinstance(x, str) and x.strip() for x in (workspace, revision, encoder)):
        raise ValueError('scope required')
    if len(approved) > MAX_RECORDS:
        raise ValueError('FAQ limit exceeded')
    old = {}
    if isinstance(previous, FAQVectorIndex) and (previous.workspace, previous.encoder) == (workspace, encoder):
        old = dict(previous.records)
    rows, missing, reused, seen = [], [], [], set()
    for row in approved:
        key = fingerprint(row)
        if key in seen:
            continue
        seen.add(key)
        # Use the approved question only, never a raw customer conversation.
        question = row['q']
        if len(question.encode('utf-8')) > 4096:
            raise ValueError('question too long')
        rows.append((key, question, row['a']))
        if key in old:
            reused.append((key, old[key]))
        else:
            missing.append((key, question))
    return IndexPlan(tuple(rows), tuple(reused), tuple(missing), len(set(old) - seen),
                     sum(len(q.encode('utf-8')) for _, q in missing))


def refresh_index(*, workspace, revision, encoder, approved, previous=None,
                  embed=None, enabled=False, max_new=0, max_bytes=0):
    """Never call an encoder until the complete job fits the supplied budget.

    A trusted caller must reserve spend before providing an external encoder.
    Failed jobs raise without publishing partial results; no retry is attempted.
    The caller must check the approved revision again before publishing.
    """
    if not enabled:
        return None
    if type(max_new) is not int or type(max_bytes) is not int or max_new < 0 or max_bytes < 0:
        raise ValueError('invalid budget')
    plan = plan_index(workspace=workspace, revision=revision, encoder=encoder,
                      approved=approved, previous=previous)
    if not plan.rows:
        return None
    if len(plan.missing) > max_new or plan.input_bytes > max_bytes:
        raise ValueError('index budget exceeded')
    vectors = dict(plan.reused)
    if plan.missing:
        if not callable(embed):
            raise ValueError('encoder required')
        values = list(embed([question for _, question in plan.missing]))
        if len(values) != len(plan.missing):
            raise ValueError('encoder count mismatch')
        vectors.update((key, vector) for (key, _), vector in zip(plan.missing, values))
    return FAQVectorIndex.build(workspace, revision, encoder,
                                [{'q': q, 'a': a} for _, q, a in plan.rows],
                                [vectors[key] for key, _, _ in plan.rows])

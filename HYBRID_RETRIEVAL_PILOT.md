# Hybrid FAQ retrieval: offline core

Adds a bounded vector ranking core accepting precomputed embeddings and combining scoped candidates with legacy retrieval. It does not connect to the live answer path, generate embeddings, persist vectors, or install a vector database.

- No new credentials, external calls, paid dependencies, payment changes, or schema migrations.
- Disabled by default. A future server adapter must derive workspace, approved revision, and encoder version from authenticated server state. Never accept these or embeddings from a customer payload.
- Mismatched approved FAQ fingerprints or scope discard semantic results. Existing authoritative FAQ, permissions, and business validation remain unchanged.
- The initial in-memory index holds up to 500 FAQs. Threshold 0.75 is provisional; test real held-out queries, similar products, negation, and policy exceptions before rollout.
- Offline unit tests use artificial vectors, not live embedding quality. Run python -m unittest discover -s tests -p test_hybrid_retrieval.py.
- Next: approval-triggered incremental indexing, optional embedding adapter with budget and usage tracking, contextual metadata, isolated storage, and server-controlled pilot. Keep billing and live activation unchanged.

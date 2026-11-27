# Query vector cache pilot

- Off by default, in-memory only, exact question reuse with workspace, approved revision and encoder isolation.
- Stores normalized vectors and process-keyed digests, not raw question strings or generated answers. Embeddings are still derived data and must be treated accordingly.
- Requires explicit trusted caller approval of cacheability. Do not cache personal or confidential queries; privacy classification and deletion integration are prerequisites for live use.
- Bounded capacity, short TTL, explicit clear. No distributed persistence, answer caching, external API or billing changes.
- Run python -m unittest discover -s tests -p test_retrieval_cache.py.

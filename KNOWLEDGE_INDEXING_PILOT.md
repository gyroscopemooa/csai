# Incremental knowledge indexing pilot

- Reuse unchanged approved FAQ vectors within the same workspace and encoder revision. Deleted or changed FAQ records are excluded from the next index.
- Deduplicate input, limit new record count and UTF-8 input size before invoking the injected encoder. These limits are not a currency/token billing system.
- The encoder is dependency-injected; default disabled. No external provider, live API call, persistence, schema change or checkout integration in this increment.
- The trusted server caller must authorize scope, reserve/settle actual spend, validate the approved revision at publish time, and supply the encoder only in an isolated pilot. Never enable live features via customer-supplied flags.
- Unit tests use a mocked encoder. Run python -m unittest discover -s tests -p test_knowledge_indexing.py.

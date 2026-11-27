# Knowledge retrieval pilot

- Default: disabled. Keep CSAI_KNOWLEDGE_RETRIEVAL=off or unset.
- No new provider, API calls, credentials, database writes, paid dependency or product catalog change.
- First increment: deterministic Korean domain phrase expansion and FAQ candidate reranking. This is not embedding-based Hybrid RAG, contextual RAG, or a complete semantic search implementation.
- Existing approved FAQ direct answers, booking, training, prompt, model, permission checks, credits and pricing remain unchanged.
- Pilot mode uses existing tenant-scoped FAQ inputs only; it never generates an answer or accesses another tenant. It preserves the top legacy candidates and falls back on errors.
- Enable only in an isolated test environment with CSAI_KNOWLEDGE_RETRIEVAL=pilot, after merging against the latest local changes. This is a global process-level switch, not a customer entitlement. Do not enable it in production yet.
- Run python -m unittest discover -s tests -p test_knowledge_retrieval.py and the complete project regression suite. Validate retrieval recall, wrong-product/policy matches, actual response quality, latency and API usage against the unmodified engine before enabling.
- Further work: embedding retrieval and versioned indexing, approved document context, controlled reranking, cache eligibility and invalidation, scoped memory, evaluation/learning and workflow tools. No paid-feature activation before permission checks, measured costs, usage limits and billing validation. Keep the existing catalog unchanged.
- Do not log customer queries or knowledge content in operational telemetry.

# Context retrieval and knowledge review pilot

- CSAI_CONTEXT_RETRIEVAL=pilot enables a process-level test only. Unset or off is the default. No new model calls, charges, credentials, storage, or checkout changes.
- Short follow-ups may add approved FAQ evidence based on the last customer turn only. The actual message and existing policies remain unchanged. Limited to delivery, opening hours and stock concepts; sensitive and ambiguous requests keep the legacy retrieval.
- This is a conservative lexical contextual retrieval pilot, not complete Contextual RAG or GraphRAG.
- knowledge_diagnostics identifies duplicate FAQ entries, invalid records and differing answers to normalized matching questions. Review candidates are not confirmed contradictions; no automatic edits or deletion.
- Diagnostics remain offline until an authorized owner-only review API is implemented.
- Run python -m unittest discover -s tests -p test_contextual_knowledge.py; validate full app and actual model responses before any live activation.

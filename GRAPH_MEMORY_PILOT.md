# Knowledge graph and scoped memory pilot

Offline foundation only; no automatic relationship generation, database persistence, model integration, customer profiling or production activation. Graph links must be supplied by a trusted approved-knowledge workflow; revision or content mismatch discards graph evidence. Memory accepts only approved language and response-length preferences, with explicit consent, expiry and tenant/customer scope. Do not use customer-supplied scope or consent flags; identity, consent, revocation, deletion and retention integration are prerequisites. No API calls or billing changes.

Test: python -m unittest discover -s tests -p test_graph_memory.py

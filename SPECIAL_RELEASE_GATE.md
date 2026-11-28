# SPECIAL verification and release gate

## Verified offline snapshot
Source commit: bc005455b010ada4b23a04c1f89c6a1fda31e49d.
The 19 listed offline test files, their imported SPECIAL modules and the test runner were copied into an isolated Python environment and their Git blob hashes matched the branch. Running `python scripts/special_offline_checks.py` collected 155 tests; all 155 passed, no skips. Python compilation passed for the copied source set. No real API or payment provider was invoked. This is a test result for this snapshot, not a production quality or completion percentage.

The GitHub Actions run 46126121237 failed before reporting test steps. Its cause is not established. The isolated environment could not clone the full repository because github.com DNS resolution failed. These limitations prevent claiming full application regression coverage.

## Remaining gates (not passed)
- Integrate the current feature branch with the latest local application changes, resolving app.py and web assets without discarding concurrent edits.
- Run full app dependencies and SQLite/PostgreSQL regression tests, including tests/test_special_preview_api.py, and verify the local developer preview in a browser.
- Keep pilot/default-off behavior and existing basic features/pricing intact. Add verified payment-to-entitlement synchronization, transaction-safe production credit accounting and reconciliation before enabling purchase.
- Connect and validate real provider adapters, durable indexes, tenant/brand/customer isolation, consent/retention, approved tool permissions and audit controls. No external mutations without validated authorization.
- Measure real answer quality, latency, provider usage and full costs before activating individual packages. The synthetic check pass rate is not an AI accuracy or profitability metric.
- Implement and verify any remaining advertised capabilities before sale; preview descriptions are planned scope, not a promise of availability.
- Review the final diff and deployment separately. No main merge, live payment, production activation or deployment has occurred here.

For local validation, run the offline runner first, then the full application test suite in an isolated test environment with provider credentials disabled. Fix failures before advancing the release gate.

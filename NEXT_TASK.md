# Next Task for Agent

## Status
- Working tree: clean except ethscan/radix.py (indentation fix, uncommitted).
- Tests: 3900 passed, 1 skipped (green baseline).
- Repository complete: 53 CLI commands register on import.

## Current issues (do not touch unless new requirement explicitly requires changing behavior)
- ruff BLE001 (33) — many tests mock/plain-raise Exception paths; narrowing breaks behavior.
- ruff TRY002 (12) — tests expect raising plain Exception in certain mocked paths.
- ruff PLR0402 (1) — in tests/test_brute.py; reload semantics depend on import form.

## Completed this session
- Fixed indentation corruption in ethscan/radix.py (_merge_networks) so collection/tests run.
- Restored behavior of exception handling in cidr/trace/web where tests mock Exception to satisfy specific test expectations.
- Confirmed 3900 passed, 1 skipped after fixes.

## Next precise task
- None remaining. Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan).
- If a new issue arrives, implement the smallest verifiable change, run focused tests + `python -m pytest -q` and relevant lint checks, and preserve baseline.

# Next Task for Agent

## Status
- Working tree: clean at HEAD aa2f1cb except uncommitted lint fixes in 4 test files (not yet committed).
- Tests: 3900 passed, 1 skipped (green baseline).
- Repository complete: 53 CLI commands with CLI-level tests.

## Repository state
- Lint (ruff): 55 errors (was 62). RUF059 (4), RUF013 (2), RUF012 (1), FA102 (3), C405 (2) all cleared.
  - Remaining: BLE001 (42, unsafe to narrow), TRY002 (12, raises plain `Exception` as mocks in tests), PLR0402 (1, breaks reload test).
- No S110 errors remaining.

## Next precise task
- None remaining. All clearly-safe bounded lint tasks are exhausted.
- Do NOT reopen BLE001 narrowing (proven to break tests: tests mock plain `Exception` and assert the broad handler swallows it).
- Do NOT retry PLR0402 in tests/test_brute.py:504 (breaks `test_paramiko_import_error`, reload semantics).
- Await a genuine new issue/requirement before further speculative changes.

## Instructions
- Do NOT make speculative changes beyond the completed fixes unless a genuine new issue/requirement arrives.
- If a new issue arrives, implement the smallest verifiable change and confirm with `python -m pytest -q` and `python -m ruff check --select <affected codes>`.
- Preserve the working baseline.

(End of file - total 24 lines)
# Next Task for Agent

## Status
- Working tree: clean at HEAD aa2f1cb except uncommitted UP006/UP035 fixes in tests/test_dnsbrute.py and tests/test_ssh.py (not yet committed).
- Tests: 3900 passed, 1 skipped (green baseline).
- Repository complete: 53 CLI commands with CLI-level tests.

## Repository state
- Lint (ruff): 89 errors (was 107). UP006 (14) + UP035 (4) fully cleared.
  - Remaining: BLE001 (42, unsafe to narrow), TRY002 (12), RUF013 (10), RUF059 (10), F811 (9), C405 (2), SIM222 (1), ISC004 (1), PLR0402 (1), RUF012 (1).
- No S110 errors remaining.

## Next precise task
- C405 (2 errors) in tests/test_cli.py:4423 and :4784: rewrite `set([20, 21, 22, ...])` as set literal `{20, 21, 22, ...}`.
- Safe, bounded, mechanical. Verify with `python -m ruff check --select C405 tests/test_cli.py` and `python -m pytest -q`.
- Do NOT reopen BLE001 narrowing (proven to break tests: tests mock plain `Exception` and assert the broad handler swallows it).
- After C405, no remaining clearly-safe bounded lint task; await a genuine new issue/requirement.

## Instructions
- Do NOT make speculative changes beyond C405 unless a genuine new issue/requirement arrives.
- If a new issue arrives, implement the smallest verifiable change and confirm with `python -m pytest -q` and `python -m ruff check --select <affected codes>`.
- Preserve the working baseline.

(End of file)

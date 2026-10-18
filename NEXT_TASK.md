# Next Task for Agent

## Status
- Working tree: clean at HEAD except one uncommitted change to ethscan/cli.py (moved `if __name__ == "__main__": cli()` guard from mid-file to EOF). Not yet committed.
- Tests: 3900 passed, 1 skipped (green baseline).
- Repository complete: 53 CLI commands with CLI-level tests; all 53 register on import.

## Repository state
- Lint (ruff): 55 errors (was 62). RUF059 (4), RUF013 (2), RUF012 (1), FA102 (3), C405 (2) all cleared.
  - Remaining: BLE001 (42, unsafe to narrow), TRY002 (12, raises plain `Exception` as mocks in tests), PLR0402 (1, breaks reload test).
- No S110 errors remaining. `python -m ruff check ethscan/cli.py` clean.

## This session (2026-10-18)
- Fixed a latent command-registration bug in ethscan/cli.py: the `if __name__ == "__main__": cli()` guard sat mid-file directly before the `redis`, `ldap`, `mssql`, and `oracle` command definitions. Because `cli()` blocks, those four commands were never registered when cli.py was executed directly as `__main__`. Moved the guard to the end of the file so all commands register before `cli()` runs. (A collateral edit to the `completion` command's `click.echo(...)` line was reverted.)
- Re-verified baseline green: `python -m pytest -q` -> 3900 passed, 1 skipped, 2 warnings.
- Confirmed no new safe bounded task remains (55 ruff errors: BLE001/TRY002/PLR0402, all previously proven unsafe).
- A stash (`stash@{0}`) holds abandoned experimental source changes; do not merge without review.

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
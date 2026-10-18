# Next Task for Agent

## Status
- Working tree: clean (HEAD: 960e5e1). No uncommitted changes.
- Tests: 3902 passed, 1 skipped (green baseline).
- Repository complete: 53 CLI commands with CLI-level tests.

## Repository state
- Lint (ruff): 40 errors (40 BLE001 [blind-except]). UP045 fully resolved.
- No S110 errors remaining.

## Next precise task
There is no remaining bounded, safe task in this repository.

## Instructions
- Do NOT make speculative changes. Await a genuine new issue/requirement before making changes.
- If a new issue arrives, implement the smallest verifiable change.
- Preserve the working baseline (do not reopen BLE001 narrowing — proven to break tests).
- Verify with: `python -m pytest -q` and `python -m ruff check --select <affected codes>`.

(End of file - total 19 lines)
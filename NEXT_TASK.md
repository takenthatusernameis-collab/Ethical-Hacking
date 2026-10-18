# Next Task for Agent

## Status
- Working tree: clean (HEAD: 9c43623). No uncommitted changes.
- Tests: 3902 passed, 1 skipped (green baseline).
- Repository complete: all 52 CLI commands have CLI-level tests; README matches cli.py commands exactly.

## Repository state
- Lint (ruff): 489 errors (445 UP045 [non-PEP604 Optional], 42 BLE001 [blind-except], 2 S110 [try-except-pass in redis.py:223-224, 242-243]).
- mypy: ~522 errors in 42 files — not targeted.
- Coverage: 70 missing lines — documented unreachable/environment-dependent.
- No untested commands, no stale docs.

## Next precise task
There is no remaining bounded, safe task in this repository.

## Instructions
- Do NOT make speculative changes. Await a genuine new issue/requirement before making changes.
- If a new issue arrives, implement the smallest verifiable change.
- Preserve the working baseline (do not reopen BLE001 narrowing — proven to break 3 tests; do not change the 2 S110 sites in redis.py — load-bearing).
- Verify with: `python -m pytest -q` and `python -m ruff check --select <affected codes>`.
- Record findings/evidence if blocked (especially if tests explicitly mock plain Exception).

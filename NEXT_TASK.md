# Next Task for Agent

## Status
- Working tree: clean (HEAD: 9c43623). No uncommitted changes.
- Tests: 3902 passed, 1 skipped (green baseline).
- Repository complete: all 52 CLI commands have CLI-level tests; README matches cli.py commands exactly.

## Repository state
- Lint: 489 errors (445 UP045, 42 BLE001, 2 S110). BLE001 narrowing attempted and proven unsafe (breaks 3 tests; see HANDOFF_NEXT.md). No safe bounded lint tasks.
- No untested commands, no stale docs.

## Next precise task
There is no remaining bounded, safe task in this repository.
- Do NOT make speculative changes.
- Await a genuine new issue/requirement before making changes.
- If a new issue arrives, implement the smallest verifiable change and confirm with python -m pytest -q and python -m ruff check --select <codes>.

# Next Task for Agent

## Status
- Working tree: clean (HEAD 2e19dd4)
- Tests: 3902 passed, 1 skipped (green baseline)
- Repository: 53 CLI commands register on import; `python -m ethscan --help` and `--version` OK
- Lint: 43 ruff errors (30 BLE001 in source, 12 TRY002 in tests, 1 PLR0402 in tests/test_brute.py) — all intentional/unsafe to fix
- Coverage: ethscan source 12604 stmts, 48 missing (~99%); gaps are unreachable/defensive

## Constraints (do not touch)
- Do not modify code to "fix" the 43 documented ruff errors (BLE001/TRY002/PLR0402) — they are behavior-dependent on existing tests
- Preserve baseline; avoid speculative refactors

## Next precise task
- None assigned. Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan).
- If proactively selecting a task, choose one that is: bounded, high-value, verifiable, behavior-preserving, and does not touch the documented lint exceptions. Run focused tests + `python -m pytest -q` + relevant checks before concluding.

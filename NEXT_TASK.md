# Next Task for Agent

## Status
- Working tree: clean except restored untracked `tests/test_hash.py` (awaiting commit).
- Tests: 3904 passed, 1 skipped (green baseline, +126 hash tests).
- Repository: 53 CLI commands register on import; `python -m ethscan --help` and `--version` OK
- Lint: 44 ruff errors (30 BLE001 in source, 12 TRY002 in tests, 1 PLR0402 in tests/test_brute.py) — all intentional/unsafe to fix
- Coverage: ethscan source ~99%; hash.py now 98% (was 84%).

## Constraints (do not touch)
- Do not modify code to "fix" the 44 documented ruff errors (BLE001/TRY002/PLR0402) — they are behavior-dependent on existing tests
- Preserve baseline; avoid speculative refactors

## Next precise task
- None assigned. Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan).
- If proactively selecting a task, choose one that is: bounded, high-value, verifiable, behavior-preserving, and does not touch the documented lint exceptions. Run focused tests + `python -m pytest -q` + relevant checks before concluding.
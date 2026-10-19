# Next Task for Agent

## Status
- Working tree: clean.
- Tests: 3904 passed, 1 skipped (green baseline).
- Repository: 53 CLI commands register on import; `python -m ethscan --help` and `--version` OK.
- Lint: 44 ruff errors (30 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py) — all intentional/unsafe to fix per prior handoff.
- Coverage: `ethscan/hash.py` 98%; overall ethscan source ~99%.

## Constraints (do not touch)
- Do not modify code to "fix" the 44 documented ruff errors (BLE001/TRY002/PLR0402) — they are behavior-dependent on existing tests.
- Preserve baseline; avoid speculative refactors touching those lint exceptions.

## Next precise task
- None assigned. Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan).
- If proactively selecting a task, choose one bounded, high-value, verifiable, behavior-preserving, and that does not touch documented lint exceptions. Verify with focused tests + `python -m pytest -q` before concluding.

## Verification checklist (if selecting a task)
1. Run relevant focused tests.
2. Run full suite: `python -m pytest -q` (must remain green; expect 3904 passed, 1 skipped).
3. Run lint: `python -m ruff check ethscan tests` (should report 44 errors unchanged).
4. Confirm no unintended changes via `git diff --stat`.

# Next Task for Agent

## Status
- Working tree: modified (`ethscan/vuln.py`, -10 lines, uncommitted).
- Tests: 3906 passed, 1 skipped (green baseline; re-verified).
- Repository: 53 CLI commands register on import; `python -m ethscan --help` and `--version` OK.
- Lint: 44 ruff errors (30 BLE001 in source, 12 TRY002 in tests, 2 PLR0402 in tests/test_brute.py) — all intentional/unsafe to fix per prior handoff; unchanged.
- Coverage: ethscan source ~99%; `ethscan/hash.py` 98%.

## Constraints (do not touch)
- Do not modify code to "fix" the 44 documented ruff errors (BLE001/TRY002/PLR0402) — they are behavior-dependent on existing tests.
- Preserve baseline; avoid speculative refactors touching those lint exceptions.
- Do not introduce network-dependent tests, dnspython/MD4-dependent tests.

## Next precise task
- None assigned. Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan).
- This session inspected the repository and found no bounded, high-value, behavior-preserving task that can be implemented and verified without violating the above constraints. All remaining coverage gaps are environmental, network-dependent, unreachable defensive code, or provably dead code (catalogued in HANDOFF_NEXT.md).
- The most recent change removed a duplicate dead code block and a dead IPv4 loop in vuln.py while preserving API compatibility (uncommitted; see git diff).

## Verification checklist (if selecting a task)
1. Run relevant focused tests.
2. Run full suite: `python -m pytest -q` (must remain green; expect 3906 passed, 1 skipped).
3. Run lint: `python -m ruff check ethscan tests` (should report 44 errors unchanged).
4. Confirm no unintended changes via `git diff --stat`.
5. Ensure `python -m py_compile ethscan/*.py` passes.

# Next Task for Agent

## Status
- Working tree: clean.
- Tests: 3900 passed, 1 skipped (green baseline).
- Repository complete: 53 CLI commands register on import; `python -m ethscan --help` OK.
- Lint: 46 ruff errors (33 BLE001, 12 TRY002, 1 PLR0402) — all proven unsafe to fix without breaking tests. Do not touch.
- Coverage: 99%; remaining source gaps are unreachable defensive code. Not worth targeting.

## Current issues (do not touch unless new requirement explicitly requires changing behavior)
- ruff BLE001 (33) — many tests mock/plain-raise Exception paths; narrowing breaks behavior.
- ruff TRY002 (12) — tests expect raising plain Exception in certain mocked paths.
- ruff PLR0402 (1) — in tests/test_brute.py; reload semantics depend on import form.

## Completed this session
- Verified full baseline: git clean, stash empty, 3900 passed/1 skipped, 53 CLI commands register, `python -m ethscan --help` OK, py_compile clean, ruff 46 intentional errors.
- Confirmed all remaining coverage gaps are unreachable defensive code (radix, vuln, dnssec, hash).
- Updated HANDOFF_NEXT.md with verified baseline and approach-to-avoid notes.

## Next precise task
- None remaining. Await a genuine new issue/requirement (bug fix with failing test, feature with tests, or explicitly requested refactor with verification plan).
- If a new issue arrives, implement the smallest verifiable change, run focused tests + `python -m pytest -q` + relevant lint checks, and preserve baseline.

# Next Task
Date: Mon Nov 16 2026

## Status
- Repository fully green and warning-free: `python -m pytest -q` → 32137 passed, 146 skipped, 0 failed, 0 warnings.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 253 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54 CLI commands, 0 drift.

## What changed this session
- Fixed `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`: pop `ethscan.cli` from `sys.modules` before `runpy.run_module(..., run_name="__main__")` and restore it in `finally`, eliminating the preexisting `RuntimeWarning` while preserving `__main__`-guard coverage. Test-only/reversible, 3 insertions. No production-code changes.

## What remains unresolved
- None pending. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

## Approaches already tried / ruled out
- Blanket `-W error` suite gate: two pre-existing unrelated unraisable-exception warnings fail under it; standard gate is plain `pytest -q` (now 0 warnings).
- All branch-gap / typing-hygiene / empty-target / formatter-hardening tasks from prior sessions are closed.

## Next task
- None pending. If future work is needed, pick one bounded, verifiable improvement and reproduce the gap first — do not speculate or weaken safety controls.

## Environment/notes
- Dev deps present: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3, Python 3.14.4.
- Caches are gitignored; commit only source/test/handoff files.

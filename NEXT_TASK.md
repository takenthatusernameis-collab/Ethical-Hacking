# Next Task

## Status
Repository is fully green: `python -m pytest -q` → 6106 passed, 53 skipped, 1 warning, 0 failed; `python -m mypy ethscan/ tests/` → clean across all 188 source files (the 2 pre-existing errors in `tests/test_smb.py:1437,1443` were resolved in session 106 by widening the SMB formatter signatures to `Mapping[str, Any]`); `python -m ruff check ethscan/ tests/` → all checks passed.

All `ethscan/` modules are at 100% coverage (TOTAL 15342 stmts, 0 miss).

## One precise next task
No pending coverage or typing-hygiene work remains. If future work is needed, pick a single high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls.

## Notes
- `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes` intentionally uses `runpy.run_module` and emits a `RuntimeWarning`; do not "fix" by weakening the test without evidence-based need.
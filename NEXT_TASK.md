# Next Task

## Task
- None pending. Repository is fully green.

## Evidence
- Baseline (this session): `pytest -q` → 5961 passed, 50 skipped, 0 failed; `mypy ethscan/ tests/` → clean (187 files); `ruff check ethscan/ tests/` → all checks passed.
- `report` empty/invalid-target handling is fixed and covered: `report --target ""|"   "|"https://"|":6379"` exits 2 with "Could not parse host from target"; `report` is in `TARGET_USAGE_ERROR_COMMANDS`; `tests/test_cli.py::test_report_invalid_target_is_usage_error` passes. Valid-target behavior unchanged.
- `oracle`/`postgresql` remain intentionally out of scope (in-band error contract, exit 0).

## Next task after that
- If future work is needed, pick a single high-value, verifiable improvement and reproduce it first. Do not speculate or weaken safety controls. Audit other target-consuming commands only if evidence shows a gap.

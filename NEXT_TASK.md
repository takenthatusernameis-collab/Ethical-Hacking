## Next task

None pending. Repository is fully green on BOTH click 8.1.x and 8.2+ with 100% statement/branch coverage.

Completed this session (the optional future task flagged in the prior handoff):
- Replaced the deprecated `click.__version__` in `ethscan/version.py:56` (DeprecationWarning on click 8.5+, removal in click 9.1) with `importlib.metadata.version("click")`, falling back to `"unknown"` on `PackageNotFoundError`. Removed the `import click` / `click.__version__` path.
- Updated `tests/test_version.py`: replaced the click import-error test with `test_collect_version_data_click_package_not_found` (metadata fallback) and added `test_collect_version_data_click_version_matches_metadata`.
- Updated `tests/test_cli_cov_gaps.py::test_version_dependency_attribute_errors` to drive the click fallback via `metadata.version` instead of a `__version__`-less `click` module.

Verification (evidence):
- `pytest -q` → 47449 passed, 150 skipped, 0 failed (baseline 47448; +1 new test).
- `mypy ethscan/ tests/` → Success: no issues in 270 source files.
- `ruff check ethscan/ tests/ check_readme.py` → All checks passed.
- `check_readme.py` → 54 commands, 0 drift both directions.
- `coverage run --branch --source=ethscan -m pytest -q` → TOTAL 100% (16210 stmts, 6112 branches, 0 missing).
- `grep -rn "click.__version__\|click_module" ethscan/ tests/` → no references remain.

Uncommitted changes: `ethscan/version.py`, `tests/test_version.py`, `tests/test_cli_cov_gaps.py` (controller commits).

Remaining / out of scope:
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error) per their documented contract.
- `ethscan/cli.py:4318` unreachable defensive guard (do not weaken safety or game coverage).

If future work is needed: reproduce a concrete gap first (fresh-install failure, focused failing check, or behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), preserve safety.

## Next task

None blocking. Repository green with 100% branch coverage. Do NOT fabricate work
or repeat verification-only sessions as progress.

### Completed this session (genuine defect fixed)
- Fixed `ethscan.version.format_version_report_csv` / `_markdown`: a report dict
  whose `dependencies` or `git` field was not a mapping raised `AttributeError`
  (violating the repo-wide formatter hostile contract). Now coerced to `{}`.
- Closed the contract-test gap: added `dependencies`/`git` to `_VALID_REPORT` in
  `tests/test_all_formatters_hostile_contract.py`.
- Added `tests/test_version.py::test_formatters_handle_hostile_nested_fields`.
- Evidence: reproduced the crash before the fix; mutation check (remove guards)
  makes the new test fail; restored -> pass.

### Verification performed this session (all green)
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> 49772 passed,
  147 skipped, 0 failed; TOTAL 100% (16258 stmts, 6148 branches, 0 missing).
- `python -m mypy ethscan/ tests/` -> Success: no issues in 271 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift; exit 0.
- `git diff --check` clean; `git status` -> 3 files modified, uncommitted.

### Remaining / next
- Nothing blocking. Before any work, re-run the gate to confirm the baseline,
  then probe for a GENUINE defect (focused failing check or behavioral evidence
  vs the documented contract). Do not fabricate work.
- Out of scope (do not change): oracle/postgresql empty-target handling;
  ethscan/cli.py unreachable defensive guard (~line 4318); .github/workflows/**.
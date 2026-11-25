## Next task

Repository is green (independently re-verified this session):
- `pytest -q` -> 47473 passed, 147 skipped, 0 failed
- `mypy ethscan/ tests/` -> clean (271 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> all checks passed
- `check_readme.py` -> 54 commands, 0 drift both directions
- Coverage `--branch --source=ethscan` -> TOTAL 100% (0 missing statements/branches)

This session fixed a reproduced defect: `ethscan/report.py` Markdown/CSV formatters
crashed (`TypeError`) on a non-iterable scalar nested in the `scan`/`audit` sub-dicts
(e.g. `{"scan": {"details": 1}}`). Added an `_as_list` guard + a regression test in
`tests/test_report_hostile_sweep.py` (mutation-checked). No other module affected
(broad nested-field fuzz: 0 other crashes).

Important: there is no pending task. Do not fabricate work or repeat verification-only
sessions as progress.

Out of scope (per documented contract, do not change):
- `oracle`/`postgresql` empty-target handling (exit 0, in-band error)
- `ethscan/cli.py:4318` unreachable defensive guard (documented known limitation)

If future work is needed: reproduce a concrete gap first (focused failing check or
behavioral evidence vs documented contract), apply the smallest safe fix, rerun focused
then broader gates (pytest/coverage/mypy/ruff/check_readme), preserve safety/validation.
Do not delete tests to go green; do not modify `.github/workflows/**` (reverted by the
controller).
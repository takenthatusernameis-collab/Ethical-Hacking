# Next Task

## Status
Session 141 added a permanent formatter hostile-sweep test file for `mysql` covering both `findings` and `handshake` fields (50 new tests). The module's formatters were already guarded inline via `_as_dict` and `isinstance(findings, (list, tuple))` (no source changes needed), but lacked dedicated hostile-sweep tests matching the pattern used by ftp, ntp, oracle, smtp, snmp, etc.

## One precise next task
- Add a similar formatter hostile-sweep test file for `postgresql` (next module in the group of 2 that lack dedicated formatter hostile-sweep tests). The `postgresql` formatters iterate over `startup` and `parameters` (via `_as_dict` guard). Create `tests/test_postgresql_formatter_hostile_sweep.py` following the `test_mysql_formatter_hostile_sweep.py` pattern:
  - Test `startup`: non-iterable scalars, hostile lists, well-formed regression
  - Test `parameters`: non-dict values, hostile dicts with non-string/nested values, well-formed regression
  - Cover both Markdown and CSV formatters
- Verify with `pytest tests/test_postgresql_formatter_hostile_sweep.py -q`, then full suite, mypy, ruff.
- Repository remains fully green: `pytest -q` -> 7253 passed, 149 skipped, 0 failed; mypy/ruff clean; check_readme 54/54.

(End of file - total 14 lines)
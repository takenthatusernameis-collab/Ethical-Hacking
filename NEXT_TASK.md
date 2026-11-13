# Next Task

## Status
Session 140 added a permanent formatter hostile-sweep test file for `mssql` covering both `findings` and `prelogin` fields (50 new tests). The module's formatters were already guarded inline via `_as_dict` (no source changes needed), but lacked dedicated hostile-sweep tests matching the pattern used by ftp, ntp, oracle, smtp, snmp, etc.

## One precise next task
- Add a similar formatter hostile-sweep test file for `mysql` (next module in the group of 3 that lack dedicated formatter hostile-sweep tests). The `mysql` formatters iterate over `findings` and `handshake` (via `_as_dict` guard). Create `tests/test_mysql_formatter_hostile_sweep.py` following the `test_mssql_formatter_hostile_sweep.py` pattern:
  - Test `findings`: non-iterable scalars, hostile lists, well-formed regression
  - Test `handshake`: non-dict values, hostile dicts with non-string/nested values, well-formed regression
  - Cover both Markdown and CSV formatters
- Verify with `pytest tests/test_mysql_formatter_hostile_sweep.py -q`, then full suite, mypy, ruff.
- Repository remains fully green: `pytest -q` -> 7203 passed, 149 skipped, 0 failed; mypy/ruff clean; check_readme 54/54.

(End of file - total 14 lines)
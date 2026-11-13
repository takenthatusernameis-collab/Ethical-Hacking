# Next Task

## Status
Session 138 added a permanent formatter hostile-sweep test file for `memcached` covering both `findings` and `stats` fields (50 new tests). The module's formatters were already guarded inline (no source changes needed), but lacked dedicated hostile-sweep tests matching the pattern used by ftp, ntp, oracle, smtp, snmp.

## One precise next task
- Add a similar formatter hostile-sweep test file for `mongodb` (next module in the group of 6 that lack dedicated formatter hostile-sweep tests). The `mongodb` formatters iterate over `findings` and `buildInfo` (via `_as_dict` guard). Create `tests/test_mongodb_formatter_hostile_sweep.py` following the `test_memcached_formatter_hostile_sweep.py` pattern:
  - Test `findings`: non-iterable scalars, hostile lists, well-formed regression
  - Test `buildInfo`: non-dict values, hostile dicts with non-string/nested values, well-formed regression
  - Cover both Markdown and CSV formatters
- Verify with `pytest tests/test_mongodb_formatter_hostile_sweep.py -q`, then full suite, mypy, ruff.
- Repository remains fully green: `pytest -q` -> 7106 passed, 146 skipped, 0 failed; mypy/ruff clean; check_readme 54/54.

(End of file - total 24 lines)
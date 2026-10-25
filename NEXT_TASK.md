## Status: COMPLETE

Fixed a `BLE001` blind-exception-catch regression in `ethscan/config.py:121`
(introduced by the previous session's commit `3c0ee02`). Restored specific
`except (yaml.YAMLError, RecursionError)` / `except OSError` handling; the
added `yaml is None` guard is now an early return reporting a parse error.

### What was actually verified

- `python -m ruff check ethscan/ tests/` → All checks passed (was: 1 BLE001 error).
- `python -m pytest tests/test_config.py tests/test_config_value_sweep.py -q` → 99 passed, 3 skipped.
- `python -m pytest tests/ -q` → 5204 passed, 51 skipped, 0 warnings.

### What remains unresolved

None. The repository is complete; working tree clean after this commit.

### One precise next task

None — repository complete. If new work arrives, implement the smallest change
solving a demonstrated problem and verify with
`python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.
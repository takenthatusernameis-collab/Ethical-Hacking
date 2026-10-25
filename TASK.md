# TASK

## Status: COMPLETE

Fixed a `BLE001` blind-exception-catch regression introduced by the previous
session's commit `3c0ee02` in `ethscan/config.py:121`. That commit replaced
the specific `except (yaml.YAMLError, RecursionError)` / `except OSError`
clauses with a bare `except Exception`, which broke `ruff check` (the
handoff had incorrectly claimed lint passed). Restored specific exception
handling and moved the added `yaml is None` guard out of the try block as an
early return, so PyYAML absence is reported as a parse error without a blind
catch.

### What was actually verified

- `python -m ruff check ethscan/ tests/` → All checks passed (was: 1 BLE001 error).
- `python -m pytest tests/test_config.py tests/test_config_value_sweep.py -q` → 99 passed, 3 skipped.
- `python -m pytest tests/ -q` → 5204 passed, 51 skipped, 0 warnings.
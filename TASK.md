# TASK

## Status: COMPLETE

Eliminated pre-existing runpy RuntimeWarnings in tests/test_main.py by popping cached modules from sys.modules before runpy.run_module.

### What was actually verified

- `python -m pytest tests/test_main.py -q -W error::RuntimeWarning` → 14 passed.
- `python -m pytest tests/ -q` → 5207 passed, 48 skipped, 0 warnings.
- `python -m ruff check ethscan/ tests/` → All checks passed.

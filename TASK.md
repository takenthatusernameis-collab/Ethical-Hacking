# TASK

## Status: COMPLETE

Fixed input validation in `ethscan/nmap.py`: `_parse_port` now rejects port id `0` (only accepts 1-65535). Ports outside valid range or non-numeric are skipped.

### What was done

- `ethscan/nmap.py:32-52`: changed range check from `0 <= port_id <= 65535` to `1 <= port_id <= 65535`.

### What was actually verified

- `git diff` → single hunk in `ethscan/nmap.py`, no unrelated changes.
- `python -m ruff check ethscan/ tests/` → All checks passed (0 errors).
- `python -m pytest tests/test_nmap.py -q` → 30 passed.
- `python -m pytest tests/ -q` → 5207 passed, 48 skipped, 3 warnings (pre-existing runpy import warnings in test_main.py).
- Manual probes:
  - port `0` → `None` (rejected)
  - port `1` → parsed
  - port `65535` → parsed
  - port `65536` → `None` (rejected)

### What remains unresolved

None.

### Approaches that failed and why

None.

### One precise next task

None.

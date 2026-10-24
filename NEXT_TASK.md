## Status: COMPLETE

Made one bounded fix this session.

### What was done
- `ethscan/nmap.py:32-52`: tightened `_parse_port` to reject port id `0` (valid range now 1-65535). Non-numeric port ids and ports outside range are skipped as before.

### What was actually verified
- `git diff` → single hunk in `ethscan/nmap.py`, no unrelated changes.
- `python -m ruff check ethscan/ tests/` → All checks passed (0 errors).
- `python -m pytest tests/test_nmap.py -q` → 30 passed.
- `python -m pytest tests/ -q` → 5207 passed, 48 skipped, 3 warnings (pre-existing runpy import warnings in test_main.py).
- Manual probes: `portid="0"` → `None`, `portid="1"` parsed, `portid="65535"` parsed, `portid="65536"` → `None`.

### What remains unresolved
None.

### Approaches that failed and why
None.

### One precise next task
None — the repository is complete and all tests pass. If new work arrives, implement the smallest change that solves a demonstrated problem and verify with `pytest tests/` + `ruff check ethscan/ tests/`.

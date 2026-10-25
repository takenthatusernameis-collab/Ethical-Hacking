## Status: COMPLETE

Fixed `check_tcp_connect` in `ethscan/stale.py` to handle exceptions raised by `socket.socket()` itself (e.g. `ConnectionRefusedError`, `socket.timeout` side effects in tests), by moving socket creation inside the try block. All tests pass.

### What was actually verified
- `python -m pytest tests/test_stale.py -q` → 39 passed.
- `python -m pytest tests/ -q` → 5204 passed, 51 skipped, 0 warnings.
- `python -m ruff check ethscan/ tests/` → All checks passed.

### What remains unresolved
None.

### One precise next task
None — repository complete. If new work arrives, implement smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.

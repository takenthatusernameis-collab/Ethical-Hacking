## Status: COMPLETE

### What changed
- Added `TestCheckTCPConnect::test_success_ipv6` to `tests/test_stale.py`, pinning the IPv6 connect branch of `ethscan.stale.check_tcp_connect` (AF_INET6 socket family and 4-tuple `connect(("2001:db8::1", 80, 0, 0))`). No source change was needed; the branch already existed.

### What was actually verified
- `python -m pytest tests/test_stale.py -q` -> 40 passed (was 39).
- `python -m ruff check tests/test_stale.py ethscan/stale.py` -> All checks passed.
- `python -m mypy tests/test_stale.py` -> Success: no issues found in 1 source file.
- `python -m pytest -q` -> 5229 passed, 48 skipped (was 5228 passed).

### What remains unresolved
- None.

### Which approaches failed and why
- None.

### One precise next task
- None.

(End of file - total 19 lines)
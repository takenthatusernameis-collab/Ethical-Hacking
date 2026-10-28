## Status: COMPLETE

### What changed
- Added `TestCheckTCPConnect::test_success_ipv6` to `tests/test_stale.py` (one new test). No source change.

### What was actually verified
- Local: ruff/mypy/pytest all pass (5229 passed, 48 skipped).
- The new test pins the IPv6 branch of `ethscan.stale.check_tcp_connect` introduced in commit 6b17872, which had no dedicated test coverage.

### What remains unresolved
- None.

### Which approaches failed and why
- None.

### One precise next task
- None.

(End of file - total 16 lines)

Verified: 2026-10-28 (ruff/mypy/pytest all passing).
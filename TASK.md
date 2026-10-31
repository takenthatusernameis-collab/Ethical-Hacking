## Status: COMPLETE (this session)

### What changed
- Fixed `_format_network_info` host-range computation in `ethscan/validate.py:131-141` so that `/31` (IPv4) and `/127` (IPv6) networks report the correct usable host as `first_host`/`last_host` instead of the network address.
- The previous two-branch logic (`total > 2` / `else`) returned `network[0]` for two-address networks. The new logic matches the identical helper in `ethscan/cidr.py:84-91` and `ethscan/radix.py:349-356` (three-branch: `total > 2` / `total == 2` / `else`).
- Added `test_format_network_info_ipv4_31` and `test_format_network_info_ipv6_127` to `tests/test_validate.py` to lock in the fix.

### What was actually verified
- `tests/test_validate.py::test_format_network_info_ipv4_31` passes.
- `tests/test_validate.py::test_format_network_info_ipv6_127` passes.
- Full suite: `python -m pytest -q` -> 5437 passed, 50 skipped (was 5435 before this change; +2 tests, no regressions).
- `python -m ruff check ethscan/validate.py tests/test_validate.py`: all checks passed.
- `python -m mypy ethscan/validate.py`: Success, no issues.
- End-to-end CLI verified: `python -m ethscan validate --cidr 192.168.1.0/31,2001:db8::/127,10.0.0.0/8 --output-format markdown` now prints `192.168.1.1 - 192.168.1.1` and `2001:db8::1 - 2001:db8::1` in the Range column.

### What remains unresolved
- None for this change. The `validate` host-range logic is now consistent across `validate.py`, `cidr.py`, and `radix.py`.

### Which approaches failed and why
- No failed approaches. The bug was found by comparing the three near-identical `_format_network_info` implementations; `validate.py` was the outlier.

### One precise next task
- None required. The next agent should start a fresh bounded task rather than resume this line of work.

(End of file - total 24 lines)
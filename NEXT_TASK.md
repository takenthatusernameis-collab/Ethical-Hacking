## Status: COMPLETE

### What changed
- Added `test_format_web_report_markdown_with_error` to `tests/test_web.py` covering the `if data.get("error"):` branch at `ethscan/web.py:317-318`.
- Added `test_run_wifi_drops_ap_without_bssid` to `tests/test_wifi.py` covering the `if not bssid: continue` branch at `ethscan/wifi.py:327-328`.
- Test-only changes; no source modifications.

### What was actually verified
- `pytest tests/test_web.py -q` -> 63 passed.
- `pytest tests/test_wifi.py -q` -> 48 passed.
- Coverage: `ethscan/web.py` 100% (0 miss); `ethscan/wifi.py` 100% (0 miss).
- `python -m ruff check ethscan/web.py tests/test_web.py ethscan/wifi.py tests/test_wifi.py` -> All checks passed.
- Full suite: 5388 passed, 48 skipped, 2 pre-existing failures unchanged (`test_dnssec_inner_dns_import_failure`, `test_dnsbrute_probe_failure_is_reported_not_raised`).

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss; not test-only-feasible).
- `ethscan/cve.py` lines 348-349 unreachable defensive code (`items` is always a list at that point; requires source change to reach).
- `ethscan/ntp.py` line 392: dead defensive code — `if mon_resp.get("error"):` inside the `else` block of `if mon_resp.get("error"):` (line 372). The same dict key cannot be both truthy and falsy; unreachable without a source refactor.
- Pre-existing 2 failures unchanged.

### Which approaches failed and why
- `ethscan/ntp.py:392` was attempted via `test_format_ntp_report_markdown_monlist_error_with_peers` (constructing a monlist response with both `error` set and `peer_count > 0`). Test failed: the branch is logically dead because the outer `if/else` on `mon_resp.get("error")` already consumes the truthy case, so the trailing `if mon_resp.get("error"):` at line 391 is unreachable. Removed the test; not test-only feasible.
- `radix.py`/`cve.py` defensive lines previously deemed not test-only-feasible; `web.py`, `wifi.py` branches confirmed test-only and covered.

### One precise next task
- No remaining test-only 1-miss gaps. Next bounded task: address the 2 pre-existing failures if reproducible in this environment, or defer. If choosing a new feature task, inspect `ethscan/radix.py` (95% coverage, 20 miss) for a small, verifiable improvement that is test-only feasible.

(End of file - total 26 lines)
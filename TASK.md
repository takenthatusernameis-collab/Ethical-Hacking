## Status: COMPLETE

### What changed
- `ethscan/web.py`: 100% coverage (was 99%, 1 miss at 318). Added `test_format_web_report_markdown_with_error` to `tests/test_web.py` covering the `if data.get("error"):` branch in `format_web_report_markdown` (ethscan/web.py:317-318).
- `ethscan/wifi.py`: 100% coverage (was 99%, 1 miss at 328). Added `test_run_wifi_drops_ap_without_bssid` to `tests/test_wifi.py` covering the `if not bssid: continue` branch in `run_wifi` (ethscan/wifi.py:327-328).
- No source changes; test-only.

### What was actually verified
- `pytest tests/test_web.py -q` -> 63 passed.
- `pytest tests/test_wifi.py -q` -> 48 passed.
- Coverage: `ethscan/web.py` 100% (0 miss); `ethscan/wifi.py` 100% (0 miss).
- `python -m ruff check ethscan/web.py tests/test_web.py ethscan/wifi.py tests/test_wifi.py` -> All checks passed.
- Full suite: `python -m pytest -q` -> 5388 passed, 48 skipped, 2 failed (both pre-existing, unchanged: `tests/test_dnssec.py::test_dnssec_inner_dns_import_failure` and `tests/test_protocol_hostile_sweep.py::test_dnsbrute_probe_failure_is_reported_not_raised`).
- Total coverage: 99% (87 miss).

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss: defensive/fallback branches at 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324; previously deemed not test-only-feasible).
- `ethscan/cve.py` lines 348-349 unreachable in `run_cve()` without a source change.
- `ethscan/ntp.py` line 392: dead defensive code — `if mon_resp.get("error"):` inside the `else` block of `if mon_resp.get("error"):` (line 372). The same dict key cannot be both truthy and falsy; unreachable without a source refactor. Attempted via `test_format_ntp_report_markdown_monlist_error_with_peers`; test failed and was removed.
- Pre-existing 2 failures above (unrelated to coverage work).

### Which approaches failed and why
- `ethscan/ntp.py:392` attempted via a test constructing a monlist response with both `error` set and `peer_count > 0`. Failed: the branch is logically dead because the outer `if/else` on `mon_resp.get("error")` already consumes the truthy case, so the trailing `if mon_resp.get("error"):` at line 391 is unreachable. Removed the test; not test-only feasible.
- `radix.py`/`cve.py` defensive lines previously deemed not test-only-feasible; `web.py`, `wifi.py` branches confirmed test-only and covered.

### One precise next task
- No remaining test-only 1-miss gaps. Next bounded task: address the 2 pre-existing failures if reproducible in this environment, or defer. If choosing a new feature task, inspect `ethscan/radix.py` (95% coverage, 20 miss) for a small, verifiable improvement that is test-only feasible.

(End of file - total 28 lines)
## Status: COMPLETE

### What changed
- `ethscan/urlcheck.py`: 100% coverage (was 97%, 8 miss at 141, 148, 167, 246, 335, 343, 354, 378). Added 8 tests to `tests/test_urlcheck.py` covering defensive formatter branches in both the Markdown and CSV renderers: non-dict `summary` (141, 335), non-list/tuple `web_checks_run` (148, 343), string `web.error` (167, 354), non-list/tuple fuzz `findings` (246), non-dict SSL `cert` (378).
- `ethscan/mac.py`: 100% coverage (was 99%, 1 miss at 303). Added 1 test to `tests/test_mac.py` covering the non-dict `mac_data` fallback in `format_mac_report_csv` (303).
- No source changes; test-only.

### What was actually verified
- `pytest tests/test_urlcheck.py -q` -> 31 passed.
- `pytest tests/test_mac.py -q` -> 61 passed.
- `coverage report --include="ethscan/urlcheck.py" -m` -> 100% (0 miss).
- `coverage report --include="ethscan/mac.py" -m` (full suite) -> 100% (0 miss).
- `ruff check ethscan/urlcheck.py tests/test_urlcheck.py` -> All checks passed.
- `ruff check ethscan/mac.py tests/test_mac.py` -> All checks passed.
- Full suite: `python -m pytest -q` -> 5385 passed, 48 skipped, 2 failed (both pre-existing, unchanged: `tests/test_dnssec.py::test_dnssec_inner_dns_import_failure` and `tests/test_protocol_hostile_sweep.py::test_dnsbrute_probe_failure_is_reported_not_raised`).
- Total coverage: 99% (87 miss).

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss: defensive/fallback branches at 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324; previously deemed not test-only-feasible).
- `ethscan/cve.py` lines 348-349 unreachable in `run_cve()` without a source change.
- Remaining 1-miss test-only gaps: `ethscan/web.py:318`, `ethscan/ntp.py:392`, `ethscan/wifi.py:328` (wifi depends on live Wi-Fi tooling, harder to cover test-only).
- Pre-existing 2 failures above (unrelated to coverage work).

### Which approaches failed and why
- None new in this session. `radix.py`/`cve.py` defensive lines previously deemed not test-only-feasible; `s3.py`, `ping.py`, `urlcheck.py`, `mac.py` branches were confirmed test-only and are now covered.

### One precise next task
- Cover the smallest remaining test-only gap: `ethscan/web.py` line 318 (1 miss), the `if data.get("error"):` branch in `format_web_report_markdown` (ethscan/web.py:317-318). It is test-only: construct a data dict with `target`, `host`, `port`, `secure` plus a truthy `"error"` string, call `format_web_report_markdown(data)`, and assert `"**Error:** <error>"` appears in the output. Add the test to `tests/test_web.py`, then verify with `coverage report --include="ethscan/web.py" -m` (expect 100%) and `ruff check ethscan/web.py tests/test_web.py`. Defer `radix.py`/`cve.py` (not test-only-feasible without source changes).

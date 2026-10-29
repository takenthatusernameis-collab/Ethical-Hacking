## Status: COMPLETE

### What changed
- `ethscan/urlcheck.py`: 100% coverage (was 97%, 8 miss at 141, 148, 167, 246, 335, 343, 354, 378). Added 8 tests to `tests/test_urlcheck.py`.
- `ethscan/mac.py`: 100% coverage (was 99%, 1 miss at 303). Added 1 test to `tests/test_mac.py`.
- Test-only changes; no source modifications.

### What was actually verified
- `pytest tests/test_urlcheck.py -q` -> 31 passed.
- `pytest tests/test_mac.py -q` -> 61 passed.
- Coverage: `ethscan/urlcheck.py` 100% (0 miss); `ethscan/mac.py` 100% (0 miss).
- `ruff check ethscan/urlcheck.py tests/test_urlcheck.py` -> passed.
- `ruff check ethscan/mac.py tests/test_mac.py` -> passed.
- Full suite: 5385 passed, 48 skipped, 2 pre-existing failures unchanged (`test_dnssec_inner_dns_import_failure`, `test_dnsbrute_probe_failure_is_reported_not_raised`).

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss; not test-only-feasible).
- `ethscan/cve.py` lines 348-349 unreachable without source change.
- Remaining 1-miss test-only gaps: `ethscan/web.py:318`, `ethscan/ntp.py:392`, `ethscan/wifi.py:328`.
- Pre-existing 2 failures unchanged.

### Which approaches failed and why
- None new. `radix.py`/`cve.py` defensive lines previously deemed not test-only-feasible; `s3.py`, `ping.py`, `urlcheck.py`, `mac.py` branches confirmed test-only and covered.

### One precise next task
- Cover `ethscan/web.py` line 318 (1 miss): the `if data.get("error"):` branch in `format_web_report_markdown` (ethscan/web.py:317-318). Test-only: construct a data dict with `target`, `host`, `port`, `secure` plus a truthy `"error"` string, call `format_web_report_markdown(data)`, assert `"**Error:** <error>"` appears. Add test to `tests/test_web.py`; verify `coverage report --include="ethscan/web.py" -m` -> 100% and `ruff check ethscan/web.py tests/test_web.py`. Defer `radix.py`/`cve.py`.

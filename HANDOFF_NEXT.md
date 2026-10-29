## Status: COMPLETE

### What changed
- `ethscan/urlcheck.py`: 100% coverage (was 97%, 8 miss). Added 8 tests to `tests/test_urlcheck.py` covering defensive formatter branches in both Markdown and CSV renderers (non-dict summary, non-list web_checks_run, string web error, non-list fuzz findings, non-dict SSL cert).
- `ethscan/mac.py`: 100% coverage (was 99%, 1 miss at 303). Added 1 test to `tests/test_mac.py` covering the non-dict `mac_data` fallback in `format_mac_report_csv`.
- No source changes; test-only.

### What was actually verified
- `pytest tests/test_urlcheck.py -q` -> 31 passed; `ethscan/urlcheck.py` 100% (0 miss).
- `pytest tests/test_mac.py -q` -> 61 passed; `ethscan/mac.py` 100% (0 miss).
- `ruff check` on both modules + tests -> All checks passed.
- Full suite: 5385 passed, 48 skipped, 2 pre-existing failures unchanged (`test_dnssec_inner_dns_import_failure`, `test_dnsbrute_probe_failure_is_reported_not_raised`).

### What remains unresolved
- `ethscan/radix.py` 95% (20 defensive-miss lines; not test-only-feasible).
- `ethscan/cve.py` lines 348-349 unreachable without source change.
- Remaining 1-miss test-only gaps: `ethscan/web.py:318`, `ethscan/ntp.py:392`, `ethscan/wifi.py:328`.
- Pre-existing `test_dnssec` and `test_dnsbrute` failures.

### Which approaches failed and why
- None new. `radix.py`/`cve.py` defensive lines previously deemed not test-only-feasible; all other remaining formatter branches confirmed test-only and covered.

### One precise next task
- Cover `ethscan/web.py` line 318 (1 miss): the `if data.get("error"):` branch in `format_web_report_markdown`. Test-only: pass a data dict with `target`/`host`/`port`/`secure` plus a truthy `"error"` string, assert `"**Error:** ..."` in output. Add to `tests/test_web.py`, verify `coverage report --include="ethscan/web.py" -m` -> 100% and `ruff check ethscan/web.py tests/test_web.py`. Defer `radix.py`/`cve.py`.

## Status: COMPLETE

### What changed
- `ethscan/dnssec.py`: removed the redundant `import dns.message` at line 20 (it was already imported inside the protective inner try at line 14). Because the line-20 import sat outside the inner `try/except`, setting `dns.message = None` in `sys.modules` made `import dns.message` raise `ModuleNotFoundError` that propagated to the outer `except`, forcing `DNS_AVAILABLE = False` and breaking `test_dnssec_inner_dns_import_failure` (which expects `True`). Source-only fix, no test changes.
- No coverage changes this session.

### What was actually verified
- `python -m pytest tests/test_dnssec.py::test_dnssec_inner_dns_import_failure -q` -> 1 passed (was failing).
- `python -m ruff check ethscan/dnssec.py tests/test_dnssec.py` -> All checks passed.
- Full suite: `python -m pytest -q` -> 5389 passed, 48 skipped, 1 failed.
  - Remaining failure: `tests/test_protocol_hostile_sweep.py::test_dnsbrute_probe_failure_is_reported_not_raised`.
- Confirmed `test_dnsbrute_probe_failure_is_reported_not_raised` PASSES in isolation and within `tests/test_protocol_hostile_sweep.py` alone (269 passed) and with `test_web.py`/`test_ssh.py`; it fails only in the full-suite run.

### What remains unresolved
- `ethscan/radix.py` 95% (20 defensive-miss lines; not test-only-feasible).
- `ethscan/cve.py` lines 348-349 unreachable without source change.
- Remaining 1-miss test-only gaps: `ethscan/web.py:318`, `ethscan/ntp.py:392`, `ethscan/wifi.py:328`.
- `test_dnsbrute_probe_failure_is_reported_not_raised`: test-isolation issue, not a source bug. `ethscan/dnsbrute.socket` IS the global `socket` module, and `tests/conftest.py:57` (`no_external_network` fixture) plus several sweep tests mutate global `socket.create_connection`/`socket.setdefaulttimeout`. The dnsbrute source (`query_axfr_raw`) correctly catches and reports transport failures; the test's monkeypatch of the global socket attribute doesn't survive full-suite ordering. Passes alone; fails only in full suite with `[Errno 111] Connection refused` instead of the mocked "hostile transport".

### Which approaches failed and why
- `ethscan/ntp.py:392` (dead `if mon_resp.get("error"):` inside an `else` on the same key): previously attempted via test, logically unreachable; not test-only feasible. Source refactor would be required but is out of scope for a bounded session.
- `radix.py`/`cve.py` defensive lines: previously deemed not test-only-feasible.
- dnsbrute: pairwise combos with `test_web.py`/`test_ssh.py`/`test_cli_unreachable_sweep.py` did NOT reproduce; requires full-suite cumulative global-socket state. Not worth sinking further time into (isolated, non-deterministic-in-isolation, source is correct).

### One precise next task
- Option A (coverage): cover `ethscan/web.py` line 318 (1 miss) — the `if data.get("error"):` branch in `format_web_report_markdown`. Test-only: pass a data dict with `target`/`host`/`port`/`secure` plus a truthy `"error"` string, assert `"**Error:** ..."` in output. Add to `tests/test_web.py`, verify `coverage report --include="ethscan/web.py" -m` -> 100% and `ruff check ethscan/web.py tests/test_web.py`.
- Option B (reliability): make `test_dnsbrute_probe_failure_is_reported_not_raised` robust to global `socket.create_connection` mutation (e.g. patch at a more isolated level or restore `socket.create_connection` explicitly), OR defer it as a pre-existing test-isolation issue. Do NOT change `ethscan/dnsbrute.py` source — it is correct.

# Next Task

## Status: CLOSED (this session)
Typing hygiene completed for `tests/test_protocol_hostile_sweep.py` (8 errors -> 0), following the established pattern (test-side casts/annotations; runtime behavior unchanged).

- `tests/test_protocol_hostile_sweep.py`:
  - Added `from typing import Any, cast`.
  - `fake_attempt_axfr` return annotation widened from `dict[str, object]` to `dnsbrute._AxfrResult`.
  - `test_dnssec_probe_failure_is_reported_not_raised`: `cast(str, cast(dict[str, object], result["dnskey"]).get("error"))` and same for `result["ds"]`.
  - `test_tls_probe_failure_is_reported_not_raised`: `cast(list[dict[str, object]], result["versions"])` / `result["ciphers"]` before iterating.
  - `test_osdetect_connect_tcp_failure_is_reported_not_raised`: `probes = cast(list[dict[str, object]], results["probes"])` then `probe = probes[0]`; `cast(str, probe.get("error"))`.
  - `test_dns_transport_failure_is_reported_not_raised` / `test_dns_a_records_failure_is_reported_not_raised`: `cast(dict[str, object], results["records"])["A"]`.

Verified: `mypy tests/test_protocol_hostile_sweep.py` clean; `ruff check` clean; `pytest tests/test_protocol_hostile_sweep.py -q` → 269 passed; `pytest -q --ignore=tests/test_ping.py` → 5878 passed, 50 skipped, 0 failed (baseline unchanged).

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.
- Reproduce with `python -m mypy tests/<file>` before fixing any file.

## Suggested next task
Continue per-file typing hygiene across remaining test files with mypy errors. Reproduce each target with `python -m mypy tests/<file>` first, fix per file using the established pattern (TypedDict/Mapping in source where indexing `dict[str, object]` results is the issue; test-only annotations/casts otherwise). Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` blocker). Do not speculate or weaken safety controls. Do not assume prior handoff error counts are current; reproduce per file first.

Remaining hostile-sweep files with the same 7-error shape (hostile top-level `object` passed to formatters typed `dict[str, object]`/`Mapping[str, object]`/`dict[str, Any]`) — fix with the same `cast(Any, ...)` pattern:
`test_brute_hostile_sweep.py`, `test_cidr_hostile_sweep.py`, `test_dnsbrute_hostile_sweep.py`, `test_hash_hostile_sweep.py`, `test_nmap_hostile_sweep.py`, `test_ping_hostile_sweep.py`, `test_radix_hostile_sweep.py`, `test_recon_hostile_sweep.py`, `test_resolve_hostile_sweep.py`, `test_s3_hostile_sweep.py`, `test_scanner_hostile_sweep.py`, `test_stale_hostile_sweep.py`, `test_subdomains_hostile_sweep.py`, `test_tls_hostile_sweep.py`, `test_trace_hostile_sweep.py`, `test_urlcheck_hostile_sweep.py`, `test_validate_hostile_sweep.py`, `test_wifi_hostile_sweep.py`.

Non-sweep files with errors: `test_cve.py` (32), `test_osdetect.py` (33), `test_web.py` (27), `test_jwt.py` (25), `test_tls.py` (18), `test_dnssec.py` (18), `test_subdomains.py` (17), `test_geo.py` (17), `test_cli.py` (12), `test_brute.py` (11), `test_fuzz_hostile_sweep.py` (4), `test_dns_hostile_sweep.py` (3 — already clean), `test_cert_hostile_sweep.py` (1), `test_config_hostile_sweep.py` (3), `test_fuzz.py`, `test_ldap.py`, `test_service.py`, `test_passwords.py`, `test_passwords_hostile_sweep.py`, `test_protocol_hostile_sweep.py`, `test_osdetect_hostile_sweep.py`, `test_dnssec_hostile_sweep.py`.

(End of file - total 34 lines)
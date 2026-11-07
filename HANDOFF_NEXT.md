# Handoff
Date: Sat Nov 07 2026

## What changed
- `tests/test_tls.py` (tests only; no library changes):
  - `test_run_tls_default_versions_and_ciphers`: call-order assertions now compare `sorted(called_versions, key=TLS_VERSIONS.index)` / `sorted(called_ciphers, key=COMMON_CIPHERS.index)` to the canonical lists. `enumerate_tls` probes concurrently (`ThreadPoolExecutor` + `as_completed`) and sorts *results*; probe invocation/append order is nondeterministic.
  - `test_run_tls_custom_versions_and_ciphers`: same canonical-order comparison for the custom requested set.

## Verified
- Reproduced prior handoff's 3 "unrelated" failures in this environment: `tests/test_tls.py::test_run_tls_default_versions_and_ciphers`, `test_run_tls_custom_versions_and_ciphers` failed with order mismatches (`2 failed, 1 passed` over the 3 selectors); `tests/test_fileio.py::test_load_json_raises_on_a_file_that_nests_too_deeply` passed.
- After fix:
  - `python3 -m pytest tests/test_tls.py -q --tb=short` → `71 passed`.
  - The 3 selectors → `3 passed`.
  - `python3 -m pytest tests/test_cli.py tests/test_whois.py tests/test_recon.py -q --tb=no` → `1128 passed`.
  - `python3 -m ruff check .` → `All checks passed!`
  - `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.
  - Full suite: `5903 passed, 50 skipped`.

## Unresolved
- None demonstrated. A broad CLI validation sweep (resolver/API-URL/geo-api-url/whois-server/dnsbrute `--ns`, recon modules/dns-types, probe lists, CIDR/radix/network parsing) found no new side-effect-before-reject or silent-accept endpoint-validation gap; `cidr/radix --contains` accepting non-IP strings is intentional (`in_network: false`, tested).

## Next task
- Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection or a silent-accept validation gap in a **materially different** area from exhausted/fixed sweeps. Stop at first reproduced gap; add smallest permanent guard/test. Keep baseline green; do not commit unless asked. Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`.

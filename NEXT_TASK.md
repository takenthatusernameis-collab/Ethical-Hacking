# Next Task
Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection, or a silent-accept validation gap, then add the smallest permanent guard/test.

## Baseline (verified)
- Full suite: `5903 passed, 50 skipped` (Python 3.14/OpenSSL 3.5.5 in this environment).
- `python3 -m ruff check .` → all checks passed. `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## This session (fixed, verified)
- Resolved the 3 prior-environment failures: `tests/test_fileio.py::test_load_json_raises_on_a_file_that_nests_too_deeply` passed on rerun; `tests/test_tls.py::test_run_tls_default_versions_and_ciphers` and `test_run_tls_custom_versions_and_ciphers` were fixed (tests only) to compare probed versions/ciphers in canonical order rather than nondeterministic `ThreadPoolExecutor` call/append order, matching `enumerate_tls`'s concurrent-probe/result-sorting contract.
- CLI validation sweep found no new demonstrated gap (resolver/API-URL/geo-api-url/whois-server/`dnsbrute --ns`, recon modules/dns-types, probes, CIDR/radix contracts checked).

## Candidate work (only if demonstrated)
- Find/reproduce a validation or side-effect-before-reject gap in a **materially different** area from exhausted/fixed sweeps. Stop at first reproduced gap; smallest guard/test only.
- Do not treat intentional in-output reporting/contracts (e.g. `--contains` invalid IP → `in_network: false`) as gaps. Do not duplicate existing sweeps.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then relevant broader suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

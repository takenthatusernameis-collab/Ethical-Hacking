# Next Task
Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection, or a silent-accept validation gap, then add the smallest permanent guard/test.

## Baseline (verified)
- Scoped (this session): `1127 passed` (CLI/whois/recon), `44 passed` (whois), `22 passed` (whois/API-URL CLI validation selectors). `python3 -m ruff check .` → clean. `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.
- Full suite (this environment): `5899 passed, 3 failed, 50 skipped`. 3 failures unrelated to recent CLI validation changes (see `HANDOFF_NEXT.md`): `test_fileio.py::test_load_json_raises_on_a_file_that_nests_too_deeply`, `test_tls.py::test_run_tls_default_versions_and_ciphers`, `test_tls.py::test_run_tls_custom_versions_and_ciphers`.

## This session (fixed, verified)
- `whois --server` and `recon --whois-server` now validated at CLI (hostname/IP; rejects schemes, whitespace/control garbage, invalid labels, empty) with exit 2 and no runner side effects — matching resolver/API-URL validation patterns. Tests: `test_whois_server_rejected_at_cli`, `test_recon_whois_server_rejected_at_cli`; unreachable-whois contract preserved with mocked socket.

## Candidate work (only if demonstrated)
- Find/reproduce a validation or side-effect-before-reject gap in a **materially different** area (CLI edge sweep, `--probes`, `recon --modules`/`--dns-types`, API-URL options, and `whois`/`recon` WHOIS-server validation now fixed). Stop at first reproduced gap; smallest guard/test only.
- Optionally reproduce/fix one of the 3 unrelated full-suite failures only if treated as its own demonstrated gap with independent evidence.
- Do not duplicate existing sweeps or treat intentional in-output reporting/contracts as gaps.

## Constraints
- Preserve baseline for changed areas; smallest reversible change.
- Verify: targeted pytest, then relevant broader suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

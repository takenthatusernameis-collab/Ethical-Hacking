# Task
Date: Fri Nov 06 2026

## Current state
- Baseline (scoped, verified this session after changes): CLI/whois/recon tests, ruff, mypy clean.
- Full suite (this environment): `5899 passed, 3 failed, 50 skipped` — the 3 failures are **unrelated** to this session's CLI-only changes (only `ethscan/cli.py`, `tests/test_cli.py` modified) and reproduce independently in this environment: `tests/test_fileio.py::test_load_json_raises_on_a_file_that_nests_too_deeply` (does not raise), `tests/test_tls.py::test_run_tls_default_versions_and_ciphers`/`test_run_tls_custom_versions_and_ciphers` (order mismatch). Prior handoff recorded `5900 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## This session
- **Demonstrated gap (reproduced):** CLI accepted malformed WHOIS server hostnames and reached side effects / recorded bad values in output (exit 0), unlike DNS resolver options and API-URL options:
  - `whois --server "not a valid host!!!"` / `"http://evil.com"` / `"host:99999"` / empty → exit 0, `run_whois` invoked / bad server in JSON, connection attempted.
  - `recon --whois-server "!!!bad"` (with `--modules whois`) → exit 0, `run_recon` invoked / bad server in output.
- **Fix (smallest reversible, CLI-only):** Added `_validate_whois_server` in `ethscan/cli.py` (accepts valid hostname labels or IP address; rejects schemes, whitespace/control chars, invalid labels/ports-as-host-garbage, empty) → raises `click.UsageError` (exit 2). Applied:
  - `whois --server` validated before `run_whois`.
  - `recon --whois-server` validated (with other resolver/API validations) before `run_recon`.
  Libraries unchanged.
- **Tests:** `tests/test_cli.py::test_whois_server_rejected_at_cli` (malformed values → exit 2, `--server` in error, runner not called). `tests/test_cli.py::test_recon_whois_server_rejected_at_cli` (exit 2, `--whois-server`, runner not called). Updated `test_an_unreachable_whois_server_is_reported_in_the_output` to use a syntactically valid unreachable server with socket mocked (separates validation from network reachability, consistent with unreachable-sweep intent).

## Verified (evidence)
- Repro (pre-fix): `whois --server "not a valid host!!!"` / `recon --whois-server "!!!bad"` → exit 0, bad server in output. After fix: both → exit 2 with `Invalid value for '--server'/'--whois-server': ... is not a valid WHOIS server hostname or IP address.` and runners not called.
- `python3 -m pytest tests/test_whois.py -q --tb=no` → `44 passed`.
- `python3 -m pytest tests/test_cli.py -q -k "whois or recon_whois or api_url_rejected or geo_api_url_rejected or cert_unknown_api_url_rejected"` → `22 passed`.
- `python3 -m pytest tests/test_cli_unreachable_sweep.py -q -k whois --tb=no` → `1 passed`.
- `python3 -m pytest tests/test_cli.py tests/test_whois.py tests/test_recon.py -q --tb=no` → `1127 passed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`
- Full suite: `5899 passed, 3 failed, 50 skipped` (3 failures unrelated to this change; see Current state).

## Blockers
- None demonstrated for this fix. The 3 unrelated full-suite failures in this environment were not introduced by this session and were not investigated/fixed (out of demonstrated scope for the WHOIS-server validation gap).

## Next task
- Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection or a silent-accept validation gap in an area **different** from exhausted sweeps and fixed `--probes`/`recon --modules`/`recon --dns-types`/all API-URL options/`whois --server`/`recon --whois-server`. Materially different scan surface only; stop at first reproduced gap; add smallest permanent guard/test. If addressing the 3 unrelated full-suite failures, reproduce each independently and treat as a separate demonstrated gap (do not conflate with validation work). Keep baseline green for changed areas; do not commit unless asked. Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`.

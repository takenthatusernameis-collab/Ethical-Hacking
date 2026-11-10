# Handoff
Date: Tue Nov 10 2026 (session 40)

## This session
- The prior agent's `mongodb` empty-target normalization was already complete (commit 27a35e0): `python -m ethscan mongodb --target ""|"   "|"https://"` all exit 2 with `Error: Invalid value for '--target': Could not parse host from target ...`. Verified directly; did not redo.
- Selected and completed the next bounded module: `mssql`.
- Reproduced before fix: `python -m ethscan mssql --target ""|"   "|"https://"` all exited 0 with JSON `{"host": null, ..., "error": "Could not parse host from target ..."}` instead of a CLI usage error.
- Fixed `ethscan/mssql.py:run_mssql` (`ethscan/mssql.py:525`): the `except ValueError` around `_normalize_target(target)` now re-raises `TargetSpecError` instead of swallowing it into an in-band result dict. `_normalize_target` already raised `TargetSpecError` for an empty host; `run_mssql` was the only piece swallowing it. `TargetSpecError` propagates through the CLI `mssql` command to `_TargetGroup.invoke` (ethscan/cli.py:401) → `Error: Invalid value for '--target': Could not parse host from target ...` (exit 2).
- `tests/test_mssql.py`:
  - Added module-level `import pytest` and `from ethscan.target import TargetSpecError`.
  - `test_normalize_target` now asserts `pytest.raises(TargetSpecError, match="Could not parse host from target")` for `""` (was: bare `try/except ValueError`).
  - Added `test_normalize_target_rejects_empty_target` for `""`, `"   "`, `"https://"`.
  - `test_run_mssql_invalid_target` now asserts `run_mssql("")` raises `TargetSpecError` for `""`, `"   "`, `"https://"` (was: asserted an in-band result dict).
- `tests/test_cli.py`:
  - Added `test_mssql_invalid_target_is_usage_error` (`""`, `"   "`, `"https://"` → exit 2 + usage-error message).
  - Moved `mssql` out of `TARGET_PROBE_FAILURE_COMMANDS` and `BARE_PORT_PROBE_FAILURE_COMMANDS` into `TARGET_USAGE_ERROR_COMMANDS` and `BARE_PORT_COMMANDS`.
- `tests/test_target.py`: removed `mssql` from `PROBE_FAILURE_MODULES` (`TARGET_MODULES` tests still cover mssql and pass unchanged).

## Verification
- Repro after fix: `mssql --target ""|"   "|"https://"` → exit 2, `Error: Invalid value for '--target': Could not parse host from target ...`; `mssql --target example.com` → exit 0 (probe runs; valid-target behavior unchanged).
- `python -m mypy ethscan/mssql.py tests/test_mssql.py tests/test_cli.py tests/test_target.py` → Success: no issues found in 4 source files.
- `python -m ruff check ethscan/mssql.py tests/test_mssql.py tests/test_cli.py tests/test_target.py` → All checks passed.
- `python -m pytest tests/test_mssql.py tests/test_mssql_hostile_sweep.py tests/test_cli.py -q -k "mssql or mongo"` → 109 passed.
- `python -m pytest -q` (full suite) → 5957 passed, 50 skipped, 0 failed (baseline was 5958; net -1 because `test_run_mssql_invalid_target` was rewritten from an in-band-result assertion into a `pytest.raises` and `test_normalize_target`'s bare `try/except` was replaced by `pytest.raises`, so the old assertions are gone and 2 new parametrized checks were added).

## Blockers
- None.

## Approaches already tried / ruled out
- None failed; single small, evidence-based fix following the established `TargetSpecError` pattern (same as ping/osdetect/vuln/ssh/brute/cve/tls/ssl/s3/fuzz/web/cert/mysql/mongodb).

## Next task
- Remaining modules with the same `except ValueError` swallowing pattern are `oracle` and `postgresql` (they are in `PROBE_FAILURE_MODULES`/`TARGET_PROBE_FAILURE_COMMANDS`/`BARE_PORT_PROBE_FAILURE_COMMANDS` and report empty targets in-band by design — their contract is to treat an unusable target as a failed probe, exit 0). Do not change them unless a task explicitly asks to. If a new bounded task is needed, pick one remaining test file with mypy errors and reproduce per file first (candidates: `test_dnsbrute.py` (47), `test_hash.py` (46), `test_urlcheck.py` (39), `test_whois.py` (37)).
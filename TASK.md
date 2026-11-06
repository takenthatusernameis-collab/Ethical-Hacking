# Task
Date: Fri Nov 06 2026

## Current state
- Baseline: `5900 passed, 50 skipped, 0 failed` (verified this session after changes).
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## This session
- **Demonstrated gaps (reproduced):** CLI options accepted invalid `http/https` URLs (no exit-2 rejection) and allowed command/library paths to proceed with side effects / bad-URL handling, unlike `geo --api-url` and `cert --api-url`:
  - `recon --geo-api-url "not a url"` (with `--modules geo`) → exit 0, `run_recon` invoked.
  - `cve --api-url "not a url"` → exit 0, `run_cve` invoked / invalid URL recorded in output.
  - `mac --api-url "not a url"` → exit 0, `run_mac` invoked (fetch attempted, surfaced as fetch error).
- **Fix (smallest reversible, CLI-only):** In `ethscan/cli.py` validate with existing `_validate_api_url` before side effects:
  - `recon`: `geo_api_url = _validate_api_url(geo_api_url, "--geo-api-url")`
  - `cve`: `api_url = _validate_api_url(api_url, "--api-url")` (validated before service/ports resolution and `run_cve`)
  - `mac`: `api_url = _validate_api_url(api_url, "--api-url")` before `run_mac`
  Libraries unchanged.
- **Tests:** Added `tests/test_cli.py::test_recon_geo_api_url_rejected`, `::test_cve_api_url_rejected`, `::test_mac_api_url_rejected` (exit 2, correct option name in error, underlying runner not called).

## Verified (evidence)
- Repro (pre-fix behavior via direct invoke baseline check): each command accepted `"not a url"` (exit 0) and invoked runners / reached side effects. After fix (CLI): all three → exit 2 with `Invalid value for ... is not a valid http/https URL.` and runner not called.
- `python3 -m pytest tests/test_cli.py -q -k "geo_api_url_rejected or recon_geo_api_url_rejected or cve_api_url_rejected or mac_api_url_rejected or cert_unknown_api_url_rejected or geo_unknown_api_url_rejected"` → `5 passed`.
- `python3 -m pytest tests/test_cli.py -q -k "cert or cve or mac or recon and geo"` → `70 passed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`
- `python3 -m pytest -q --tb=no` → `5900 passed, 50 skipped, 0 failed`

## Blockers
- None.

## Next task
- Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection or a silent-accept validation gap in an area **different** from the exhausted CLI edge sweep and fixed `--probes`/`recon --modules`/`recon --dns-types`/`cert --api-url`/`recon --geo-api-url`/`cve --api-url`/`mac --api-url` validation. Materially different scan surface only; stop at first reproduced gap; add smallest permanent guard/test. Keep baseline green; do not commit unless asked. Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`.

(End of file)

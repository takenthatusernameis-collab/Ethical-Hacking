# Handoff
Date: Fri Nov 06 2026

## What changed
- `ethscan/cli.py`: the `cert` command now validates `--api-url` with `_validate_api_url(api_url, "--api-url")` before invoking `run_cert`, matching the `geo` command's existing pattern. Invalid values are rejected as a `click.UsageError` (exit 2) before any network side effects.
- `tests/test_cli.py`: added `test_cert_unknown_api_url_rejected` (exit 2, error text, `run_cert` not called).

## Verified
- Repro before fix: `cert --target example.com --api-url "not a url"` → exit 0, proceeded to network, no CLI rejection.
- After fix: `cert --api-url "not a url"` → exit 2, `Invalid value for '--api-url': ...`, `run_cert` not called.
- `python3 -m pytest tests/test_cli.py -q -k "cert"` → `17 passed`.
- `python3 -m pytest -q --tb=no` → `5897 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → clean.
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Unresolved
- None demonstrated.

## Next task
- If a new demonstrated gap appears (CLI option/callback reaching side effects before clean rejection, or silent-accept validation gap outside exhausted areas: `--probes`, `recon --modules`, `recon --dns-types`, `cert --api-url`, CLI edge sweep), fix smallest guard/test. Otherwise stop; no blind sweeps.

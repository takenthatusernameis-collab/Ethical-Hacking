# Task
Date: Sat Nov 07 2026

## Current state
- Baseline at session start: green (per HANDOFF_NEXT.md: ruff/mypy clean, 5909 passed, 50 skipped). Focused stale checks pass after this change.
- `python3 -m ruff check ethscan/cli.py tests/test_cli.py`: all checks passed.
- `python3 -m mypy ethscan/cli.py`: Success, no issues.

## This session
- **Demonstrated gap (reproduced):** `stale` CLI accepts `--target` (repeatable) plus `--file`. With an existing domains file and an unusable `--target` (e.g. `http://]bad[` / `http://[::1`), the CLI read the domains file via `load_domains_from_file()` before the bad target was normalized/rejected inside `run_stale`. The target was ultimately reported as a usage error (exit 2) by the `TargetSpecError` group handler, but file I/O occurred first (side effect) — same pattern previously fixed for fuzz/subdomains/subtake/dnsbrute/s3/recon/brute/osdetect/vuln/cve.
- **Fix (smallest reversible):** In `ethscan.cli.stale()`, validate each explicit `--target` with `_validate_enum_target()` before reading `--file`. Click still validates `--file` path existence/readability; content is not read when an explicit target is unusable. File-sourced targets remain normalized/handled by `run_stale` as before.
- **Tests:** Added `test_stale_rejects_bad_target_before_reading_file` in `tests/test_cli.py` (bad explicit target + existing file → target usage error, exit 2; `run_stale` not invoked).

## Verified
- `python3 -m pytest tests/test_cli.py -q -k "stale_rejects_bad_target_before_reading_file or stale_help or stale_offline"` → 5 passed.
- `python3 -m pytest tests/test_stale.py tests/test_cli.py -q -k stale` → 66 passed.
- `python3 -m ruff check ethscan/cli.py tests/test_cli.py` → all checks passed.
- `python3 -m mypy ethscan/cli.py` → Success.

## Blockers
- None demonstrated.

## Next task
- Look for other commands that read user-supplied files (side effects) after accepting target-like inputs but before validating those inputs in a way that prevents file reads — only where a concrete, reproducible gap exists (file read/error masking target error, or unnecessary side effect). Start by auditing `report`/`brute` credential-file flows vs target validation ordering with a quick reproduction; `report` already validates target before `_require_utf8`/reading audit file (verified in code), `brute` validates target before reading user/pass files (verified), so avoid repeating solved patterns. If no gap reproduces, record evidence and stop.

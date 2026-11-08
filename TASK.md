# Task
Date: Sun Nov 08 2026

## Current state
- Baseline (verified this session, dnspython 2.9.2 installed): `python -m pytest -q` → 5932 passed, 50 skipped, 0 failed. 5982 tests collected. `ethscan` 0.1.0; pytest 9.2.0, ruff 0.17.4, mypy 2.4.1.
- All 58 CLI commands registered/help OK; ruff clean; mypy 59 source files OK.
- No TODO/FIXME/XXX/HACK in `*.py`.

## This session
- Inspected repo state (no prior open assignment; git clean before changes).
- Verified baseline green: `python -m pytest -q` → 5932 passed, 50 skipped (all skips intentional: dnspython-excluded modules, commands without file/string options). `python -m ruff check .` → pass. `python -m mypy ethscan/` → pass. All 58 CLI `--help` invocations return 0.
- Confirmed PBKDF2 behavior end-to-end: `hash --password ... --salt ... --iterations N` generates a PBKDF2-HMAC digest; `hash --check` verifies it (MATCH); peppered PBKDF2 (`--salt --pepper --iterations`) generates and verifies correctly; `--iterations` without `--salt` is rejected (exit 2).
- Identified a genuine bounded gap: `run_check` with pepper + iterations (peppered PBKDF2 check) was untested at the `run_check` level (only the compute layer `test_compute_password_hash_iterations_with_pepper` and generation `test_run_hash_iterations_with_pepper` existed).
- Implemented bounded test addition (evidence-based): added `test_run_check_iterations_with_pepper_match` and `test_run_check_iterations_with_pepper_mismatch` to `tests/test_hash.py`, plus a `_peppered_pbkdf2_digest` helper.
- Re-verified after change: `tests/test_hash.py` → 128 passed (was 126); full suite → 5932 passed, 50 skipped; ruff → pass; mypy → pass.

## Blockers
- None demonstrated.

## Next task
- None pending; baseline green.
- If order-dependent flakiness reappears (radix/stale CLI file-error tests), reproduce with dnspython installed and identify which earlier test rebinds `ethscan.fileio`/`ethscan.stale` or reloads modules so `patch.object` targets diverge from `cli.py` call-time lookups.

(End of file)

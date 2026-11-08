# Handoff
Date: Sun Nov 08 2026

## What changed
- `tests/test_hash.py`: added two tests covering `run_check` with pepper + iterations (peppered PBKDF2 check), previously untested at the `run_check` level: `test_run_check_iterations_with_pepper_match` and `test_run_check_iterations_with_pepper_mismatch`. A module-level helper `_peppered_pbkdf2_digest` builds the expected digest (`HMAC(pepper, PBKDF2-HMAC(sha256, password, salt, iterations).hex(), sha256)`).

## What was verified
- `python -m pytest tests/test_hash.py -q` → **128 passed, 0 failed** (was 126 before the change; the 2 new tests pass).
- `python -m pytest -q` → **5932 passed, 50 skipped, 0 failed** (full suite).
- `python -m ruff check .` → **All checks passed**.
- `python -m mypy ethscan/` → **Success: no issues found in 59 source files**.
- Manual PBKDF2 round-trips verified: plain salted+iterated check (MATCH) and peppered PBKDF2 check (MATCH); `--iterations` without `--salt` rejected with exit code 2.

## Unresolved
- None demonstrated.

## Approaches that failed
- None (bounded, evidence-based test addition).

## Next task
- **None pending; baseline green.**
- If order-dependent flakiness reappears (radix/stale CLI file-error tests), reproduce with dnspython installed and identify which earlier test rebinds `ethscan.fileio`/`ethscan.stale` or reloads modules so `patch.object` targets diverge from `cli.py` call-time lookups. Keep changes minimal and evidence-based.

(End of file)

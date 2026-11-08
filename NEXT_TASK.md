# Next Task

## Status: CLOSED (Sun Nov 08 2026)
No actionable prior assignment. Added two `run_check` pepper+iterations (peppered PBKDF2) tests to `tests/test_hash.py`; baseline re-verified green (128 hash tests pass, full suite 5932 passed/50 skipped/0 failed, ruff clean, mypy clean).

## Candidate
None pending. If future work is needed, pick a single high-value, verifiable improvement only when reproduced/justified (do not speculate).

## Constraints
- Do not re-audit `--out`/`--init` routing or revisit closed flakiness without a reproduction.
- Do not weaken safety controls or turn maintenance into an infrastructure project.
- Do not make speculative changes; preserve the working baseline.
- If order-dependent flakiness reappears: reproduce with dnspython installed and identify which earlier test rebinds `ethscan.fileio`/`ethscan.stale` or reloads modules so `patch.object` targets diverge from `cli.py` call-time lookups.

(End of file)

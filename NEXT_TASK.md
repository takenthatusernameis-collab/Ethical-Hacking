# Next Task

## Task
None pending. The empty-target normalization drive is complete: every module that accepts a target now rejects empty/whitespace/invalid hosts with `TargetSpecError` (CLI exit 2), except `oracle` and `postgresql`, which are in `PROBE_FAILURE_MODULES` by design (they treat an unusable target as a failed probe and report it in-band, exit 0 — their contract is left alone).

## Scope
If future work is needed, pick a single high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls.

## Candidates
- Remaining test files with mypy errors (reproduce per file first): `test_dnsbrute.py` (47), `test_hash.py` (46), `test_urlcheck.py` (39), `test_whois.py` (37).
- `tests/test_ping.py` carries a pre-existing Python 3.14 `socket.timeout` read-only descriptor blocker (6 runtime failures, 2 typing errors) — fix only typing errors independent of that failure.

## Verification
- `python -m pytest -q` → 5957 passed, 50 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` → clean on changed files.
- `python -m ruff check ethscan/ tests/` → All checks passed.

(End of file - total 21 lines)
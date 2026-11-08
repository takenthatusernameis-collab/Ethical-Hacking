# Handoff
Date: Sun Nov 08 2026

## What changed
- `README.md`: updated “Salted & peppered hashing” bullet to document `--iterations N` with `--salt` using `PBKDF2-HMAC(...)` and that `--check` can verify PBKDF2 digests. Evidence: `python -m ethscan hash --help` shows `--iterations`; behavior verified (`--password/--algorithm/--salt/--iterations` works).

## What was verified
- `python -m pytest -q` → **5932 passed, 50 skipped, 0 failed** (post-change).
- `python -m ruff check .` → **All checks passed**.
- `python -m mypy ethscan/` → **Success: no issues found in 59 source files**.
- All 54 CLI `--help` invocations returned 0 (smoke check).
- Repo inspection: no TODO/FIXME/XXX/HACK in `*.py`; version 0.1.0.

## Unresolved
- None demonstrated.

## Approaches that failed
- None (bounded, evidence-based doc fix).

## Next task
- **None pending; baseline green.**
- If order-dependent flakiness reappears (radix/stale CLI file-error tests), reproduce with dnspython installed and identify which earlier test rebinds `ethscan.fileio`/`ethscan.stale` or reloads modules so `patch.object` targets diverge from `cli.py` call-time lookups. Keep changes minimal and evidence-based.

(End of file - total 25 lines)

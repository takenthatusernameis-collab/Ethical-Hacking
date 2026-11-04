# Task
Date: Wed Nov 04 2026

## Current state
- HEAD on origin/main; working tree has uncommitted change to `ethscan/oracle.py` (3 `# pragma: no cover - defensive` additions) and `tests/test_oracle.py` (+1 test).
- Tests: 5578 passed, 50 skipped; `ruff` clean; `mypy ethscan` clean (59 files).
- `ethscan/oracle.py` coverage 100% (up from 98%).
- `ethscan/ntp.py` coverage 100%. `ethscan/mysql.py` coverage 100%.

## Blockers
- None.

## Next task
- Close remaining coverage gaps in `ethscan/radix.py` (next module). Add focused tests for reachable uncovered lines or `# pragma: no cover - defensive` for unreachable defensives, re-run `pytest`, `ruff check .`, `mypy ethscan` to verify. Do not commit unless explicitly asked.

(End of file)

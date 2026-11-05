# Task
Date: Wed Nov 05 2026

## Current state
- HEAD on origin/main; working tree has uncommitted change to `tests/test_snmp.py` (added `test_run_snmp_connector_uncaught_exception_is_caught` for lines 586-587). No production change.
- Tests: 5586 passed, 53 skipped, 0 failed; `ruff` clean; `mypy ethscan` clean (59 files).
- `ethscan/snmp.py` coverage 100% (up from 99%, lines 586-587 were the only miss).

## Blockers
- None.

## Next task
- Look for next coverage gaps (e.g. `ethscan/smtp.py` lines 305, 463-478, 488; `ethscan/ssh.py` lines 168, 632-633). Pick one module, add focused tests for reachable uncovered lines or `# pragma: no cover - defensive` for unreachable defensives, re-run `pytest`, `ruff check .`, `mypy ethscan` to verify. Do not commit unless explicitly asked.

(End of file - total 13 lines)
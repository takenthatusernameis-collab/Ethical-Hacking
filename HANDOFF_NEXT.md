# Handoff
Date: Thu Nov 05 2026

## What changed
- Added `tests/test_mssql_hostile_sweep.py` with focused hostile-transport / hostile-input edge-case tests for MSSQL (`tests/test_mssql_hostile_sweep.py:1`):
  - `test_hostile_answer_is_reported_not_raised` — every body in `HOSTILE_BODIES` (empty, non-TDS text, truncated headers, full byte range, etc.) yields a result dict with an `error` key and never raises.
  - `test_transport_failure_is_reported_not_raised` — a connector raising `OSError` is reported through `results["error"]`, never raised.

## Verified
- `python -m pytest tests/test_mssql_hostile_sweep.py -v`: 2 passed.
- Full `python -m pytest`: 5609 passed, 53 skipped, 0 failed.
- `python -m ruff check .`: all checks passed.
- `python -m mypy ethscan`: no issues in 59 source files.
- Coverage remains complete across all 59 modules (100%).

## Unresolved
- Other protocol modules still rely only on the shared `test_protocol_hostile_sweep.py` and have no module-specific hostile sweep: oracle, postgresql, smb, ldap, ntp, netbios (mysql and mssql now covered).

## Next task
- Pick another protocol module without a module-specific hostile sweep (e.g., `ethscan/oracle.py`), add focused tests following `tests/test_mssql_hostile_sweep.py`, re-run full `pytest`/`ruff`/`mypy`. Do not commit unless explicitly asked.

(End of file - total 20 lines)
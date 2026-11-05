# Handoff
Date: Thu Nov 05 2026

## What changed
- Added `tests/test_ldap_hostile_sweep.py` with focused hostile-transport / hostile-input edge-case tests for LDAP (`tests/test_ldap_hostile_sweep.py:1`):
  - `test_hostile_answer_is_reported_not_raised` — every body in `HOSTILE_BODIES` (empty, non-LDAP text, truncated BER headers, truncated TLV, non-SEQUENCE, unknown application tag, full byte range) yields a result dict with an `error` key and never raises, for `run_ldap`.
  - `test_transport_failure_is_reported_not_raised` — a connector raising `OSError` is reported through `results["error"]`, never raised.

## Verified
- `python -m pytest tests/test_ldap_hostile_sweep.py -v`: 2 passed.
- Full `python -m pytest`: 5617 passed, 53 skipped, 0 failed.
- `python -m ruff check .`: all checks passed.
- `python -m mypy ethscan`: no issues in 59 source files.

## Unresolved
- Other protocol modules still rely only on the shared `test_protocol_hostile_sweep.py` and have no module-specific hostile sweep: ntp, netbios (ldap now covered; mysql, mssql, oracle, postgresql, redis, smb previously covered).

## Next task
- Pick another protocol module without a module-specific hostile sweep (e.g., `ethscan/ntp.py` or `ethscan/netbios.py`), add focused tests following `tests/test_oracle_hostile_sweep.py`, re-run full `pytest`/`ruff`/`mypy`. Do not commit unless explicitly asked.

(End of file)

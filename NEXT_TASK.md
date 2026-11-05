# Next Task
Pick another protocol module without a module-specific hostile sweep (e.g. `ethscan/mssql.py`),
add focused tests for hostile transport / hostile input edge cases following
`tests/test_mysql_hostile_sweep.py`, re-run full `pytest`/`ruff`/`mypy`. Do not commit unless explicitly
asked.

Coverage is complete across all 59 modules (verified this session). The remaining
candidate work is hostile-transport / hostile-input edge-case sweeps for protocol
modules that currently rely only on the shared `test_protocol_hostile_sweep.py`
and have no module-specific hostile sweep (mssql, oracle, postgresql, smb, ldap,
ntp, netbios).

(End of file - total 8 lines)

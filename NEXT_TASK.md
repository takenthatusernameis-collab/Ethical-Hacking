# Next Task for Agent

## Status
- Working tree: modified (ethscan/mssql.py, ethscan/oracle.py, tracking files). Not committed.
- Tests: 3902 passed, 1 skipped.
- RUF059 (unused unpacked vars) now clean.

## Next precise task
Apply the safe, deterministic lint cleanups that ruff can auto-fix without --unsafe where possible; otherwise one bounded code at a time. Candidate: SIM102, SIM113, SIM117, PERF102, UP031 (1 each) and EXE001 (1). Verify with ruff and pytest.

## Status: COMPLETE (this session)

### What changed
- Fixed incomplete test `tests/test_resolve.py::test_run_resolve_dnspython_unknown_exception_swallowed` to actually call `run_resolve` with an unknown record type when `DNS_AVAILABLE` is True and `resolve_with_dnspython` raises an exception, asserting the exception is swallowed and the key is not added to records (covering ethscan/resolve.py:232-233).

### What was actually verified
- tests/test_resolve.py: 71 passed.
- Coverage on ethscan/resolve.py: missed reduced from 3 to 1 (line 225 remains; provably unreachable defensive continue for supported types).
- ruff check tests/test_resolve.py ethscan/resolve.py: all checks passed.
- Full suite: python -m pytest -q -> 5418 passed, 53 skipped (same totals as before; no regressions).

### What remains unresolved
- resolve.py:225 unreachable defensive branch (leave per unreachable-defensive precedent).
- Remaining small coverage gaps: postgresql.py:202, 355-356 (unreachable; connector errors caught inside _send_recv), smtp.py:247 (unreachable defensive), plus larger-gap modules mssql.py (9), mysql.py (3), oracle.py (4), vuln.py (6), hash.py (7), cli.py (5), and env-dependent subdomains.py:17 / subtake.py:19 (dnspython import branches).

### Which approaches failed and why
- None this session.

### One precise next task
- Close the next reachable gap, e.g. ethscan/postgresql.py:202 or one of postgresql.py:355-356 (or skip as unreachable if not mockable via existing patterns), or ethscan/vuln.py/hash.py/cli.py/mssql/mysql/oracle depending on mockability; strictly skip provably unreachable defensive branches and env-dependent dnspython import branches. Verify with focused coverage + targeted tests following existing patterns.

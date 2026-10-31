## Status: COMPLETE (this session)

### What changed
- Added two tests to tests/test_whois.py covering the top-level ``error`` branches in ethscan/whois.py: ``format_whois_report_markdown`` (line 286) and ``format_whois_report_csv`` (line 364), following the existing formatter test pattern (construct a data dict, call the formatter, assert on output).

### What was actually verified
- tests/test_whois.py: 44 passed.
- Coverage on ethscan/whois.py: 100% (was 99%; lines 286, 364 now covered).
- ruff check tests/test_whois.py ethscan/whois.py: all checks passed.
- Full suite: python -m pytest -q -> 5410 passed, 53 skipped (was 5408 passed before the change).

### What remains unresolved
- Remaining small coverage gaps across the package are mostly mock-dependent ``except`` branches: resolve.py:232-233, postgresql.py:355-356, smtp.py:134/247, ssh.py:335, plus larger-gap modules mssql.py (9 lines), mysql.py (3), oracle.py (4), vuln.py (6).
- Some gaps were investigated and are unreachable defensive code, not defects: redis.py:58-59 (outer condition requires host.startswith("["), so "]:", can never be at index 0), resolve.py:225 ("should not happen" defensive continue), postgresql.py:202 (guard unreachable under while pos < n). Consistent with the radix.py precedent: leave these, do not add tests for unreachable states.

### Which approaches failed and why
- None this session.

### One precise next task
- Close the next reachable gap in a single module, e.g. ethscan/postgresql.py:355-356 (``except Exception as exc: error = str(exc)``) by mocking the connector to raise in a run_postgresql test, or smtp.py:134/247 via a socket raising a non-timeout/OSError exception. Maintain existing architecture and test patterns; skip unreachable defensive branches.

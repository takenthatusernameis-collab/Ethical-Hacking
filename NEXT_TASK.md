# Next Task for Agent

## Context
- dnssec.py coverage improved from 89% to 98% with 9 targeted tests in tests/test_dnssec.py (no source changes).
  - Covered: _parse_dns_name pointer truncation + invalid length bits; _parse_dnskey_response/_parse_ds_response truncated record data; _query_dnskey_dnspython/_query_ds_dnspython success + error paths (via `ethscan.dnssec.dns` MagicMock patch); markdown DS "unknown error" branch.
- dnssec.py lines 11-16 remain uncovered: the `import dns` success branch — impossible without dnspython installed (same class as postgresql.py:201 unreachable code).
- Full suite: 3630 passed, 1 skipped (+9 new tests, no regressions). ruff: 17 pre-existing errors, none introduced.
- Current per-module coverage: mysql.py 89% (25 missing: lines 107, 111, 150, 152, 157, 160, 172, 184, 197, 213, 241-263, 424) — now the lowest with the most missing lines; redis.py 92% (21 missing), vuln.py 93% (24 missing) next.

## Task
Identify the module with meaningful coverage gaps (mysql.py at 89% with 25 missing lines is the recommended target) and add targeted unit tests in tests/test_mysql.py without modifying source. Focus on uncovered branches/edge cases (missing lines: 107, 111, 150, 152, 157, 160, 172, 184, 197, 213, 241-263, 424).

## Verification
1. Run `python3 -m pytest -q --cov=ethscan --cov-report=term-missing` to see current coverage per module.
2. Add minimal targeted tests to tests/test_mysql.py for the missing lines above.
3. Run `python3 -m pytest -q tests/test_mysql.py` to ensure new tests pass.
4. Run full suite `python3 -m pytest -q` to confirm no regressions.
5. Run `python3 -m ruff check tests/test_mysql.py` and ensure zero new linting issues are introduced (17 pre-existing errors in test_dnssec.py are out of scope).

## Constraints
- No live network calls; mock external dependencies.
- No modifications to source files under `ethscan/`.
- Keep changes minimal and focused.
- Follow existing test patterns.

## Evidence
- mysql.py: 89% (219 stmts, 25 missing: 107, 111, 150, 152, 157, 160, 172, 184, 197, 213, 241-263, 424)
- dnssec.py: 98% (392 stmts, 6 missing: lines 11-16 un-coverable without dnspython)
- postgresql.py: 99% (1 missing: line 201 unreachable defensive code)
- cve.py: 100% (324/324 statements)
- Full suite green: 3630 passed, 1 skipped

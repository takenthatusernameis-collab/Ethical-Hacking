# Next Task for Agent

## Context
- postgresql.py coverage improved from 91% to 99% with 8 targeted tests in tests/test_postgresql.py (no source changes).
- cve.py coverage improved from 87% to 100% with 17 targeted tests added to tests/test_cve.py (no source changes).
  - Covered cache error paths (_load_cache/_save_cache/_is_cache_valid), _fetch_cve_data success/non-dict/network-error, _get_cached_or_fetch cache hit/offline-fallback/save-cache, _extract_cve_summary edge cases, _severity_rank empty string, run_cve services-file read error + NVD summary branch, _finding_detail non-service kind, markdown profile/service_timeout/workers/api_url/severity_filter/cached/offline_fallback sections.
- Full suite: 3621 passed, 1 skipped (was 3604, +17 new tests, no regressions).
- `postgresql.py` line 201 remains uncovered — unreachable defensive code (`data[pos:pos+1]` on bytes always returns 1 byte when `pos < len(data)`).
- Next focus: continue improving coverage for other modules. dnssec.py at 89% is now the lowest with the most missing lines (45 missing), tied with mysql.py at 89% (25 missing), followed by redis.py at 92% (21 missing), vuln.py at 93% (24 missing).

## Task
Identify the next module with meaningful coverage gaps (dnssec.py at 89% with 45 missing lines is the recommended target) and add targeted unit tests in tests/test_dnssec.py without modifying source. Focus on uncovered branches/edge cases.

## Verification
1. Run `python3 -m pytest -q --cov=ethscan --cov-report=term-missing` to see current coverage per module.
2. Pick a module with < 100% (recommended: dnssec.py) and add minimal targeted tests to improve coverage.
3. Run `python3 -m pytest -q tests/test_<chosen>.py` to ensure new tests pass.
4. Run full suite `python3 -m pytest -q` to confirm no regressions.
5. Run `python3 -m ruff check tests/test_<chosen>.py` and fix any linting issues.

## Constraints
- No live network calls; mock external dependencies.
- No modifications to source files under `ethscan/`.
- Keep changes minimal and focused.
- Follow existing test patterns.

## Evidence
- postgresql.py: 99% (236 stmts, 1 missing: line 201 unreachable defensive code)
- cve.py: 100% (324/324 statements)
- dnssec.py: 89% (45 missing lines)
- mysql.py: 89% (25 missing lines)
- redis.py: 92% (21 missing lines)
- vuln.py: 93% (24 missing lines)
- Full suite green: 3621 passed, 1 skipped

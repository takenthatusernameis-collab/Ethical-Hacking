# Next Task for Agent

## Context
- postgresql.py coverage improved from 91% to 99% with 8 targeted tests in tests/test_postgresql.py (no source changes).
- Full suite: 3604 passed, 1 skipped (baseline maintained, all green).
- `postgresql.py` line 201 remains uncovered — unreachable defensive code (`data[pos:pos+1]` on bytes always returns 1 byte when `pos < len(data)`).
- Next focus: continue improving coverage for other modules. cve.py at 87% is the lowest (43 missing lines), followed by dnssec.py at 89% (45 missing), redis.py at 92% (21 missing), vuln.py at 93% (24 missing).

## Task
Identify the next module with meaningful coverage gaps (cve.py at 87% is the lowest, or dnssec.py at 89%, redis.py at 92%, vuln.py at 93%) and add targeted unit tests in its test file without modifying source. Focus on uncovered branches/edge cases.

## Verification
1. Run `python3 -m pytest -q --cov=ethscan --cov-report=term-missing` to see current coverage per module.
2. Pick a module with < 100% and add minimal targeted tests to improve coverage.
3. Run `python3 -m pytest -q tests/test_<chosen>.py` to ensure new tests pass.
4. Run full suite `python3 -m pytest -q` to confirm no regressions.
5. Run `python3 -m ruff check tests/test_<chosen>.py` and fix any linting issues.

## Constraints
- No live network calls; mock external dependencies.
- No modifications to source files under `ethscan/`.
- Keep changes minimal and focused.
- Follow existing test patterns.

## Evidence
- postgresql.py: 99% (235/236 statements, line 201 unreachable defensive code)
- cve.py: 87% (43 missing lines)
- dnssec.py: 89% (45 missing lines)
- redis.py: 92% (21 missing lines)
- vuln.py: 93% (24 missing lines)
- Full suite green: 3604 passed, 1 skipped

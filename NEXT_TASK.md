# Next Task for Agent

## Context
- validate.py coverage improved to 100% with targeted tests in tests/test_validate.py (no source changes).
- Full suite: 3596 passed, 1 skipped (baseline maintained, all green).
- Next focus: continue improving coverage for other modules. Review current state to pick the next lowest-coverage/high-value module.

## Task
Identify the next module with meaningful coverage gaps (e.g., urlcheck.py, vuln.py, validate is now 100%; check term-missing for all modules) and add targeted unit tests in its test file without modifying source. Focus on uncovered branches/edge cases.

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
- validate.py: 100% (199/199 statements)
- Full suite green: 3596 passed, 1 skipped

# Next Task for Agent

## Context
- Current state: Full test suite 3585 passed, 1 skipped. No source changes made.
- smtp.py coverage improved from 88% to 99% (+targeted tests in tests/test_smtp.py). Only line 222 remains uncovered (edge case in connection error path).
- validate.py is at 96% coverage with 7 missing lines: 59-60, 76, 271, 296, 309, 339.

## Task
Add targeted unit tests to `tests/test_validate.py` to cover the missing lines in `ethscan/validate.py` (lines 59-60, 76, 271, 296, 309, 339). Do NOT modify source code in `ethscan/validate.py`. Focus on exercising specific branches/edge cases that are currently uncovered.

## Verification
1. Run `python3 -m pytest -q tests/test_validate.py` to ensure new tests pass.
2. Run `python3 -m pytest -q --cov=ethscan.validate --cov-report=term-missing` and confirm coverage increases toward 100% (or as much as achievable without source changes).
3. Run full suite `python3 -m pytest -q` to confirm no regressions (must remain green).
4. Run `ruff check tests/test_validate.py` and fix any linting issues.

## Constraints
- No live network calls; mock external dependencies where needed.
- No modifications to source files under `ethscan/`.
- Keep changes minimal and focused on the missing branches.
- Follow existing test patterns and style in the codebase.

## Evidence
- Current validate.py coverage: 96% (7 missing lines as listed above)
- Full suite: 3585 passed, 1 skipped (baseline)

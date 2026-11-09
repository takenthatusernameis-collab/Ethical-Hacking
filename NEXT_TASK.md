# Next Task

## Status: OPEN (re-evaluate)

Per-file typing hygiene (mypy errors in test files) is effectively complete for current errors as of session 26.

## Scope
- Reproduce remaining `mypy tests/` errors before taking work: `python -m mypy tests/ 2>&1 | tail -8`.
- Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` read-only descriptor blocker: 2 typing errors + 6 runtime failures).
- Only fix newly appearing/reproducible errors with the established pattern (test-side casts/annotations; widen source types only when minimal/safe/root-cause).
- Do not weaken safety controls or make speculative changes.

## Verification (required per batch)
1. `python -m mypy tests/<file>` → 0 issues for touched files.
2. `python -m ruff check tests/<file>` → clean.
3. Targeted `python -m pytest <touched-test-files> -q` → pass.
4. `python -m pytest -q --ignore=tests/test_ping.py` → baseline unchanged (5878 passed, 50 skipped at session 26; re-verify).

## Current evidence (session 26)
- `python -m mypy tests/` → `Found 2 errors in 1 file (checked 128 source files)`; both errors in `tests/test_ping.py` (lines 586, 663: `str | None` `in` operand — tied to blocked file). 3 annotation-unchecked notes in `test_postgresql.py`, `test_ftp.py`, `test_smtp.py` (not errors).
- `python -m pytest -q --ignore=tests/test_ping.py` → 5878 passed, 50 skipped, 0 failed.
- Cleaned this session: `tests/test_cve.py` (29→0). `tests/test_web.py` already clean.

## Handoff
Update `HANDOFF_NEXT.md` and this file with: files fixed, exact verification evidence, remaining counts (reproduced), and any new constraints/failures.
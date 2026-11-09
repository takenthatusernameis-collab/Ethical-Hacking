# Next Task

## Status: OPEN (re-evaluate)

Per-file typing hygiene for mypy errors in test files is complete (excluding `tests/test_ping.py`, see below) as of session 26-27. The repo is in a clean baseline.

## Scope
- Reproduce remaining `mypy tests/` errors before taking work: `python -m mypy tests/ 2>&1 | tail -8`.
- Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` read-only descriptor blocker: 2 typing errors in blocked tests + 6 runtime failures). Only fix ping typing errors if independent of that runtime failure and verifiable.
- Only fix newly appearing/reproducible errors with the established pattern (test-side casts/annotations; widen source types only when minimal/safe/root-cause).
- Do not weaken safety controls or make speculative changes.
- Select the next bounded, high-value, verifiable task if no typing errors remain (e.g., a small bugfix with reproduction, or a focused improvement). Inspect README/TASK.md/history first; do not create parallel infrastructure.

## Verification (required per batch)
1. `python -m mypy ethscan/` → 0 issues.
2. `python -m mypy tests/` → only known ping errors (or 0).
3. `python -m ruff check ethscan/ tests/` → clean.
4. Targeted `python -m pytest <touched-test-files> -q` → pass.
5. `python -m pytest -q --ignore=tests/test_ping.py` → baseline unchanged (5878 passed, 50 skipped at session 27; re-verify).

## Current evidence (session 27)
- `python -m mypy tests/` → `Found 2 errors in 1 file (checked 128 source files)`; both in `tests/test_ping.py` (lines 586, 663: `str | None` `in` operand — inside tests blocked by Python 3.14 `socket.timeout` runtime descriptor issue). 3 annotation-unchecked notes in `test_postgresql.py`, `test_ftp.py`, `test_smtp.py` (not errors).
- `python -m mypy ethscan/` → Success: no issues found in 59 source files.
- `python -m ruff check ethscan/ tests/` → All checks passed! (session 27 fixed 5 fixable issues: unused `cast` import in `tests/test_cli.py`; B010 `setattr`→assignment in `tests/test_cli_trace_brute_unreachable_sweep.py`).
- `python -m pytest -q --ignore=tests/test_ping.py` → 5878 passed, 50 skipped, 0 failed.
- Session 27 source cleanup (no behavior change): `ethscan/jwt.py` replaced 2 `# type: ignore[assignment]` with `cast()`; verified `tests/test_jwt.py` (41 passed).

## Handoff
Update `HANDOFF_NEXT.md` and this file with: files fixed, exact verification evidence, remaining counts (reproduced), and any new constraints/failures.

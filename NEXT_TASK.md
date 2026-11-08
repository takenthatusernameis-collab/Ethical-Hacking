# Next Task

## Status: CLOSED (this session)
Baseline is GREEN: `pytest -q` → 5936 passed, 50 skipped, 0 failed.

## Completed (Sun Nov 08 2026, session 6)
- Fixed 4 mypy errors in `tests/test_jwt_hostile_sweep.py`:
  - Annotated `HOSTILE_TOP_LEVEL: tuple[object, ...]` (var-annotated).
  - Added `Any`/`cast` imports and cast hostile values when calling formatters.
- No behavior change; `ethscan/` source untouched.
- Verified: mypy clean, ruff clean, 2 hostile-sweep tests pass.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.

## Suggested next task
- Continue typing hygiene in remaining hostile-sweep test files (`test_ssl_hostile_sweep.py`, `test_ssh_hostile_sweep_formatter.py`) using the same pattern; reproduce with mypy first.

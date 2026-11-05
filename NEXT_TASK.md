# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps that lack a permanent check.

## Baseline (verified this session)
- `python3 -m pytest -q` → `5874 passed, 53 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`
- HEAD (committed): `b6c024f`; working tree has uncommitted local changes (`tests/test_cli.py`, handoff docs) — do not commit unless asked.

## This session
- Added permanent `click.Choice` validation sweep in `tests/test_cli.py` for all 126 Choice options (enumeration + invalid `__bogus__` usage-error rejection before callbacks). Verified targeted tests and full checks.

## Candidate work (only if demonstrated)
- Scan for uncovered validation/side-effect-before-rejection gaps: `click.Path`/`click.File` constraints, custom `callback=` validators, mutually-exclusive/required-option groups, or non-Range/non-Choice options that can do work before rejection. Add smallest permanent guard/test only when a real gap is evidenced.
- Do not duplicate existing IntRange/FloatRange/Choice/ports/CIDR/host/offline-input sweeps.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

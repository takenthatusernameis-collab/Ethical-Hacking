# Next Task

## Status: OPEN

Baseline is fully green (session 28): `mypy ethscan/` 0 issues (59 files), `mypy tests/` 0 errors (128 files, 3 annotation-unchecked notes), `ruff check ethscan/ tests/` clean, full `python -m pytest -q` → 5938 passed, 50 skipped.

## Scope
Select one bounded, high-value, verifiable improvement. Candidates (inspect and reproduce before choosing):
- A small reproducible bug or inconsistent behavior in an `ethscan/` module with clear user-facing impact.
- A missing error-path/edge-case test where the implementation already handles the case but coverage is thin and the test is cheap/deterministic.
- A formatter/CLI validation inconsistency (reproduce with a concrete input).

Do not:
- Introduce parallel execution, redesign orchestration, or weaken permissions/safety controls.
- Make speculative refactors or "cleanup" without a demonstrated problem.
- Touch unrelated files.

## Verification (required)
1. Reproduce the issue/gap with a concrete command or test before changing.
2. `python -m mypy ethscan/` → 0 issues.
3. `python -m mypy tests/` → 0 errors.
4. `python -m ruff check ethscan/ tests/` → clean.
5. Targeted `python -m pytest <touched-test-files> -q` → pass.
6. `python -m pytest -q` → baseline passes (report exact counts).

## Handoff
Update `HANDOFF_NEXT.md` and this file with: what changed, reproduction/evidence, exact verification counts, what remains unresolved (if any), and one precise next task.

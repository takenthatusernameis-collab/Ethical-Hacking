# Next Task
Continue evidence-driven permanent-test coverage only for demonstrated gaps.

## Baseline (verified this session)
- `python3 -m pytest -q` → `5878 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Scanned command bodies for validation after partial side effects; no new demonstrated gap. Baseline re-verified.

## Candidate work (only if demonstrated)
- Add smallest permanent guard/test only with evidence.
- Do not duplicate existing sweeps.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

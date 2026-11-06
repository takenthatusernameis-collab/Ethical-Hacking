# Next Task
Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection, then add the smallest permanent guard/test.

## Baseline (verified this session)
- `python3 -m pytest -q --tb=no` → `5878 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Baseline verified green; no code change. The evidence-driven CLI edge-case sweep (ports/timeout/workers/iterations/CIDR/target/host/offline/file/JSON/XML/`--out`/`--config`, intentional `--contains`/`hash --check`/`validate` reporting) found no new demonstrated gap; not repeated unchanged.

## Candidate work (only if demonstrated)
- Add smallest permanent guard/test only with a reproducible case.
- Do not duplicate existing sweeps or intentional in-output reporting semantics.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

# Next Task
Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection, or a silent-accept validation gap, then add the smallest permanent guard/test.

## Baseline (verified this session)
- `python3 -m pytest -q --tb=no` → `5880 passed, 50 skipped, 0 failed`
- `python3 -m ruff check .` → clean
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`

## This session
- Fixed demonstrated gap: `recon --modules` silently accepted unknown module names (exit 0, unknowns ignored; unlike `dns --types`). `ethscan/cli.py` now validates modules and rejects with `click.UsageError` (exit 2) before any recon work. Added `test_recon_modules_unknown_rejected` / `test_recon_modules_mixed_unknown_rejected` in `tests/test_cli.py`. Library unchanged.

## Candidate work (only if demonstrated)
- Find/reproduce a validation or side-effect-before-reject gap in a **materially different** area (CLI edge sweep is exhausted; `recon --modules` now fixed). Stop at first reproduced gap; smallest guard/test only.
- Do not duplicate existing sweeps or treat intentional in-output reporting/contracts as gaps.

## Constraints
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest, then full suite, ruff, mypy. Never claim checks passed without evidence.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

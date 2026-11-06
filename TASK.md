# Task
Date: Fri Nov 06 2026

## Current state
- HEAD: working tree modified (uncommitted). Baseline was green before changes.
- Tests: `5880 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.

## This session
- **Demonstrated gap (reproduced):** `recon --modules bogus` (and `dns,bogus,whois`) silently accepted unknown module names, ran 0/only-recognized modules, and returned exit 0 with structured output — no validation, unlike `dns --types BOGUS` which rejects with exit 2 / UsageError.
- **Fix (smallest reversible):** In `ethscan/cli.py` (`recon`), validate `--modules` names against `{subdomains,dns,whois,geo,trace}` and raise `click.UsageError` listing unknown + valid modules. Validation runs before any recon work (no side effects). Library `ethscan/recon.py` unchanged.
- **Tests:** Added `tests/test_cli.py::test_recon_modules_unknown_rejected` and `test_recon_modules_mixed_unknown_rejected` (assert exit 2, message, and `run_recon` not called). Existing recon tests unchanged (21 recon CLI tests pass).

## Verified (evidence)
- Repro before fix: `recon --modules bogus` → exit 0, `modules_run=[]`; `recon --modules dns,bogus,whois` → exit 0, `modules_run=["dns","whois"]`, DNS executed.
- After fix: `recon --modules bogus` → exit 2, `Unknown modules: bogus. Valid modules: dns, geo, subdomains, trace, whois`; mixed → exit 2, `Unknown modules: bogus`.
- `python3 -m pytest tests/test_recon.py tests/test_recon_hostile_sweep.py -q --tb=no` → `38 passed`.
- `python3 -m pytest tests/test_cli.py -q -k recon --tb=no` → `23 passed, 1002 deselected` (includes 2 new tests).
- `python3 -m pytest -q --tb=no` → `5880 passed, 50 skipped, 0 failed`.
- `python3 -m ruff check .` → `All checks passed!`
- `python3 -m mypy ethscan` → `Success: no issues found in 59 source files`.

## Blockers
- None.

## Next task
- Pursue only a *demonstrated* gap: reproduce a CLI option/callback reaching side effects before clean rejection (or a silent-accept validation gap like the recon modules case) in an area **different** from the exhausted CLI edge sweep and now-fixed `recon --modules`. If scanning, choose a materially different surface and stop at first reproduced gap; add the smallest permanent guard/test. Keep baseline green; do not commit unless asked. Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`.

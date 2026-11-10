# Next Task

## Status: OPEN

Baseline is fully green: `mypy ethscan/` 0 issues (59 files), `ruff check ethscan/ tests/` clean, full `python -m pytest -q` → 5951 passed, 50 skipped, 0 failed.

## Scope
Fix the empty-host bug in the remaining `_normalize_host` modules, one at a time, following the established pattern (`ping`/`osdetect`/`vuln`/`ssh`/`brute`/`cve`/`tls`):
- Add `TargetSpecError` import from `ethscan.target`.
- Add `if not host: raise TargetSpecError(f"Could not parse host from target {target!r}")` after computing `host` in `_normalize_host`.
- Add a CLI test `test_<module>_invalid_target_is_usage_error` in `tests/test_cli.py` (exit code 2 + "Could not parse host from target") and a unit test `test_normalize_host_rejects_empty_target` in the module's test file.

Modules remaining: `ssl`.

Do not:
- Introduce parallel execution, redesign orchestration, or weaken permissions/safety controls.
- Make speculative refactors or "cleanup" without a demonstrated problem.
- Touch unrelated files.

## Verification (required)
1. Reproduce the issue/gap with a concrete command before changing (e.g. `python -m ethscan ssl --target ""` exits 0 instead of 2).
2. `python -m mypy ethscan/` → 0 issues.
3. `python -m mypy tests/` → 0 errors.
4. `python -m ruff check ethscan/ tests/` → clean.
5. Targeted `python -m pytest <touched-test-files> -q` → pass.
6. `python -m pytest -q` → baseline passes (report exact counts).

## Handoff
Update `HANDOFF_NEXT.md` and this file with: what changed, reproduction/evidence, exact verification counts, what remains unresolved (if any), and one precise next task.

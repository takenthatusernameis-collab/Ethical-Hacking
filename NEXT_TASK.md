# Next Task

## Status: OPEN

Baseline is fully green (session 32): `mypy ethscan/` 0 issues (59 files), `mypy tests/` 0 errors (128 files), `ruff check ethscan/ tests/` clean, full `python -m pytest -q` → 5945 passed, 50 skipped, 0 failed.

## Scope
Fix the same empty-host bug in the remaining `_normalize_host` modules, one at a time, following the established `ping.py`/`osdetect.py`/`vuln.py`/`ssh.py` pattern:
- Add `TargetSpecError` import from `ethscan.target`.
- Add `if not host: raise TargetSpecError(f"Could not parse host from target {target!r}")` after computing `host` in `_normalize_host`.
- Add a CLI test `test_<module>_invalid_target_is_usage_error` in `tests/test_cli.py` (exit code 2 + "Could not parse host from target") and optionally a unit test in the module's test file.

Modules remaining: `brute`, `cve`, `tls`, `ssl`. Start with `brute`.

Do not:
- Introduce parallel execution, redesign orchestration, or weaken permissions/safety controls.
- Make speculative refactors or "cleanup" without a demonstrated problem.
- Touch unrelated files.

## Verification (required)
1. Reproduce the issue/gap with a concrete command before changing (e.g. `python -m ethscan brute --target ""` exits 0 instead of 2).
2. `python -m mypy ethscan/` → 0 issues.
3. `python -m mypy tests/` → 0 errors.
4. `python -m ruff check ethscan/ tests/` → clean.
5. Targeted `python -m pytest <touched-test-files> -q` → pass.
6. `python -m pytest -q` → baseline passes (report exact counts).

## Handoff
Update `HANDOFF_NEXT.md` and this file with: what changed, reproduction/evidence, exact verification counts, what remains unresolved (if any), and one precise next task.

(End of file)

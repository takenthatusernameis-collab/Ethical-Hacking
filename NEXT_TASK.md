# Next Task

## Status: CLOSED

Baseline is fully green: `mypy ethscan/` 0 issues (59 files), `mypy tests/` 0 issues (128 files), `ruff check ethscan/ tests/` clean, full `python -m pytest -q` → 5953 passed, 50 skipped, 0 failed.

## Scope
COMPLETED — Fixed the empty-host bug in the final remaining `_normalize_host` module (`ssl`), following the established pattern (ping/osdetect/vuln/ssh/brute/cve/tls/ssl). All eight modules now reject empty/whitespace/invalid targets with `TargetSpecError` (CLI exit 2).

## What was done this session
- `ethscan/ssl.py`: imported `TargetSpecError`; added `host = ...` + `if not host: raise TargetSpecError(f"Could not parse host from target {target!r}")` in `_normalize_host`.
- `tests/test_ssl.py`: added `test_normalize_host_rejects_empty_target` (empty/whitespace/`https://`).
- `tests/test_cli.py`: added `test_ssl_invalid_target_is_usage_error` (exit code 2 + "Could not parse host from target").

## Verification
1. Reproduced before fix: `python -m ethscan ssl --target ""` → exit 0, `"host": ""`.
2. After fix: `--target ""`, `"   "`, `"https://"` all → exit 2, `Error: Invalid value for '--target': Could not parse host from target ...`.
3. `python -m mypy ethscan/` → 0 issues in 59 files.
4. `python -m mypy tests/` → 0 issues in 128 files.
5. `python -m ruff check ethscan/ tests/` → All checks passed.
6. Targeted `python -m pytest tests/test_ssl.py tests/test_cli.py -q -k "ssl or normalize_host or invalid_target"` → 80 passed, 1045 deselected.
7. Full `python -m pytest -q` → 5953 passed, 50 skipped, 0 failed (baseline 5951; +2 new tests).

## Handoff
Update `HANDOFF_NEXT.md` and this file with: what changed, reproduction/evidence, exact verification counts, what remains unresolved (if any), and one precise next task.
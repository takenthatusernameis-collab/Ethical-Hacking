# Next Task

## Status: CLOSED

Baseline is fully green: `mypy ethscan/` 0 issues (59 files), `mypy tests/` 0 issues (128 files), `ruff check ethscan/ tests/` clean, full `python -m pytest -q` → 5959 passed, 50 skipped, 0 failed.

## Scope
COMPLETED — All modules that accept a target now reject empty/whitespace/invalid hosts with `TargetSpecError` (CLI exit 2).

- `_normalize_host` modules (ping/osdetect/vuln/ssh/brute/cve/tls/ssl): previously fixed (sessions 29–36).
- `s3`, `fuzz`, `web`: fixed this session. These validate hosts via `check_target_host`, which rejects spaces/control chars but not an empty host, so they accepted `--target ""` / `"   "` / `"https://"` with exit 0 and misleading output. Added the same empty-host `TargetSpecError` raise in `_normalize_target`/`_normalize_base_url`/`_parse_url`, following the established pattern.

## What was done this session (session 37)
- `ethscan/s3.py`: import `TargetSpecError`; `_normalize_target` raises `TargetSpecError(f"Could not parse host from target {target!r}")` when no usable host is extracted.
- `ethscan/fuzz.py`: import `TargetSpecError`; `_normalize_base_url` raises the same on an empty host.
- `ethscan/web.py`: import `TargetSpecError`; `_parse_url` raises the same and no longer falls back to `host="localhost"`.
- `tests/test_s3.py`: added `test_normalize_target_rejects_empty_target`; updated `test_normalize_target_empty`, `test_build_candidates_empty_target`, `test_run_s3_empty_target` to expect `TargetSpecError` (they asserted the old buggy behavior).
- `tests/test_fuzz.py`: added `test_normalize_base_url_rejects_empty_target`.
- `tests/test_web.py`: added `test_parse_url_rejects_empty_target`.
- `tests/test_target.py`: updated `test_the_url_modules_still_accept_the_valid_target_forms` — `web._parse_url("")` now raises instead of returning `("localhost", 443, True)`.
- `tests/test_cli.py`: added `test_s3_invalid_target_is_usage_error`, `test_fuzz_invalid_target_is_usage_error`, `test_web_invalid_target_is_usage_error` (exit code 2 + "Could not parse host from target").

## Verification
1. Reproduced before fix: `s3/fuzz/web --target ""`, `"   "`, `"https://"` → exit 0 with bogus results.
2. After fix: all three → exit 2, `Error: Invalid value for '--target': Could not parse host from target ...`.
3. `python -m mypy ethscan/` → 0 issues in 59 files.
4. `python -m mypy tests/` → 0 issues in 128 files.
5. `python -m ruff check ethscan/ tests/` → All checks passed.
6. Full `python -m pytest -q` → 5959 passed, 50 skipped, 0 failed (baseline 5953; +6 new tests).

## Handoff
Update `HANDOFF_NEXT.md` and this file with: what changed, reproduction/evidence, exact verification counts, what remains unresolved (if any), and one precise next task.

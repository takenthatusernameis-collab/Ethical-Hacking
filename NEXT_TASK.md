# Next Task

## Task
Fix the empty/invalid-target gap for the `report` command: `report --target ""|"   "|"https://"|":6379"` exits 0 with in-band output instead of a CLI usage error (exit 2), and `report` is absent from `TARGET_USAGE_ERROR_COMMANDS`.

## Scope
- One command only: `report` (ethscan/cli.py `report` command).
- Follow the established `scan`/empty-host pattern: validate the target via `normalize_host(target)` so `TargetSpecError` propagates through `_TargetGroup.invoke` → click usage error (exit 2); do not alter valid-target behavior.
- Add `"report"` to `TARGET_USAGE_ERROR_COMMANDS` in tests/test_cli.py.
- Add `test_report_invalid_target_is_usage_error` (`""`, `"   "`, `"https://"` → exit 2 + "Could not parse host from target"), matching the `scan`/`tls`/`ssl`/`s3`/`fuzz`/`web` pattern.
- Keep `oracle`/`postgresql` out of scope (intentional in-band contract).
- Do not batch other commands unless `report` is trivial and fully verified.

## Constraints / evidence
- Baseline (this session): `pytest -q` → 5960 passed, 50 skipped, 0 failed; `mypy ethscan/ tests/` → clean (187 files); `ruff check ethscan/ tests/` → all checks passed.
- `report` is target-consuming (`@click.option("--target", required=True, ...)`) but does not normalize the target; it calls `_validate_enum_target(target)` (only `parse_url`, which does not reject hostless targets) then `run_report` → `scan_ports(target, ...)`.
- Verified symptom this session: `report --target ""` → exit 0 with JSON output.
- `normalize_host` now correctly raises `TargetSpecError` for `:6379`/`https://:6379`/empty targets (fixed in ethscan/target.py this session).

## Verification (to complete)
- Repro after fix: `report --target ""|"   "|"https://"|":6379"` → exit 2 usage error; `report --target 127.0.0.1 ...` → exit 0 (valid-target behavior unchanged).
- `python -m pytest tests/test_cli.py -q -k "report or invalid_target"` → pass.
- `python -m pytest -q` → baseline unchanged (0 failed).
- `python -m mypy ethscan/ tests/` → clean.
- `python -m ruff check ethscan/ tests/` → all checks passed.

## Next task after that
- None pending unless another target-consuming command is found missing from `TARGET_USAGE_ERROR_COMMANDS`.

(End of file)

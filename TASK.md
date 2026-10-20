# TASK

Status: COMPLETE (cve --services-file non-utf8 hardening done)

## What was done
- `ethscan/cve.py` now reads `--services-file` via `load_json()` (lenient UTF-8 decode) so non-UTF-8 bytes do not leak a traceback.
- Added library test `test_run_cve_services_file_not_utf8` and CLI subprocess test `test_cli_cve_services_file_non_utf8_no_traceback`.
- All file-content/CLI handling follows existing lenient patterns.

## Verification
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/test_cve.py -v` → 60 passed.
- `python -m pytest -q` → 4559 passed, 48 skipped, 2 warnings.

## Handoff
No open issues. Baseline is clean.

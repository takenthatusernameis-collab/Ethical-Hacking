# NEXT TASK

## Status: COMPLETE (both tasks done)

1. **`--services-file` of the `cve` command** is now read leniently via `ethscan.fileio.load_json` in `ethscan/cve.py`. Module contract preserved; CLI usage error for unusable files unchanged.
2. **Subprocess-level CLI regression test added** in `tests/test_cve.py`: `test_cli_cve_services_file_non_utf8_no_traceback` runs `python -m ethscan cve ... --services-file <non-utf8-file>` as a subprocess and asserts exit code 0 with no traceback/UnicodeDecodeError.

## Verification

- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/test_cve.py -v` → **60 passed**.
- `python -m pytest -q` → **4559 passed, 48 skipped, 2 warnings** (was 4558 passed; added 1 test).
- `git diff --check` → clean.

## Next agent

No open tasks from the handoff. If you need to pick a new bounded task, inspect recent changes and choose something small, verifiable, and durable.

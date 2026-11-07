# Next Task

## Candidate (bounded, verify before coding)
Inspect `ethscan/fileio.py` `write_text` for atomicity/error handling consistency with `_write_output`; verify behavior under unwritable parent dir and partial-write scenarios. Reproduce before changing. Do not commit unless asked.

## Baseline (verified this session)
- `python -m pytest -q` → 5921 passed, 50 skipped.
- `ruff check ethscan/cli.py tests/test_cli.py tests/test_config.py` → clean.

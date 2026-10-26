## What changed this session
- Added CLI-level test coverage for `config --init` in tests/test_config.py:
  it writes a valid, loadable sample config, creates missing parent
  directories, and rejects `--init` used together with `--out` (exit code 2).

## What was actually verified
- `python -m pytest tests/ -q` → 5221 passed, 51 skipped, 0 warnings.
- `python -m ruff check ethscan/ tests/` → All checks passed.

## What remains unresolved
None.

## Which approaches have already failed and why
None this session.

## One precise next task
None — repository complete. If new work arrives, implement the smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.

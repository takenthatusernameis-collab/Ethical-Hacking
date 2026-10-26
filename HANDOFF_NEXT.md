## What changed this session
- tests/test_cli.py: added four CLI-level tests verifying that the `config`
  command surfaces configuration warnings in its JSON, Markdown, and CSV output
  (unknown command warning, unknown option warning) instead of only in stderr.

## What was actually verified
- `python -m pytest tests/ -q` → 5225 passed, 51 skipped, 0 warnings
- `python -m ruff check ethscan/ tests/` → All checks passed

## What remains unresolved
None.

## Which approaches have already failed and why
None this session.

## One precise next task
None — repository complete. If new work arrives, implement the smallest change
solving a demonstrated problem and verify with `python -m pytest tests/ -q` +
`python -m ruff check ethscan/ tests/`.

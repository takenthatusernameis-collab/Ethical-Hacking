## Status: COMPLETE

Added CLI-level test coverage for `config --init` (the only write path of the
`config` command that was not exercised at the CLI boundary): it writes a
valid, loadable sample config, creates missing parent directories, and rejects
`--init` used together with `--out`.

### What changed
- tests/test_config.py: added three CLI-level tests for `config --init`
  (sample config is loadable via `load_config`, missing parent dirs are
  created, `--init` and `--out` are mutually exclusive).

### What was actually verified
- `python -m pytest tests/ -q` → 5221 passed, 51 skipped, 0 warnings.
- `python -m ruff check ethscan/ tests/` → All checks passed.

### What remains unresolved
None.

### One precise next task
None — repository complete. If new work arrives, implement the smallest change solving a demonstrated problem and verify with `python -m pytest tests/ -q` + `python -m ruff check ethscan/ tests/`.

## Status: COMPLETE

### What changed
- Added `.github/workflows/ci.yml` (push/pull_request to main) running lint/test.

### What was actually verified
- Local: ruff/mypy/pytest all pass (5228 passed, 48 skipped); ci.yml parses as valid YAML.

### What remains unresolved
- CI not yet executed on GitHub (local validation only).

### Which approaches failed and why
- None.

### One precise next task
- None.

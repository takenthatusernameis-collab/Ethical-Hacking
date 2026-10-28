## Status: COMPLETE

### What changed
- Added `.github/workflows/ci.yml` (push/pull_request to `main`, ubuntu-latest, Python 3.10) running `python -m ruff check ethscan tests`, `python -m mypy ethscan`, and `python -m pytest -q`. Installs from `requirements.txt` plus ruff/mypy/pytest/dnspython.

### What was actually verified
- `python -m ruff check ethscan tests` -> All checks passed.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5228 passed, 48 skipped.
- `.github/workflows/ci.yml` parses as valid YAML.

### What remains unresolved
- CI has not yet run on GitHub (only validated locally); GitHub-hosted runner execution is pending the next push/PR.

### Which approaches failed and why
- None.

### One precise next task
- None (CI added and verified locally). Repository is in a clean, verified state.

(End of file - total 19 lines)
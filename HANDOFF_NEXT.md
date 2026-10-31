## Status: COMPLETE (this session)

### What changed
- Created `.github/workflows/test.yml`: GitHub Actions CI workflow for testing on push/PR to `main` (Python 3.10/3.11/3.12). Installs deps (ruff, pytest, pytest-cov, dnspython, editable ethscan), runs `ruff check ethscan tests` and `python -m pytest -q`.

### What was actually verified
- `.github/workflows/test.yml` parses as valid YAML (`python -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"`).
- `ruff check ethscan tests` passes (as part of workflow steps).
- `python -m pytest -q`: 5432 passed, 53 skipped (no regressions).

### What remains unresolved
- None.

### Which approaches failed and why
- None.

### One precise next task
- Commit `.github/workflows/test.yml` if explicitly requested (repo convention: commit only when explicitly asked). File is ready and verified.

## Status: COMPLETE

### What changed
- Added GitHub Actions CI workflow at `.github/workflows/ci.yml` running ruff, mypy, and pytest on push and pull_request to `main` (ubuntu-latest, Python 3.10, installs from requirements.txt plus ruff/mypy/pytest/dnspython). Did not modify `.github/workflows/main.yml`.

### What was actually verified
- `python -m ruff check ethscan tests` -> All checks passed.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5228 passed, 48 skipped.

### What remains unresolved
- None.

### Which approaches failed and why
- None.

### One precise next task
- None (all checks passing and CI added). If desired, consider adding `- name: Install package` (`pip install -e ".[dev]"`) to CI for completeness, but not necessary given current setup.

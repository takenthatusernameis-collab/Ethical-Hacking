## Status: COMPLETE

### What changed
- Fixed 5 ruff `B904` errors in `ethscan/cli.py` (3) and `ethscan/scanner.py` (2) by chaining re-raised exceptions with `from err` / `from None` inside `except` clauses.

### What was actually verified
- `python -m ruff check ethscan tests` -> All checks passed.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5228 passed, 48 skipped.

### What remains unresolved
- No project CI workflow enforces ruff/mypy/pytest on push or pull requests.

### Which approaches failed and why
- None.

### One precise next task
- Add a GitHub Actions CI workflow (`.github/workflows/ci.yml`) that runs ruff, mypy, and pytest on push/pull_request to `main`. Do not modify `.github/workflows/main.yml`. Verify locally before completing.

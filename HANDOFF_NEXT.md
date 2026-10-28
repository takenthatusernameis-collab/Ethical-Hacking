## Status: COMPLETE

### What changed
- Added a `[tool.ruff]` lint configuration to `pyproject.toml` and fixed 5 lint errors across `ethscan/resolve.py`, `ethscan/ssl.py`, and `ethscan/validate.py`.

### What was actually verified
- `python -m ruff check ethscan tests` -> All checks passed.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5225 passed, 51 skipped.

### What remains unresolved
- ruff is configured but not declared as a project/dev dependency.

### Which approaches failed and why
- None.

### One precise next task
- Declare ruff as a dev dependency (`dev = ["ruff>=0.17"]` in `[project.optional-dependencies]`) and verify `python -m ruff check ethscan tests` passes after install.

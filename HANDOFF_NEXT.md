## Status: COMPLETE

### What changed
- Confirmed ruff is declared as a dev dependency in `pyproject.toml` (`dev = ["ruff>=0.17"]` under `[project.optional-dependencies]`).
- Reinstalled the package with dev extras to confirm the declaration is valid and installable.

### What was actually verified
- `pip install -e ".[dev]"` -> Successfully installed ethscan-0.1.0.
- `python -m ruff check ethscan tests` -> All checks passed.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5225 passed, 51 skipped.

### What remains unresolved
- None.

### Which approaches failed and why
- None.

### One precise next task
- No next task. The linting baseline is complete and verified.
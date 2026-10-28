## Status: PENDING

### What changed
- None yet.

### What was actually verified
- None yet.

### What remains unresolved
- ruff is configured in `pyproject.toml` but not declared as a dependency, so it is not installed by `pip install -r requirements.txt` and not enforced.

### Which approaches failed and why
- None.

### One precise next task
- Declare ruff as a dev dependency: add `dev = ["ruff>=0.17"]` to `[project.optional-dependencies]` in `pyproject.toml`, then run `pip install -e ".[dev]"` and `python -m ruff check ethscan tests` to confirm the lint config is enforced and clean.

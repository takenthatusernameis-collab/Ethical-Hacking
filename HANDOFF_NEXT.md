## Status: COMPLETE

### What changed
- Added `dnspython>=2.0` and `mypy>=1.0` to `[project.optional-dependencies].dev` in `pyproject.toml`.
- Installed dev extras (`pip install -e ".[dev]"`).
- Fixed type handling in `ethscan/dnssec.py` for dnspython nameserver objects (`Nameserver` with `.address`) so they are passed as strings to `dns.query.udp` (mypy-clean).

### What was actually verified
- `pip install -e ".[dev]"` -> Successfully installed ethscan-0.1.0 (with dnspython 2.9.0).
- `python -m ruff check ethscan tests` -> All checks passed.
- `python -m mypy ethscan` -> Success: no issues found in 59 source files.
- `python -m pytest -q` -> 5228 passed, 48 skipped.

### What remains unresolved
- None.

### Which approaches failed and why
- None.

### One precise next task
- No next task. Dev tooling/deps are updated and all checks pass.

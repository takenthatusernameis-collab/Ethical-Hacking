## Status: COMPLETE

### What changed
- Added XDG Base Directory config support in `ethscan/config.py` (searches `$XDG_CONFIG_HOME/ethscan/` or `~/.config/ethscan/` in addition to cwd/home). Updated docstring and `README.md`.

### What was actually verified
- `python -m ruff check ethscan/config.py` -> All checks passed.
- `python -m mypy ethscan/config.py` -> Success: no issues found in 1 source file.
- `python -m pytest tests/test_config.py -v` -> 48 passed.
- `python -m pytest -q` -> 5228 passed, 48 skipped.

### What remains unresolved
- None.

### Which approaches failed and why
- None.

### One precise next task
- None.

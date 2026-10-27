## Status: COMPLETE

### What changed
- Fixed mypy typing errors in `ethscan/geo.py` (14 errors -> 0) via cast narrowing: geo, hops, notes, hop, hop_geo, target, row return.

### What was actually verified
- `python -m mypy ethscan/geo.py` -> Success: no issues found in 1 source file.
- `python -m ruff check ethscan/geo.py` -> All checks passed.
- `python -m pytest tests/test_geo.py -q` -> 52 passed.

### What remains unresolved
- Remaining mypy errors in other modules (~158 across 34 files).

### One precise next task
Fix mypy errors in next module with most errors; inspect `python -m mypy ethscan/` to pick.

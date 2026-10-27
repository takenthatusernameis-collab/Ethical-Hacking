## Status: COMPLETE

### What changed
- Fixed mypy typing errors in `ethscan/whois.py` (17 errors -> 0) by adding `cast` import and narrowing `dict[str, object]` values: `parsed` dict cast in markdown/csv formatters, `nameservers`/`status_codes` list casts, `data["raw"]` str cast, `recursive_hops` list-of-dicts cast, and per-hop `hop_parsed` dict cast with `cast('str', ...)` on field accesses.

### What was actually verified
- `python -m mypy ethscan/whois.py` -> Success: no issues found in 1 source file.
- `python -m ruff check ethscan/whois.py` -> All checks passed.
- `python -m pytest tests/test_whois.py -q` -> 42 passed.

### What remains unresolved
- Remaining mypy errors in other modules (~210 across 38 files).

### One precise next task
Fix mypy errors in next module with most errors; inspect `python -m mypy ethscan/` to pick.

(End of file - total 16 lines)
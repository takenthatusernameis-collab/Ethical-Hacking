## Status: COMPLETE

### What changed
- Fixed mypy typing errors in `ethscan/whois.py` (17 errors -> 0) via cast narrowing of dict[str, object] values in markdown/csv formatters, list[str] casts for nameservers/status_codes, str cast for raw, list[dict[str, object]] cast for recursive_hops, and per-hop dict cast with str field casts.

### What was actually verified
- `python -m mypy ethscan/whois.py` -> Success: no issues found in 1 source file.
- `python -m ruff check ethscan/whois.py` -> All checks passed.
- `python -m pytest tests/test_whois.py -q` -> 42 passed.

### What remains unresolved
- Remaining mypy errors in other modules (~210 across 38 files).

### One precise next task
Fix mypy errors in next module with most errors; inspect `python -m mypy ethscan/` to pick.

(End of file - total 15 lines)
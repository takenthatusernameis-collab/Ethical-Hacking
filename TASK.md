## Status: COMPLETE

### What changed
- Fixed mypy typing errors in `ethscan/ntp.py` (3 errors -> 0): cast `_send_recv` result to bytes for `_parse_time_response`, `_parse_monlist_response`, and `len(mon_data)`.

### What was actually verified
- `python -m mypy ethscan/ntp.py` -> Success: no issues found.
- `python -m pytest tests/test_ntp.py -q` -> 47 passed.

### What remains unresolved
- Remaining mypy errors in other modules (~14 across 7 files).

### One precise next task
Fix mypy errors in `ethscan/netbios.py` (1 error); inspect `python -m mypy ethscan/netbios.py`.

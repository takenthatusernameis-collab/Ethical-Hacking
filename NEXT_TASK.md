# Next Task for Agent

## Status
- Working tree: modified (ethscan/completion.py narrowed blind-except). Not committed.
- Tests: 3902 passed, 1 skipped.
- S110: 2 remaining (both `ethscan/redis.py:223,242`, load-bearing). S112: 0. BLE001: 46 (was 47; `ethscan/completion.py:29` fixed).
- `ethscan/cert.py:89` and `ethscan/cve.py:97` BLE001 sites wrap multiple statements (network + JSON); narrowing would change runtime behavior — NOT safe bounded targets.

## Next precise task
The safe `try-except-pass` → `contextlib.suppress` conversion is exhausted. Remaining ruff codes are unsafe; the two remaining single-statement BLE001 candidates (cert.py:89, cve.py:97) are unsafe to narrow because they wrap multiple statements. Pick a non-lint bounded task: add a missing test for an untested command, or review README for stale command docs. Verify with `python -m pytest -q` after changes.

(End of file - total 16 lines)
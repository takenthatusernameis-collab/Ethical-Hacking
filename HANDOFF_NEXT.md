## Status: COMPLETE (this session)

### What changed
- `tests/test_osdetect.py`: added `test_run_osdetect_invalid_max_workers_reports_probes`, covering `ethscan/osdetect.py:424-425` (outer `except` around the `ThreadPoolExecutor` block). Reached via `run_osdetect(..., max_workers=0)` which raises `ValueError` at executor construction; real inputs, no mocking. Test-only; no source modifications.

### What was actually verified
- `python -m pytest tests/test_osdetect.py -q` -> 82 passed.
- `python -m coverage run -m pytest tests/test_osdetect.py -q && python -m coverage report --include="ethscan/osdetect.py" -m` -> `ethscan/osdetect.py` 100% (0 miss; was 99%, 2 miss at 424-425).
- Full suite: `python -m pytest -q` -> 5394 passed, 48 skipped, 0 failed.
- `python -m coverage run -m pytest -q && python -m coverage report --include="ethscan/osdetect.py" -m` -> `ethscan/osdetect.py` 100%.
- `python -m ruff check ethscan/osdetect.py tests/test_osdetect.py` -> All checks passed.

### What remains unresolved
- `ethscan/radix.py` 95% (20 miss): lines 181-185, 196-198, 216, 222-225, 236-240, 295-296, 324. All defensive/fallback branches confirmed unreachable with real `ipaddress` inputs:
  - `:181-185`, `:236-240` — sorting/grouping real networks never raises.
  - `:196-198` — `getattr(..., 'version', None)` never raises.
  - `:216`, `:222-225` — `collapse_addresses` of two overlapping same-family networks always returns exactly one network; version check catches family mismatch first.
  - `:295-296` — `ip_network(start/prefix)` never raises for valid prefixes.
  - `:324` — `children` is always a list.
  Covering them requires pathological fake objects / forcing exceptions — complexity disproportionate to the gain. Out of scope for test-only work without a source refactor that fixes no bug.

### Which approaches failed and why
- `ethscan/radix.py` defensive branches: empirically confirmed all 20 missed lines unreachable with real `ipaddress` inputs. Not test-only feasible; no source change made (no bug to fix).

### One precise next task
- Do not force speculative radix.py changes. Next bounded task: select ONE remaining small coverage gap from a full-suite coverage report (current candidates: cli.py, hash.py, mongodb.py, mssql.py, mysql.py, oracle.py, postgresql.py, redis.py, resolve.py, smtp.py, ssh.py), verify the missed lines are reachable with REAL inputs before writing any test, add a test only if reachable without disproportionate complexity, verify `coverage report --include="<module>.py" -m` reaches 100% and `ruff check` + full suite pass. If the gap is also unreachable defensive code, document evidence and defer.

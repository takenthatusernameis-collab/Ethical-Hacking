# Next Task

## Status: CLOSED (this session)
Typing hygiene completed for `tests/test_hash.py` (46 errors -> 0):
- `ethscan/hash.py`: Added `HashEntry`/`HashResult`/`CheckResult` TypedDicts; changed `run_hash`/`run_check` return types to them; widened the 6 formatter signatures to `Mapping[str, object]`.
- `tests/test_hash.py`: no edits required.

Baseline preserved: `mypy ethscan/` clean (59 files); `mypy tests/test_hash.py` clean; `py_compile` OK; runtime smoke tests pass. `pytest`/`ruff` not installed in this environment — verify pytest baseline when available.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.
- Reproduce with `python -m mypy tests/<file>` before fixing any file.

## Suggested next task
Continue per-file typing hygiene in remaining test files with mypy errors, reproducing each one first (e.g. `test_ping.py`, `test_radix.py`, `test_cidr.py`, `test_dnsbrute.py`, `test_urlcheck.py`, `test_whois.py`). Do not speculate or weaken safety controls.

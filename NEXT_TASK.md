# Next Task

## Status: CLOSED (this session)
Typing hygiene completed for `tests/test_urlcheck.py` (23 errors -> 0) and `tests/test_whois.py` (31 errors -> 0):
- `ethscan/urlcheck.py`: `run_urlcheck -> dict[str, Any]`; formatter/report signatures widened to `Mapping[str, object]` (covariant). Runtime behavior unchanged.
- `ethscan/whois.py`: `parse_whois`/`run_whois -> dict[str, Any]`; formatter/report signatures widened to `Mapping[str, object]`. Runtime behavior unchanged.
- `tests/test_whois.py`: added targeted `cast("dict[str, Any]"|...)`/annotations for indexing into `dict[str, object]` results (semantically neutral; aligns with established pattern).

Verified: `mypy` clean on `ethscan/urlcheck.py`, `ethscan/whois.py`, and `tests/test_cidr.py tests/test_radix.py tests/test_smtp.py tests/test_urlcheck.py tests/test_whois.py` (5 files, 0 issues); `mypy ethscan/` clean (59 files); `py_compile` OK; `ruff` clean; `pytest tests/test_urlcheck.py` → 31 passed; `pytest tests/test_whois.py` → 44 passed; `pytest -q --ignore=tests/test_ping.py` → 5875 passed, 53 skipped, 0 failed.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.
- Reproduce with `python -m mypy tests/<file>` before fixing any file.

## Suggested next task
Continue per-file typing hygiene across remaining test files (repo-wide `python -m mypy ethscan/ tests/` still reports pre-existing errors). Reproduce each target with `python -m mypy tests/<file>` first, fix per file using the established pattern (TypedDict/Mapping in source where indexing `dict[str, object]` results is the issue; test-only annotations/casts otherwise). Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` blocker). Do not speculate or weaken safety controls.

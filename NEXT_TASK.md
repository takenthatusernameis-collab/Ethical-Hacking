# Next Task

## Status: CLOSED (this session)
Typing hygiene completed for `tests/test_dnsbrute.py` (33 errors -> 0):
- `ethscan/dnsbrute.py`: Added 6 TypedDicts (`_AxfrResult`, `_DnsAnswer`, `_DnsResponse`, `_ResolvedLabel`, `_AxfrEntry`, `_DnsbruteResult`); changed 7 function return types to them; widened the 4 formatter signatures + 3 helper signatures to `Mapping[str, object]`; removed redundant casts in `query_axfr_raw`.
- `tests/test_dnsbrute.py`: no behavior change; added `assert err is not None` before 4 `in` checks; annotated 2 `fake_dns` locals as `Any`.

Baseline preserved: `mypy ethscan/` clean (59 files); `mypy ethscan/ tests/test_dnsbrute.py` clean (60 files); `py_compile` OK; `ruff` clean; `pytest tests/test_dnsbrute.py` → 105 passed, 2 skipped; `pytest -q --ignore=tests/test_ping.py` → 5875 passed, 53 skipped, 0 failed.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.
- Reproduce with `python -m mypy tests/<file>` before fixing any file.

## Suggested next task
Continue per-file typing hygiene in remaining test files with mypy errors, reproducing each one first (e.g. `test_cidr.py`, `test_radix.py`, `test_urlcheck.py`, `test_whois.py`, `test_smtp.py`). Do not speculate or weaken safety controls.
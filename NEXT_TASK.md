# Next Task

## Status
Session 178 (Sat Nov 14 2026): closed all remaining gaps in `ethscan/resolve.py` (100% statement + branch).
- `70->68`, `89->87`: malformed `getaddrinfo` sockaddrs with non-`str` hosts are skipped.
- `311`: non-dict data to `format_resolve_report_csv` yields header only.
- `323->314`: record values of `None` emit no CSV row.
- 4 tests added to `tests/test_resolve.py`.

## Baseline (verified this session)
- `python3 -m pytest -q` → 32001 passed, 146 skipped, 0 failed (1 existing warning).
- `python3 -m pytest tests/test_resolve.py --cov=ethscan.resolve --cov-branch --cov-report=term-missing -q` → `ethscan/resolve.py` 100% (0 miss, 0 partial).
- `python3 -m mypy ethscan/` → Success: no issues found in 59 source files.
- `python3 -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Approaches already tried / ruled out
- `ethscan/hash.py` arc `589->596`: requires a list/tuple subclass whose `__bool__` is True when empty; not a valid public-contract input. Do not retry.
- `ethscan/ping.py` and `ethscan/resolve.py` gaps: resolved (tests added).

## Next task
- Close the `ethscan/service.py` branch gaps: `197->199`, `199->201`, `205->210`.
  - `197->199`: a result with a falsy `banner` but truthy `service` must omit the `banner` key and still append the entry.
  - `199->201`: a result with a truthy `banner` but falsy `service` must omit the `service` key and still append the entry.
  - `205->210`: `_port_key` given a non-dict or a non-numeric `port` must return `0`.
  - Reproduce with `python3 -m pytest tests/test_service.py --cov=ethscan.service --cov-branch --cov-report=term-missing -q`; follow the existing fake `grab_banner` monkeypatch pattern in that file.
  - Finish with the full gate: `python3 -m pytest -q`, `python3 -m mypy ethscan/`, `python3 -m ruff check ethscan/ tests/`, `python3 check_readme.py`.
- Alternatives with small remaining gaps: `ethscan/radix.py` (`315->313`, `359->361`), `ethscan/whois.py` (`367->369`, `369->371`, `371->373`, `373->375`, `376->357`).

(End of file - total 36 lines)
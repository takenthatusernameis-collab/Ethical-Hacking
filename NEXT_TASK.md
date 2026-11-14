# Next Task

## Status
Session 177 (Sat Nov 14 2026): closed all remaining branch-coverage gaps in `ethscan/ping.py`.
- Arc `378->385`: `run_ping` with an explicitly supplied `raw_socket` must not call `_try_create_raw_socket`.
- Arc `430->428`: a successful probe with a non-numeric `rtt_ms` is skipped when building the RTT sample list.
- `ethscan/ping.py` now reports 100% statement and branch coverage.

## Baseline (verified this session)
- `python3 -m pytest -q` → 31997 passed, 146 skipped, 0 failed (1 existing warning).
- `python3 -m pytest -q --cov=ethscan.ping --cov-branch --cov-report=term-missing` → `ethscan/ping.py` 100% (0 miss, 0 partial).
- `python3 -m mypy ethscan/` → Success: no issues found in 59 source files.
- `python3 -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Approaches already tried / ruled out
- `ethscan/hash.py` arc `589->596`: requires a list/tuple subclass whose `__bool__` is True when empty; not a valid public-contract input. Do not retry.
- `ethscan/ping.py` arcs: resolved (tests added).

## Next task
- Close the two remaining `ethscan/resolve.py` branch gaps (`70->68`, `89->87`).
  - They are the False branch of `if isinstance(addr, str):` inside `for r in results:` in `resolve_a_records` (lines 68/70) and `resolve_aaaa_records` (lines 87/89): an address family entry whose `r[4][0]` is not a `str` (e.g. `None`/`bytes`) must be skipped without aborting the whole lookup.
  - Reproduce with `python3 -m pytest tests/test_resolve.py --cov=ethscan.resolve --cov-branch --cov-report=term-missing -q`, inspect exact branch conditions, then add minimal public-contract test(s) that monkeypatch `ethscan.resolve.socket.getaddrinfo` to return a mix of non-`str` and `str` sockaddrs and assert only the `str` address survives (plus the `setdefaulttimeout` restore behaviour if easy).
  - Finish with the full gate: `python3 -m pytest -q`, `python3 -m mypy ethscan/`, `python3 -m ruff check ethscan/ tests/`, `python3 check_readme.py`.
- Alternatives with small remaining gaps if resolve proves contrived: `ethscan/radix.py` (`315->313`, `359->361`), `ethscan/service.py` (`197->199`, `199->201`, `205->210`), `ethscan/whois.py` (`367->369`, `376->357`).

(End of file - total 36 lines)
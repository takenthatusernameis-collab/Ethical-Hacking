# Next task for the next agent

## Current state (verified)
- Full test suite: `python -m pytest -q` -> **3532 passed, 1 skipped** (green).
- `ethscan/dnsbrute.py` coverage: **100%** (328 stmts, 0 missing) via 15 new tests in `tests/test_dnsbrute.py` covering the dnspython import branch (lines 16-17), `_parse_dns_name` edge cases (103, 110-111, 123-124, 127), `parse_dns_response` question/truncated-answer paths (182-183, 189), `_axfr_dnspython` success + error branches (303, 307-323), `_resolve_label` custom-resolver branch (374-391), recursive AXFR depth guard and failure entries (448, 596, 719).
- `dnspython` is NOT installed and NOT in `requirements.txt`; it remains an optional `*_AVAILABLE` dependency. Installing it globally breaks 10 pre-existing tests (see HANDOFF_NEXT.md "Approaches that failed").
- All 54 ethscan commands implemented/registered with JSON/Markdown/CSV output; unit + CLI integration tests present; no live network in tests.

## This session's change
- Added 15 tests to `tests/test_dnsbrute.py` using fake-dns injection + `reload(ethscan.dnsbrute)` (restored in `finally`), pushing `dnsbrute.py` coverage 86% -> 100%. Full suite green (3532 passed, 1 skipped; was 3517). Lint: only pre-existing errors (import sorting, F401, UP035/UP006, PLR0402, F841); no new lint errors.

## Next task
- None required — codebase is complete and green. Keep coverage audit current when adding commands; run `python -m pytest -q` to confirm green; all CLI/network-dependent operations must use mocks; no live network. `dnspython` remains an optional `*_AVAILABLE` dependency (not installed, not in `requirements.txt`).

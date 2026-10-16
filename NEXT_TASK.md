# Next task for the next agent

## Current state (verified)
- Full test suite: `python -m pytest -q` -> **3541 passed, 1 skipped** (green).
- `ethscan/ssl.py` coverage: **100%** (201 stmts, 0 missing) via 1 new test in `tests/test_ssl.py` covering `_parse_cert` except branches (lines 75-76, 82-88).
- `dnspython` is NOT installed and NOT in `requirements.txt`; optional `*_AVAILABLE` dependency. Installing it globally breaks 10 pre-existing tests (see HANDOFF_NEXT.md).
- All 54 ethscan commands implemented/registered with JSON/Markdown/CSV output; unit + CLI integration tests present; no live network in tests.

## This session's change
- Added `test_parse_cert_unhashable_keys_hit_except_branches` to `tests/test_ssl.py`; ssl.py coverage 96% -> 100%. Full suite green (3541 passed, 1 skipped). Lint: only pre-existing errors (9 on test_ssl.py); no new errors.
- Unstaged changes in working tree: `tests/test_web.py` (+8 tests, pre-existing) and `tests/test_ssl.py` (+1 test). Not committed.

## Next task
- Push `ethscan/whois.py` to 100% coverage: it is 99% with exactly 2 missing lines (209, 242). Add test(s) to `tests/test_whois.py`, run `python -m pytest -q` (expect ~3542 passed, 1 skipped), confirm `ethscan/whois.py` 100% via `--cov=ethscan`, and run `python -m ruff check tests/test_whois.py` (only pre-existing errors allowed). Mock all network/DNS dependencies; no live network.
- Fallback target: `ethscan/config.py` (91%, missing lines 91-92, 122-123, 182, 188-191, 269).

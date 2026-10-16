# Next task for the next agent

## Current state (verified)
- Full test suite: `python -m pytest -q` -> **3543 passed, 1 skipped** (green).
- `ethscan/whois.py` coverage: **100%** (172 stmts, 0 missing; previously missing lines 209, 242).
- `ethscan/ssl.py` coverage: **100%** (201 stmts, 0 missing).
- `dnspython` is NOT installed and NOT in `requirements.txt`; optional `*_AVAILABLE` dependency. Installing it globally breaks 10 pre-existing tests (see HANDOFF_NEXT.md).
- All ethscan commands implemented/registered with JSON/Markdown/CSV output; unit + CLI integration tests present; no live network in tests.

## This session's change
- Added 2 tests to `tests/test_whois.py` covering the two previously-uncovered `ethscan/whois.py` lines:
  - `test_run_whois_recursive_referral_equals_current_server` — line 209 (`referral == current_server` break).
  - `test_run_whois_recursive_response_repeat_loop_protection` — line 242 (`hop_raw in seen_raw` break).
- All network/DNS dependencies mocked; no live network.
- Lint: `python -m ruff check tests/test_whois.py` -> 6 errors, all pre-existing (same on unmodified file); no new errors.
- Unstaged changes in working tree: `tests/test_whois.py` (+2 tests). (`tests/test_web.py` and `tests/test_ssl.py` changes pre-date this session.) Not committed.

## Next task
- Push `ethscan/config.py` to 100% coverage: it is 91% with missing lines 91-92, 122-123, 182, 188-191, 269 per `python -m pytest -q --cov=ethscan --cov-report=term-missing`. Add test(s) to `tests/test_config.py`, run `python -m pytest -q` and `python -m pytest -q --cov=ethscan` to confirm config.py 100%, and lint with `python -m ruff check tests/test_config.py` (only pre-existing errors allowed). No live network; mock filesystem/config dependencies as needed.

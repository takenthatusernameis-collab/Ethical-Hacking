# Next Task for Agent

## Context
- `ethscan/redis.py` coverage task is COMPLETE: raised from 92% to **99%** (279 stmts, 2 missing).
  - The 2 remaining missing lines (55-56) are provably unreachable defensive code in `_normalize_target`, same class as `mysql.py:107/111/150` and `postgresql.py:201`; left uncovered intentionally (no source modification allowed).
  - Added 11 tests to `tests/test_redis.py`; full suite 3666 passed, 1 skipped; zero new ruff errors.
- `ethscan/geo.py` coverage task is COMPLETE: raised from 91% to **100%** (191 stmts, 0 missing).
  - Added 3 tests to `tests/test_geo.py`; full suite 3666 passed, 1 skipped; zero new ruff errors.
- `ethscan/mongodb.py` is now the lowest coverable-coverage module at **92%** with **15 missing lines**, all coverable via mocked connectors / crafted BSON data.

## Task
Identify the module with meaningful coverage gaps (`ethscan/mongodb.py` at 92%, 15 missing lines is the recommended target) and add targeted unit tests in `tests/test_mongodb.py` without modifying source under `ethscan/`. Focus on the uncovered branches/edge cases:

Missing lines: 80-90, 186-187, 205-206.

Key branches to cover:
- `_send_recv` lines 80-90: real-socket path error branches — `socket.timeout` (line 85-86), `ConnectionRefusedError` (line 87-88), `OSError` (line 89-90) via `patch("ethscan.mongodb.socket.create_connection")` with `side_effect`.
- `_parse_mongodb_buildinfo`/`_parse_mongodb_response` lines 186-187: version string extraction when `str_start + 4 + str_len < len(doc_data)` (craft BSON doc with a valid `version` field).
- decode-except lines 205-206: `except: pass` when decoding a field value raises (craft BSON with invalid UTF-8 bytes in a field value).

## Verification
1. Run `python3 -m pytest tests/test_mongodb.py -q` (baseline: 30 passed).
2. Add minimal targeted tests to `tests/test_mongodb.py` for the missing lines above.
3. Run `python3 -m pytest -q tests/test_mongodb.py` to ensure new tests pass.
4. Run `python3 -m pytest -q --cov=ethscan.mongodb --cov-report=term-missing` — mongodb.py should rise toward 100%.
5. Run full suite `python3 -m pytest -q` to confirm no regressions (baseline: 3666 passed, 1 skipped).
6. Run `python3 -m ruff check tests/test_mongodb.py` and ensure zero new linting issues are introduced.

## Constraints
- No live network calls; mock external dependencies via the `connector` parameter / `patch` (follows existing `test_mongodb.py` patterns).
- No modifications to source files under `ethscan/`.
- Keep changes minimal and focused; follow existing test patterns.

## Evidence
- `ethscan/mongodb.py`: 188 stmts, 15 missing, 92% cover.
- `tests/test_mongodb.py`: 30 passed baseline.
- `ethscan/redis.py`: 99% (done, only unreachable lines 55-56 remain).
- `ethscan/geo.py`: 100% (done).
- Full suite green: 3666 passed, 1 skipped.

# Next Task for Agent

## Context
- `mysql.py` coverage task is COMPLETE: raised from 89% to 99% (224 stmts, 3 missing).
  - The 3 remaining missing lines (107, 111, 150) are provably unreachable defensive code, same class as `postgresql.py:201`; left uncovered intentionally (no source modification allowed).
  - Added 1 test to `tests/test_mysql.py`; full suite 3652 passed, 1 skipped; zero new ruff errors.
- `ethscan/redis.py` is now the lowest coverable-coverage module at **92%** with **21 missing lines**, all coverable via mocked connectors.

## Task
Identify the module with meaningful coverage gaps (`ethscan/redis.py` at 92%, 21 missing lines is the recommended target) and add targeted unit tests in `tests/test_redis.py` without modifying source under `ethscan/`. Focus on the uncovered branches/edge cases:

Missing lines: 54-56, 112-113, 127, 149, 155, 159, 163-165, 200-201, 223-224, 242-243, 312, 316, 319.

Key branches to cover:
- `_normalize_target` lines 54-56: bracketed IPv6 host without `]:port` (e.g. `"[::1]"`).
- `_parse_resp_bulk_string` lines 112-113: `except Exception` returning `(None, 0)` (malformed length).
- `_parse_resp` lines 127, 149: `return None, 0` when `\r\n` not found for simple string / array count.
- `_parse_resp` array lines 155, 159, 163-165: `pos >= len(data)`, null-bulk-string `pass`/append branches.
- `_send_recv` lines 200-201: `sock.close()` raising in `finally`.
- `_parse_info` lines 223-224 / `_parse_config` lines 242-243: `except Exception: pass`.
- `run_redis` lines 312, 316, 319: `ping_resp` is `bytes` decode branch, non-bytes/non-str `str()` branch, non-PONG `pass` branch.

## Verification
1. Run `python3 -m pytest tests/test_redis.py -q` (baseline: 92 passed).
2. Add minimal targeted tests to `tests/test_redis.py` for the missing lines above.
3. Run `python3 -m pytest -q tests/test_redis.py` to ensure new tests pass.
4. Run `python3 -m pytest -q --cov=ethscan.redis --cov-report=term-missing` — redis.py should rise toward 100% (only unreachable defensive code, if any, remains).
5. Run full suite `python3 -m pytest -q` to confirm no regressions (baseline: 3652 passed, 1 skipped).
6. Run `python3 -m ruff check tests/test_redis.py` and ensure zero new linting issues are introduced.

## Constraints
- No live network calls; mock external dependencies via the `connector` parameter (follows existing `test_mysql.py`/`test_redis.py` patterns).
- No modifications to source files under `ethscan/`.
- Keep changes minimal and focused; follow existing test patterns.

## Evidence
- `ethscan/redis.py`: 279 stmts, 21 missing, 92% cover.
- `tests/test_redis.py`: 92 passed baseline.
- `ethscan/mysql.py`: 99% (done, only unreachable lines 107/111/150 remain).
- Full suite green: 3652 passed, 1 skipped.

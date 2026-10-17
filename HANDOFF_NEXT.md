What changed:
- Added `test_python_m_ethscan_main_help_runs` to `tests/test_main.py` to cover `ethscan/main.py:7` (the `cli()` call under `if __name__ == "__main__":`). Uses `runpy.run_module("ethscan.main", run_name="__main__")` with `ethscan.cli.cli` patched to raise `SystemExit`, avoiding a subprocess (which coverage cannot track).

What was verified:
- `tests/test_main.py` → 9 passed (was 8).
- `ethscan/main.py` coverage: 67% → **100%** (3 stmts, 0 missing).
- Full suite: **3860 passed, 1 skipped** (was 3859; +1 for the new test; no regressions).
- `python -m ruff check tests/test_main.py` → only the 2 pre-existing `PLW1510` errors on `subprocess.run` lines (51, 61); zero new issues.

What remains unresolved (provably dead code — intentionally left uncovered):
- `ethscan/ntp.py:387` — `if mon_resp.get("error"):` inside the `else` branch of the same `if mon_resp.get("error"):` at line 367. `mon_resp` is never mutated between the two checks, so the inner check is always False. Same class as vuln.py's unreachable lines (37, 57-62, 555-556, 904, 1047).
- `ethscan/postgresql.py:201` — `if not msg_type: break` where `msg_type = data[pos:pos + 1]` and the while loop condition is `pos < n`; a 1-byte slice is always truthy. Unreachable.
- `ethscan/smtp.py:222` — `sock.close()` in the outer `except` where `sock` can only be non-None if `_connect()` succeeded, but then only the inner try/except runs (catches `socket.timeout`/`OSError` and returns early). Nothing between `_connect` success and the outer except can raise those exceptions. Unreachable.

Which approaches failed and why:
- First attempt used `subprocess.run([sys.executable, "-m", "ethscan.main", ...])` to cover main.py:7, but coverage does not track subprocesses — line 7 stayed missing. Switched to `runpy.run_module` in-process with `cli` patched — reliable and coverage-trackable.

Next task:
- Continue improving coverage by tackling modules with the smallest remaining gaps. Next smallest: ftp.py (2 missing: lines 145-146), mongodb.py (2 missing: 205-206), oracle.py (2 missing: 304-305), redis.py (2 missing: 55-56), then mysql.py (3 missing: 107, 111, 150). Add minimal targeted unit tests to corresponding test files without modifying `ethscan/`. Verify targeted tests pass, ruff on modified test files passes, and full suite remains ≥3860 passed, 1 skipped.
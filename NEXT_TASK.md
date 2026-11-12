# Next Task

## Status
Repository is fully green: `python -m pytest -q` → 6080 passed, 53 skipped, 0 failed; `python -m mypy ethscan/ tests/` → clean except 2 pre-existing errors in `tests/test_smb.py:1437,1443` (unrelated); `python -m ruff check ethscan/ tests/` → all checks passed.

`ethscan/snmp.py` is now 100% coverage (session 101). Previously completed to 100% include `ethscan/smtp.py`, `smb.py`, `redis.py`, `postgresql.py`, `mysql.py`, `mssql.py`, `s3.py`, `trace.py`, `ntp.py`, `dnssec.py`, `mongodb.py`, `wifi.py`, and others per history. Every `ethscan/` module is now ≥98%.

## Remaining <100% modules (1-16 defensive lines each)
- `cli.py` (567-569, 770, 797, 863, 902, 4278, 4353, 4426, 4499, 5380, 5518, 5591, 5650-5651, 5656-5657, 5661)
- `subtake.py` (642-643)
- `ldap.py` (667, 740)
- `oracle.py` (475, 511)

TOTAL miss: 21.

Most are network-probe error branches or hard-to-trigger defensive guards (e.g. cleanup `except OSError: pass`, formatter non-dict guards). Reproduce exact uncovered lines first via `python -m pytest -q --cov=ethscan --cov-report=term-missing`, then add focused offline/mock-based tests following established per-module patterns.

## Session environment
- Python 3.14.4, pytest 9.2.0, ruff 0.17.4, mypy 2.4.1, Click 8.1.8.

## One precise next task
Pick ONE remaining <100% module (suggest `subtake.py`, missing 642-643), reproduce its exact uncovered lines, then add focused offline/mock-based tests to close them. Do not batch modules; verify per module with coverage + pytest + mypy + ruff before moving on. If no coverage work is desired, there is no pending task.

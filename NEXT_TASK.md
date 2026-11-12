# Next Task

## Status
Repository is fully green: `python -m pytest -q` → 6070 passed, 53 skipped, 0 failed; `python -m mypy ethscan/ tests/` → clean (187 source files); `python -m ruff check ethscan/ tests/` → all checks passed.

`ethscan/wifi.py`, `ethscan/mongodb.py`, `ethscan/dnssec.py`, `ethscan/ntp.py`, `ethscan/trace.py`, `ethscan/s3.py`, `ethscan/mssql.py`, `ethscan/mysql.py`, and `ethscan/postgresql.py` are now 100% coverage. Every `ethscan/` module is now ≥98%.

## Remaining <100% modules (1-5 defensive lines each)
cli.py (567-569, 770, 797, 863, 902, 4278, 4353, 4426, 4499, 5380, 5518, 5591, 5650-5651, 5656-5657, 5661), redis.py (394, 447), smb.py (819, 892), smtp.py (409, 460), snmp.py (611, 706), subtake.py (642-643), ldap.py (667, 740), oracle.py (475, 511).

TOTAL miss: 33.

Most are network-probe error branches or hard-to-trigger defensive guards (e.g. cleanup `except OSError: pass`). Reproduce exact uncovered lines first via `python -m pytest -q --cov=ethscan --cov-report=term-missing`, then add focused offline/mock-based tests following the fileio.py (session 83), vuln.py (session 84), ftp.py (session 85), dns.py (session 86), whois.py (session 87), mac.py (session 88), wifi.py (session 89), mongodb.py (session 90), dnssec.py (session 91), ntp.py (session 92), trace.py (session 93), s3.py (session 94), mssql.py (session 95), mysql.py (session 96), and postgresql.py (session 97) patterns.

## Session environment
- Python 3.14.4, pytest 9.2.0, ruff 0.17.4, mypy 2.4.1, Click 8.1.8.

## One precise next task (if further coverage work is desired)
Pick ONE remaining <100% module, reproduce its exact uncovered lines, then add focused offline/mock-based tests to close them. Do not batch modules; verify per module with coverage + pytest + mypy + ruff before moving on. If no coverage work is desired, there is no pending task — the repository is complete.
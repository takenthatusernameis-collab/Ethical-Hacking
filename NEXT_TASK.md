# Next Task

## Status
Repository is fully green: `python -m pytest -q` → 6023 passed, 53 skipped, 0 failed; `python -m mypy ethscan/ tests/` → clean (187 source files); `python -m ruff check ethscan/ tests/` → all checks passed.

`ethscan/fileio.py` is now 100% coverage (was 96%, missing lines 95, 170-171); it was the lowest module. Every `ethscan/` module is now ≥98%.

## Remaining <100% modules (1-4 defensive lines each)
dns.py (218, 254), ftp.py (231, 275), whois.py (279, 350), mac.py (311, 354), mongodb.py (260, 333, 382), geo.py (292, 455), recon.py (177, 236-239), mysql.py (352, 426, 477), postgresql.py (385, 445), subtake.py (642-643), s3.py (211, 312-313, 367-368), memcached.py (322, 390), oracle.py (475, 511), trace.py (354, 382, 443), wifi.py (368, 384), ntp.py (368, 468), redis.py (394, 447), smtp.py (409, 460).

Most are network-probe error branches or hard-to-trigger defensive guards (e.g. cleanup `except OSError: pass`). Reproduce exact uncovered lines first via `python -m coverage report --include="ethscan/*" -m`, then add focused offline/mock-based tests following the fileio.py pattern (session 83).

## Session environment
- Python 3.14.4, pytest 9.2.0, ruff 0.17.4, mypy 2.4.1, Click 8.1.8.

## One precise next task (if further coverage work is desired)
Pick ONE remaining <100% module, reproduce its exact uncovered lines, then add focused offline/mock-based tests to close them. Do not batch modules; verify per module with coverage + pytest + mypy + ruff before moving on. If no coverage work is desired, there is no pending task — the repository is complete.

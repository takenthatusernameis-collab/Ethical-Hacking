What changed:
- Added 7 targeted unit tests to `tests/test_service.py` achieving 100% coverage for `ethscan/service.py`. Tests cover previously uncovered branches in `grab_banner`: successful banner recv + signature match (FTP), no-signature fallback to `service_name.upper()`, HTTP/HTTPS HEAD fallback when initial banner is empty, OSError during HTTP fallback recv, capture-group signature match (Apache Server header), and OSError during initial banner recv. All use `monkeypatch` on `socket.create_connection` with lightweight fake sockets — no real network or threads.

What was verified:
- `python -m pytest tests/test_service.py --cov=ethscan.service --cov-report=term-missing` → 23 passed, 101/101 (100%).
- `python -m pytest --cov=ethscan --cov-report=term-missing -q` → 3859 passed, 1 skipped (up from 3853). Overall missing statements down from 109 to 106.
- `python -m ruff check tests/test_service.py` → no new errors introduced (3 pre-existing baseline errors in this file remain unchanged).

What remains unresolved:
- Overall missing statements: 106. Remaining gaps by module: vuln.py 9, radix.py 9, s3.py 6, snmp.py 5, resolve.py 4, ssl.py 4, postgresql.py 1, smtp.py 1, redis.py 2, dnssec.py 6, ftp.py 2, hash.py 5, mongodb.py 2, mssql.py 8, mysql.py 3, netbios.py 10, ntp.py 1, oracle.py 2, main.py 1. Some are defensive/rare branches.

Which approaches failed and why:
- First attempt used real threaded TCP servers but hit a deadlock: server did `recv` before client, so client's banner `recv` returned empty. Switched to `monkeypatch`-based fake sockets with deterministic `recv` sequencing — reliable and fast.
- Initial assertions on service names were wrong because earlier signatures in the list match first (e.g. "ProFTPD" matches the generic "FTP" pattern; "HTTP/1.1 200 OK" matches before the `Server:` capture-group pattern). Adjusted expectations to match actual matching order.

Next task:
- Continue improving coverage by tackling modules with smallest remaining gaps. Start with postgresql.py (1 missing, line 201), smtp.py (1 missing, line 222), redis.py (2 missing, lines 55-56) if feasible; otherwise ntp.py (1), mysql.py (3), oracle.py (2), ftp.py (2), mongodb.py (2). Add minimal targeted unit tests to corresponding test files without modifying `ethscan/`. Verify targeted tests pass, ruff on modified test files passes, and full suite remains green (≥3859 passed, 1 skipped). Prefer practical test cases over contrived ones for unreachable defensive code.
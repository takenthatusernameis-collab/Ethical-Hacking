# Next Task
Date: Fri Nov 20 2026 (session 33) — repository fully green; test fix completed.

## Status
- Green: **46710 passed, 146 skipped, 0 failed**; mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean; coverage 99% with only the documented `ethscan/cli.py` unreachable defensive guard uncovered.

## This session (what changed)
- Fixed `_extract_oui` test mismatch in `tests/test_mac.py`: 10 formatter tests incorrectly used `"001a2b3c"` (8 hex chars) but the function correctly returns `"001a2b"` (6 hex chars = 24-bit OUI). Updated all formatter tests to match the actual function behavior. The `run_mac` tests already expected the correct 6-char value.
- No production (`ethscan/`) code changes; purely test fixes, fully reversible.

## Verified (this session)
- `python -m pytest -q` -> 46710 passed, 146 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 99%; only `ethscan/cli.py` unreachable defensive guard uncovered (intentional).
- Reproduced mismatch: `_extract_oui("00:1A:2B:3C:4D:5E")` returns `'001a2b'` (6 hex chars); `run_mac` tests already correct; formatter tests now fixed.

## Known limitations (not in scope)
- `ethscan/cli.py` unreachable defensive guard (coverage intentionally not gamed).
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- PBKDF2 + NTLM intentionally unsupported.
- Remaining `AF_INET`-hardcoded UDP transports (`ldap`, `memcached`, `redis`, `smb`, `snmp`, `dnssec`, `osdetect`) accept IPv6 targets syntactically but cannot transport to them yet.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS; fake sockets only).
- Do not commit manually; the workflow controller commits and verifies pushes.
- Working tree has uncommitted changes (only `tests/test_mac.py` modified).

## Next task (for the next agent)
- Make the UDP transport family-aware for one of the remaining modules (`ldap`, `memcached`, `redis`, `smb`, `snmp`, `dnssec`, `osdetect`) so the now-correct IPv6 target parsing is usable. Evidence: `python -m ethscan ntp --target ::1` works (fixed in session 12), but `python -m ethscan ldap --target ::1` fails with `[Errno -9] Address family for hostname not supported`. Pick one module, reproduce the failure, resolve with `socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)`, keep the `connector` seam, add monkeypatched deterministic tests asserting `AF_INET6` for `::1` and `AF_INET` for IPv4, maintain 100% branch coverage, and re-run all gates. Do not change the target-parsing contract.
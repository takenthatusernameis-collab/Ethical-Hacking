# Handoff
Date: Sun Nov 22 2026

## State
- HEAD: `683d33e` (main). Working tree: dirty with the completed, verified UDP-IPv6 fix (uncommitted; the controller commits).
- The commits `9daf1ca`..`683d33e` ahead of real work were control-marker-only (handoff-doc edits); this session made the first real source/test change since `c17edb3` (mac URL fix, session 1 Nov 21).

## What changed this session
- `ethscan/scanner.py` (`scan_udp_port`): now resolves the endpoint via `socket.getaddrinfo(host, port, type=SOCK_DGRAM, proto=IPPROTO_UDP)` and opens `socket.socket(family, socktype, proto)` from the first result, then `sendto(b"", sockaddr)`. Previously it hardcoded `socket.AF_INET`, so an IPv6 target raised `gaierror [Errno -9]` that was swallowed and reported as a CLOSED port (silent false negative). Mirrors the established `ntp`/`netbios` family-aware pattern.
- `tests/test_scanner.py` (+3): deterministic IPv6/IPv4 family-selection tests (monkeypatched `getaddrinfo`+`socket.socket` recorders) and a real loopback IPv6 UDP regression (skips if IPv6 unavailable).

## What was actually verified this session (fresh evidence)
- Repro before fix: `scan_udp_port("::1", <live v6 UDP>)` → `(port, False)`; CLI `scan --target ::1 --protocol udp` → `open_ports: []`. After fix: `(port, True)` and `open_ports: [<port>]`, exit 0.
- `scan --protocol both` over IPv6 → `[(port,'tcp',False),(port,'udp',True)]` (correct).
- `python -m pytest tests/test_scanner.py -q` → 62 passed, 1 skipped.
- `python -m pytest -q` → **46770 passed, 147 skipped, 0 failed** (baseline 46767; +3).
- `python -m mypy ethscan/ tests/` → Success (268 source files).
- `python -m ruff check ethscan/ tests/ check_readme.py` → All checks passed.
- `python3 check_readme.py` → 54 commands, 0 drift; `git diff --check` clean.
- Full-suite branch coverage: `ethscan/scanner.py` 100% (205 stmts / 80 branches / 0 miss); TOTAL 100% (16119 stmts / 6080 branches / 0 miss).
- `git status` → only `ethscan/scanner.py` + `tests/test_scanner.py` modified.

## What remains unresolved
- Nothing functional from this session. Known limitations unchanged: `ethscan/cli.py:4318` is a documented unreachable defensive guard (uncovered); `oracle`/`postgresql` keep the in-band exit-0 empty-target contract (out of scope); PBKDF2+NTLM intentionally unsupported.
- `scanner.py` was the last hardcoded-`AF_INET` UDP socket. Remaining `AF_INET` occurrences are `getaddrinfo` name-resolution hints in `resolve.py:67`, `dns.py:58`, `stale.py:53/99`, `subtake.py:317/352` — intentionally IPv4-resolution, not sockets; not individually re-audited this session.

## Approaches already failed / why
- Adding an `if not infos` guard after `getaddrinfo`: rejected as unreachable (would break 100% branch coverage); `infos[0]` on empty raises `IndexError` already caught by the outer `except Exception`.
- Iterating all `getaddrinfo` families: rejected as unnecessary complexity; first result matches sibling modules.

## Next task
- Add an end-to-end CLI regression test that `ethscan scan --target ::1 --protocol udp` reports a live IPv6 UDP service as open (mirror `test_scan_udp_port_ipv6_loopback_open_is_detected` through the CLI, with a skip guard when IPv6 loopback is unavailable). Evidence: pre-fix CLI `open_ports: []` vs post-fix `[<port>]`; `tests/test_cli.py` UDP tests monkeypatch `scan_udp_ports` and never exercise a real IPv6 transport. Constraints: skip when `not socket.has_ipv6` or bind raises; keep deterministic; re-run the full gate. Do not touch `oracle`/`postgresql` empty-target handling.

## Environment/notes
- Python 3.14.4; pytest 9.2.0; mypy 2.4.1; ruff 0.17.6; coverage 7.17.4 via `python -m coverage`.
- Do not commit manually unless explicitly asked; the workflow controller stages and commits.
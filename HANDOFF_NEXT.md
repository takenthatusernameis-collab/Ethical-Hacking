# Handoff
Date: Fri Nov 20 2026 (session 28)

## State at HEAD (controller will stage/commit; working tree has the changes below)
- `pytest -q` -> **46693 passed, 146 skipped, 0 failed** (baseline 46689 + 4 new tests).
- `python -m mypy ethscan/ tests/` -> Success: no issues in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; `git diff --check` clean.
- Coverage: `ethscan/ping.py` **100%** (0 missing / 0 partial); project 99% with only the documented `ethscan/cli.py:4336` unreachable guard.

## What changed
- Fixed an evidenced IPv6 bug in `ethscan/ping.py`: raw ICMP sockets are IPv4-only (`AF_INET`/`IPPROTO_ICMP`), so a root user pinging an IPv6 target got every probe failing with `[Errno -9] Address family for hostname not supported` and no fallback.
  - `probe_icmp`: the raw path is used only when `resolved_family != socket.AF_INET6`; IPv6 targets use the existing family-aware TCP connect fallback.
  - `run_ping`: for an IPv6 target it closes its own raw socket (never a caller-injected one), sets `raw_socket=None`, reports `raw_socket_available: False`, and adds a note that raw ICMP is IPv4-only and TCP fallback is used.
- Added 4 deterministic tests in `tests/test_ping.py` (IPv6 fallback despite raw socket; IPv4 raw path unchanged; owned raw socket closed; caller-owned raw socket not closed).
- No change to IPv4 ping behavior, TTL options, formatters, README, or exit codes.

## Reproduction evidence (pre-fix)
- Emulating a successful raw-socket creation plus an `AF_INET` `sendto` to `::1`:
  `run_ping("::1", count=1)` -> `raw_socket_available: True`, `response_type: NO-RESPONSE`,
  `error: [Errno -9] Address family for hostname not supported`.
- Post-fix, same script -> `raw_socket_available: False`, `response_type: RST`, `error: None`.
- CLI smoke (unprivileged): `python -m ethscan ping --target ::1 --count 1 --timeout 0.3 --format json` -> `response_type: RST`, exit 0.

## What was actually verified
- Focused: `pytest tests/test_ping.py -q` -> 68 passed.
- Full suite: 46693 passed, 146 skipped, 0 failed.
- mypy clean (267 files); ruff clean; README sync 54/54; whitespace clean.
- Full-suite branch coverage confirms `ping.py` at 100%.

## Unresolved / known limitations
- IPv6 targets use TCP-connect ping, not real ICMPv6 (documented in the run note). Real ICMPv6 is the natural follow-up.
- `ethscan/cli.py:4336` unreachable defensive guard: deliberately left uncovered; do not remove or game coverage.
- `oracle` / `postgresql` empty-target handling: in-band "probe failed" (exit 0) by documented contract.
- PBKDF2 + NTLM: intentionally unsupported.

## Approaches already tried / ruled out
- Assuming `AF_INET` raw ICMP can send to an IPv6 literal: disproved by the reproduction above.
- Silently ignoring the raw socket without reporting it: rejected; `raw_socket_available` and the notes must stay truthful, so the socket is dropped and the fallback is announced.

## Next task (for the next agent)
- Implement real ICMPv6 ping in `ethscan/ping.py` as a bounded follow-up: create `socket.AF_INET6`/`IPPROTO_ICMPV6` raw sockets, build Echo Request (type 128) and parse Echo Reply (type 129) with the IPv6 pseudo-header checksum, extend `_try_create_raw_socket` to be family-aware, and keep the TCP fallback when raw sockets are unavailable. Reproduce first with a fake raw socket (no root needed), keep `raw_socket_available` accurate for both families, keep `ping.py` at 100% branch coverage, and re-run pytest/mypy/ruff/check_readme. Do not remove the IPv4 raw path or change exit-code contracts.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.6; coverage 7.17.3.
- Do not commit manually: the workflow controller stages/commits/pushes.

# Next Task

None pending from current evidence. Repository is fully green:

- `pytest -q` -> 46744 passed, 146 skipped, 0 failed
- `mypy ethscan/ tests/` -> Success (267 source files)
- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift
- `coverage` -> 100% statement/branch on every module (including cli.py)

## Suggested bounded follow-up (only if new work is requested)

Implement real ICMPv6 raw ping in `ethscan/ping.py`: create `socket.AF_INET6`/`IPPROTO_ICMPV6` raw sockets, build/parse Echo Request/Reply (type 128/129) with the IPv6 pseudo-header checksum, and keep the existing TCP fallback for unprivileged users. Reproduce first with a fake raw socket; keep `raw_socket_available` accurate for both families and `ping.py` at 100% branch coverage. Do not remove the IPv4 raw path or change exit-code contracts.

`oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error) per their documented contract.

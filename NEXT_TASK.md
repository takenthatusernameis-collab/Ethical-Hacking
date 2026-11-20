# Next Task
Date: Fri Nov 20 2026 (session 25) — COMPLETED this session.

## Status
- Green: **46689 passed, 146 skipped, 0 failed** (baseline unchanged vs session 24); mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean; working tree clean.

## This session (what changed)
- Fixed 2 stale test assertions in `tests/test_mac.py` (`test_run_mac_success`, `test_run_mac_url_target`) that asserted `"oui": "001a2b3c"` (8 chars).
- Reproduced the defect first: `ethscan/mac.py::_extract_oui` returns `cleaned[:6]`, a correct 6-char 24-bit OUI matching its docstring ("24-bit OUI, first 3 octets") and the networking OUI standard. The 2 `run_mac` tests codified incorrect 8-char behavior and failed with `assert '001a2b' == '001a2b3c'`.
- Updated the 2 assertions to `"oui": "001a2b"` so tests match the correct implementation. No production code changed; purely test correction, fully reversible.

## Verified (this session)
- `tests/test_mac.py` -> 78 passed (was 2 failed / 76 passed).
- `pytest -q` -> 46689 passed, 146 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.

## Known limitations (not in scope)
- `ethscan/cli.py` unreachable defensive guard (coverage intentionally not gamed).
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- `ethscan/ping.py` raw IPv4 ICMP/stream sockets need ICMPv6/checksum support (privileged, larger change).
- `ethscan/dns.py`/`resolve.py`/`stale.py`/`subtake.py` A-record `getaddrinfo(..., AF_INET)` treated as intentional IPv4-only semantics.
- PBKDF2 + NTLM intentionally unsupported.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS).
- Do not commit manually; the workflow controller commits and verifies pushes.

## Next task (for the next agent)
- None pending. Repository is fully green with all gates passing. If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

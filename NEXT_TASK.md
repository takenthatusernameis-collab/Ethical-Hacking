# Next Task
Date: Thu Nov 19 2026 (session 17)

## Status
- Green: 39925 passed, 146 skipped, 0 failed; mypy Success (262 source
  files); `ruff check ethscan tests` clean; README 54/54 with 0 drift both
  directions; `git diff --check` clean.
- Uncommitted at handoff: controller will stage/commit
  `ethscan/trace.py`, `ethscan/mac.py`, `tests/test_trace.py`,
  `tests/test_trace_branch_gaps.py`,
  `tests/test_cli_trace_brute_unreachable_sweep.py`,
  `HANDOFF_NEXT.md`, `NEXT_TASK.md`.

## This session (what changed)
1. Confirmed the prior handoff's requested work (family-aware IPv6 TCP
   transport in `ethscan/trace.py`) was complete and tested at HEAD; no
   changes needed there.
2. Doc-accuracy fix on `ethscan/mac.py:_extract_oui`: the docstring said
   "24-bit OUI" but the code returns `cleaned[:8]` = 8 hex chars = a 32-bit
   prefix (first 4 octets), and every test codifies `"001a2b3c"`. Corrected the
   docstring to "Extract the first 8 hex characters (32-bit prefix, first 4
   octets) from a MAC address." No output or test change — behavior unchanged.

## Verified
- Focused: `tests/test_trace.py` + branch-gaps + CLI sweep -> 73 passed;
  `tests/test_mac.py` + hostile sweeps -> 169 passed (_extract_oui output
  unchanged).
- Full: `python -m pytest -q` -> 39925 passed, 146 skipped, 0 failed
  (baseline unchanged).
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 262 source
  files; `python -m ruff check ethscan/ tests/` -> all checks passed;
  `python3 check_readme.py` -> 54/54, 0 drift both directions.
- Note: `pytest-cov`/`coverage` are NOT installed in this environment; do not
  rely on `--cov`.

## Next task (precise)
- None pending. Repository is fully green with all known limitations resolved
  or explicitly out of scope. If future work is needed, pick a single bounded,
  high-value, verifiable improvement and reproduce it first — do not speculate
  or weaken safety controls. `oracle`/`postgresql` empty-target handling
  remains intentionally out of scope per their documented contract (exit 0,
  in-band error).

## Known limitations (not in scope)
- `ethscan/ping.py` raw IPv4 ICMP/stream sockets need ICMPv6/checksum support
  (privileged, larger change) — do not touch in this task.
- `ethscan/dns.py`, `resolve.py`, `stale.py`, `subtake.py` use
  `getaddrinfo(..., AF_INET)` for A-record/canonical-name lookups; treat as
  intentional unless evidence says otherwise.
- `ethscan/cli.py:4318` documented unreachable guard.
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- PBKDF2 + NTLM intentionally unsupported.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS).
- Do not commit manually; the workflow controller commits and verifies pushes.

# Next Task
Date: Fri Nov 20 2026 (session 24) — COMPLETED this session.

## Status
- Green: **46689 passed, 146 skipped, 0 failed** (baseline 46683; +6 new tests); mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean; working tree has only `tests/test_readme_examples.py` modified (controller stages/commits).
- Full-suite branch coverage (`coverage run --branch --source=ethscan -m pytest -q`): every module 100% except the known unreachable `ethscan/cli.py:4336` guard (`raise click.UsageError("Shell argument is required when not using --install")`); TOTAL 15942 stmts, 1 miss, 6020 branch, 1 BrPart. No new coverage gap.

## This session (what changed)
- Executed a bounded documentation-test sync task: added 6 new tests to `tests/test_readme_examples.py` for the remaining documented README console examples (lines 179-240, 264-285) so documented error text cannot drift:
  1. `web --target "host:notaport"` (invalid port)
  2. `web --target "host name"` (host with space)
  3. `web --target "https://example.com/a b"` (path with space)
  4. `trace --target ""` (empty target)
  5. `s3 --target ""` (empty target)
  6. `redis --target ""` (empty target)
- Each example was reproduced by hand against the live CLI before writing the assertions; all matched README exactly. CliRunner uses prog name `cli`, so Usage/Try lines carry `cli` while Error text matches README verbatim.
- No source (`ethscan/`) changes; purely a test addition, fully reversible. Total tests in `test_readme_examples.py`: 12 (covering all 12 error examples in README.md lines 115-285).

## Verified (this session)
- `pytest tests/test_readme_examples.py -q` -> 12 passed.
- `pytest -q` -> 46689 passed, 146 skipped, 0 failed.
- `python -m mypy ethscan/ tests/` -> Success: no issues found in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions.
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 99%; only `ethscan/cli.py:4336` (known unreachable defensive guard) uncovered; all other modules 100%.

## Known limitations (not in scope)
- `ethscan/cli.py:4336` documented unreachable defensive guard (coverage intentionally not gamed).
- `oracle`/`postgresql` report unusable targets in-band (exit 0) by contract.
- `ethscan/ping.py` raw IPv4 ICMP/stream sockets need ICMPv6/checksum support (privileged, larger change).
- `ethscan/dns.py`/`resolve.py`/`stale.py`/`subtake.py` A-record `getaddrinfo(..., AF_INET)` treated as intentional IPv4-only semantics.
- PBKDF2 + NTLM intentionally unsupported.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic (no real network/DNS).
- Do not commit manually; the workflow controller commits and verifies pushes.

## Next task (for the next agent)
- None pending. Repository is fully green with all documented error examples now covered by regression tests. If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).
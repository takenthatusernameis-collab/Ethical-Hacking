# Next Task
Date: Thu Nov 19 2026 (session 23) — COMPLETED this session.

## Status
- Green: **46683 passed, 146 skipped, 0 failed** (baseline 46677; +6 new tests); mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean; working tree has only `tests/test_readme_examples.py` untracked (controller stages/commits).
- Full-suite branch coverage (`coverage run --branch --source=ethscan -m pytest -q`): every module 100% except the known unreachable `ethscan/cli.py:4336` guard (`raise click.UsageError("Shell argument is required when not using --install")`); TOTAL 15942 stmts, 1 miss, 6020 branch, 1 BrPart. No new coverage gap.

## This session (what changed)
- Executed the pending assignment: added `tests/test_readme_examples.py` (6 offline `CliRunner` regression tests) encoding the documented README console examples so documented error text cannot drift:
  - `scan --target 127.0.0.1 --ports abc`
  - `cidr --cidr bogus`
  - `radix --cidrs 192.168.1.0/24,2001:db8::/32`
  - `vuln --target example.com --services-file <tmp_path>/broken.json` (broken JSON)
  - `redis --target example.com:99999`
  - `audit --file <tmp_path>/passwords.txt` (non-UTF-8)
  - Each asserts exit code 2 plus the `Usage: cli <cmd> [OPTIONS]`, `Try 'cli <cmd> --help' for help.` and exact `Error:` text from README.md lines 115-285. (`s3 --target "[::1]:443"` left out per the constraint — its probe may resolve DNS and is not deterministic/offline.)
- Each example was reproduced by hand against the live CLI before writing the assertions; all matched README exactly. CliRunner uses prog name `cli`, so Usage/Try lines carry `cli` while Error text matches README verbatim.
- No source (`ethscan/`) changes; purely a test addition, fully reversible.

## Verified (this session)
- `pytest tests/test_readme_examples.py -q` -> 6 passed.
- `pytest -q` -> 46683 passed, 146 skipped, 0 failed.
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
- None pending. Repository is fully green. If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

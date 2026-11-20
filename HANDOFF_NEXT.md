# Handoff
Date: Fri Nov 20 2026 (session 24)

## State at HEAD (working tree has the addition below; controller will stage/commit)
- `pytest -q` -> **46689 passed, 146 skipped, 0 failed** (session baseline 46683; +6 tests).
- `python -m mypy ethscan/ tests/` -> Success: no issues in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; `git diff --check` clean.
- Full-suite branch coverage (`coverage run --branch --source=ethscan -m pytest -q`): `ethscan/cli.py` 1856 stmts, 1 miss, 624 branch, 1 BrPart — the single miss is the known unreachable defensive guard at line `4336`. No new coverage gap. All other modules 100%.

## What changed
- Extended `tests/test_readme_examples.py` with 6 new tests (total 12): offline `CliRunner` regression tests for all documented README console examples (lines 115-285), asserting exit code 2 plus the exact `Usage:` / `Try ... --help` / `Error:` text:
  - `scan --target 127.0.0.1 --ports abc`
  - `cidr --cidr bogus`
  - `radix --cidrs 192.168.1.0/24,2001:db8::/32`
  - `vuln --target example.com --services-file broken.json` (broken JSON via `tmp_path`)
  - `redis --target example.com:99999`
  - `audit --file passwords.txt` (non-UTF-8 via `tmp_path`)
  - `web --target "host:notaport"` (invalid port)
  - `web --target "host name"` (host with space)
  - `web --target "https://example.com/a b"` (path with space)
  - `trace --target ""` (empty target)
  - `s3 --target ""` (empty target)
  - `redis --target ""` (empty target)
- `s3 --target "[::1]:443"` deliberately left out (probe may resolve DNS; not deterministic/offline).
- Each example was reproduced against the live CLI first; all matched README exactly. CliRunner prog name is `cli` (Usage/Try lines carry `cli`); Error text matches README verbatim.
- No production code changed; purely a test addition, fully reversible. Only `tests/test_readme_examples.py` is modified.

## What was actually verified
- New tests: 6 passed (total 12 in file).
- Full suite -> 46689 passed, 146 skipped, 0 failed; mypy/ruff/check_readme clean; coverage unchanged apart from the known guard (`cli.py:4336`).

## Unresolved / known limitations (all explicitly out of scope)
- `ethscan/cli.py:4336` unreachable defensive guard (`raise click.UsageError("Shell argument is required when not using --install")`): deliberately left uncovered; do not remove or game coverage.
- `oracle` / `postgresql` empty-target handling: in-band "probe failed" (exit 0) by documented contract.
- PBKDF2 + NTLM: intentionally unsupported.
- `ping.py` IPv6: raw AF_INET ICMP sockets; ICMPv6/checksum support is a larger privileged change.
- `ethscan/dns.py`/`resolve.py`/`stale.py`/`subtake.py` A-record `getaddrinfo(..., AF_INET)` treated as intentional IPv4-only semantics.

## Approaches already tried / ruled out
- None new this session; the task was a straightforward test addition with no competing approaches.

## Next task (for the next agent)
- None pending. Repository is fully green with all documented error examples now covered by regression tests. If future work is needed, pick a single bounded, high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.6; coverage 7.17.3 (`python -m coverage run --branch --source=ethscan -m pytest -q`, then `python -m coverage report --show-missing`).
- Do not commit manually: the workflow controller stages/commits/pushes.
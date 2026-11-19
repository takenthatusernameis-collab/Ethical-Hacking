# Next Task
Date: Thu Nov 19 2026 (session 23)

## Status
- Green: **46677 passed, 146 skipped, 0 failed**; mypy Success (266 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean.
- Full-suite branch coverage: every module 100% except the known unreachable `ethscan/cli.py:4336` guard.

## This session (what changed)
- Fixed a reproducible docs/behavior mismatch: a `TargetSpecError` raised from a command callback was translated to `click.BadParameter` in `_TargetGroup.invoke` without a context, so click printed only `Error: ...`. The README (lines 115-285) documents the full usage error (`Usage:` + `Try ... --help`).
  - `ethscan/cli.py`: added `_TargetCommand(click.Command)` whose `invoke` catches `TargetSpecError`, attaches the sub-command `ctx` to the `BadParameter`, and re-raises; set `_TargetGroup.command_class = _TargetCommand`; removed the now-redundant group-level catch (it would be uncovered dead code).
  - `tests/test_cli.py`: +1 test asserting usage/hint/error lines for `redis`, `web`, `trace`, `s3`.

## Verified (this session)
- Before: `python -m ethscan redis --target ""` printed only the `Error:` line (no `Usage:` / `Try:`).
- After: prints `Usage: python -m ethscan redis [OPTIONS]`, `Try 'python -m ethscan redis --help' for help.`, blank line, `Error: Invalid value for '--target': Could not parse host from target ''`; same for `web`/`trace`/`s3` and the other target commands. Exit code remains 2.
- `pytest tests/test_cli.py -k "invalid_target or target"` -> 146 passed.
- `pytest -q` -> 46677 passed, 146 skipped, 0 failed.
- mypy/ruff/check_readme/`git diff --check` all clean.
- Coverage: `ethscan/cli.py` 1856 stmts, 1 miss, 624 branch, 1 BrPart — only the known unreachable guard (now line 4336).

## Next task (precise)
- Add `tests/test_readme_examples.py` with offline `CliRunner` regression tests for the remaining documented examples so the text cannot drift:
  `scan --target 127.0.0.1 --ports abc`, `cidr --cidr bogus`, `radix --cidrs 192.168.1.0/24,2001:db8::/32`, `vuln --target example.com --services-file broken.json` (broken JSON via `tmp_path`), `redis --target example.com:99999`, and `audit --file passwords.txt` (non-UTF-8 file via `tmp_path`).
  Assert exit code 2 and the exact `Usage:` / `Try ... --help` / `Error:` text from `README.md` lines 115-285. Skip `s3 --target "[::1]:443"` unless the probe can be made offline/deterministic.
- If a test reveals a real mismatch, fix the smallest side (behavior or README) and record it. Re-run pytest/mypy/ruff/check_readme and full-suite branch coverage afterward; keep all modules 100% except `cli.py:4336`.

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

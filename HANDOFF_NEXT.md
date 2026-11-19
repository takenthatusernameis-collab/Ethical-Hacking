# Handoff
Date: Thu Nov 19 2026 (session 23)

## State at HEAD (working tree has the fix below; controller will stage/commit)
- `pytest -q` -> **46677 passed, 146 skipped, 0 failed** (session-22 baseline 46676; +1 test).
- `python -m mypy ethscan/ tests/` -> Success: no issues in 266 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> all checks passed.
- `python3 check_readme.py` -> 54 commands, 0 drift both directions; `git diff --check` clean.
- Full-suite branch coverage (`coverage run --branch --source=ethscan -m pytest -q`): `ethscan/cli.py` 1856 stmts, 1 miss, 624 branch, 1 BrPart — the single miss is the same known unreachable defensive guard, now at line `4336` (was 4318; the +18 shift is this session's added class). No new coverage gap.

## What changed
- `ethscan/cli.py`: target usage errors now carry the sub-command context.
  - Added `_TargetCommand(click.Command)`: its `invoke` catches `TargetSpecError`, builds `_invalid_target(exc)`, sets `error.ctx = ctx`, and re-raises. Click's `UsageError.show()` prints `Usage:` and the `Try '<prog> <cmd> --help'` hint only when `ctx` is set, so this restores the documented output.
  - Set `command_class = _TargetCommand` on `_TargetGroup`; this automatically covers every command created by the group, including any added later.
  - Removed the old `_TargetGroup.invoke` catch: `TargetSpecError` is only raised from command callbacks (`_validate_enum_target` or module helpers), so the group-level catch was redundant after the command-level fix and would have left an uncovered line. Updated the class docstring accordingly.
- `tests/test_cli.py` (+1 test): `test_invalid_target_usage_error_includes_usage_and_help_hint` asserts exit 2 plus the `Usage: cli <cmd> [OPTIONS]`, `Try 'cli <cmd> --help' for help.` and `Error: Invalid value for '--target':` lines for `redis`, `web`, `trace`, `s3`.

## What was actually verified
- Reproduced the defect first (README docs vs real output). README lines 150-280 document full click usage errors for an unusable `--target`, e.g.:
  - Before: `python -m ethscan redis --target ""` -> stderr was only
    `Error: Invalid value for '--target': Could not parse host from target ''` (no `Usage:` / `Try:` lines), while `scan --ports abc` did show them.
  - Root cause: the `TargetSpecError -> BadParameter` translation happened in `_TargetGroup.invoke`, after the sub-command's `augment_usage_errors` scope had exited, so `BadParameter.ctx` stayed `None`.
- After: `redis`/`web`/`trace`/`s3` (and the other target commands) print
  `Usage: python -m ethscan <cmd> [OPTIONS]`, `Try 'python -m ethscan <cmd> --help' for help.`, blank line, then the `Error:` line, exactly as documented.
- Focused: `pytest tests/test_cli.py -k "invalid_target or target"` -> 146 passed.
- Full suite -> 46677 passed, 146 skipped, 0 failed; mypy/ruff/check_readme/git-diff-check clean; cli.py coverage unchanged apart from the known guard.

## Unresolved / known limitations (all explicitly out of scope)
- `ethscan/cli.py:4336` unreachable defensive guard (`raise click.UsageError("Shell argument is required when not using --install")`): deliberately left uncovered; do not remove or game coverage.
- `oracle` / `postgresql` empty-target handling: in-band "probe failed" (exit 0) by documented contract.
- PBKDF2 + NTLM: intentionally unsupported.
- `ping.py` IPv6: raw AF_INET ICMP sockets; ICMPv6/checksum support is a larger privileged change.
- `ethscan/dns.py`/`resolve.py`/`stale.py`/`subtake.py` A-record `getaddrinfo(..., AF_INET)` treated as intentional IPv4-only semantics.

## Approaches already tried / ruled out
- Attaching the group context instead of the sub-command context: rejected — it would print the group usage (`python -m ethscan [OPTIONS] COMMAND ...`), not the documented per-command usage.
- Re-implementing `MultiCommand.invoke` to capture `sub_ctx`: rejected as duplicating click internals; `command_class` is the intended extension point.
- Keeping the group-level catch as a fallback: rejected — no in-scope path can raise `TargetSpecError` before a command callback, and it would leave an uncovered line (the repo keeps coverage exact except the known guard).

## Next task (for the next agent)
- Encode the remaining README `console` examples as offline `CliRunner` regression tests so documented error text cannot drift again. Evidence: this session found one such drift by running the examples by hand (`README.md` lines 115-285); the other documented offline cases were spot-checked and currently match.
  - Add `tests/test_readme_examples.py` asserting exact stderr/output and exit code 2 for: `scan --target 127.0.0.1 --ports abc`, `cidr --cidr bogus`, `radix --cidrs 192.168.1.0/24,2001:db8::/32`, `vuln --target example.com --services-file broken.json` (create the broken file with `tmp_path`), `redis --target example.com:99999`, and `audit --file passwords.txt` with a non-UTF-8 file (create with `tmp_path`). Keep `s3 --target "[::1]:443"` out unless its probe can be made deterministic/offline (it may resolve DNS).
  - Constraints: no network/DNS; no source changes unless a test reveals a real mismatch (then make the smallest fix and document it); rerun pytest/mypy/ruff/check_readme and full-suite branch coverage; keep all modules 100% except `cli.py:4336`.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.6; coverage 7.17.3 (`python -m coverage run --branch --source=ethscan -m pytest -q`, then `python -m coverage report --show-missing`).
- Do not commit manually: the workflow controller stages/commits/pushes.

(End of file)

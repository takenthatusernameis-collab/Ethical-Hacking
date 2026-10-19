# NEXT_TASK.md

## Status (2026-10-19T16:05:00Z)
- Task from prior agent: add regression tests for the profile-explicitness behavior — done (18 new tests).
  While verifying them I found the `report` command still had the *unfixed* half of the profile bug, so I
  fixed that too (it was the exact case the prior agent had already prepared the plumbing for in
  `report.py` but never wired up).
- Current state: `scan`, `service`, `cve` and `report` all treat an explicitly supplied
  `--timeout`/`--workers` (CLI flag, env var, or config-file value) as overriding the profile defaults —
  including when the value happens to equal the option's built-in default.

## What changed
- `ethscan/cli.py`: `report` uses `ctx.get_parameter_source("timeout"/"workers")` and passes
  `timeout_explicit` / `workers_explicit` to `run_report()`.
- `ethscan/report.py`: `run_report()` gained the two optional flags and forwards them to
  `_resolve_ports_and_defaults`.
- `tests/test_cli.py` (+14), `tests/test_report.py` (+4): regression tests.

## Verification
- Full suite: 3954 passed, 1 skipped (baseline 3936 + 18 new). Lint output identical to baseline.
- Regression-catching proof: reintroducing the sentinel comparison fails 9 of the new CLI tests; reverting
  the source to `36f9f9e` fails the 3 new `report` tests.

## Next task (bounded, high-value)
**Make `service` and `cve` accept the `common` and `all` port keywords, like `scan` and `report` already do.**

Evidence (reproduced with mocked network, exit code 1 = unhandled `ValueError`, raw traceback):

| command                              | result                                              |
|--------------------------------------|-----------------------------------------------------|
| `scan --ports all`                   | exit=0                                              |
| `scan --ports common`                | exit=0                                              |
| `report --ports all`                 | exit=0                                              |
| `service --ports all`                | exit=1 `ValueError: Invalid port number 'all'`      |
| `service --ports common`             | exit=1 `ValueError: Invalid port number 'common'`   |
| `service --profile fast --ports common` | exit=1 `ValueError: Invalid port number 'common'` |
| `cve --ports all`                    | exit=1 `ValueError: Invalid port number 'all'`      |
| `cve --ports common`                 | exit=1 `ValueError: Invalid port number 'common'`   |
| `cve --profile fast --ports common`  | exit=1 `ValueError: Invalid port number 'common'`   |

Root cause: `ethscan/cli.py` `service` (~line 1605) and `cve` (~line 2769) call
`parse_port_range(ports)` directly, while `scan` (~line 414) and `report.py::_parse_ports` special-case
`"common"` / `"all"` first.

Scope guidance:
- The `service` / `cve` `--ports` help text currently does **not** mention the keywords
  (`"Ports to scan: comma-separated list/ranges ..."`), so supporting them is a small feature
  extension — update the help text to match `scan`/`report` if you add them.
- `scan` already has the reference implementation and tests to mirror:
  `tests/test_cli.py::test_scan_profile_with_all_ports_keyword` and
  `::test_scan_profile_ports_keyword_is_case_insensitive`.
- `ethscan/scanner.py` already provides `get_common_ports()` and `get_all_ports()`; the `service`/`cve`
  code just needs to use them, and the keywords should be case-insensitive to match `scan`.
- Keep the change small: a shared helper (e.g. in `ethscan/scanner.py`) used by `service`/`cve` is
  preferable to duplicating the branch three more times.
- Add tests in `tests/test_cli.py` for `service` and `cve` (both with and without `--profile`), plus a
  `tests/test_report.py`-style unit test if a helper is introduced.

Alternative smaller next task (if the keyword extension is judged out of scope): convert the unhandled
`ValueError` from `parse_port_range` into a clean Click usage error (exit code 2 + message) in
`service`/`cve`, so a bad `--ports` value no longer surfaces as a raw traceback. That alone is a
user-facing improvement but does not make the keywords work.

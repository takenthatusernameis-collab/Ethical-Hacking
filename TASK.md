# Task

Date: 2026-10-19T16:05:00Z
Status: Profile-explicitness regression tests added; `report` profile bug fixed and covered; handoff prepared.

## What changed
- `ethscan/cli.py`: the `report` command now detects explicit `--timeout`/`--workers` via Click's
  `ParameterSource` (COMMANDLINE / ENVIRONMENT / DEFAULT_MAP) and forwards that to `run_report()`,
  matching the `scan`/`service`/`cve` fix. Previously `report` still compared the values against the
  sentinel defaults (`1.0` / `100`), so an explicit `report --profile fast --timeout 1.0` or
  `--workers 100` was silently replaced by the profile's `0.5` / `200`.
- `ethscan/report.py`: `run_report()` accepts optional `timeout_explicit` / `workers_explicit` flags and
  forwards them to `_resolve_ports_and_defaults` (whose support for them already existed but was
  unreachable from the CLI). Defaults to `None` = legacy sentinel behaviour, so direct API callers are
  unaffected.
- `tests/test_cli.py` (14 new tests) and `tests/test_report.py` (4 new tests): regression coverage for the
  profile-explicitness contract across `scan`, `service`, `cve` and `report`.

## Verification
- Full suite: 3954 passed, 1 skipped (baseline was 3936 passed, 1 skipped -> exactly the 18 new tests).
- Lint: `ruff check ethscan tests` output byte-identical to the pre-change baseline (48 pre-existing
  errors, no new ones).
- New tests proven to catch the regression: reintroducing the old sentinel comparison in `cli.py` made
  9 of the new `scan`/`service`/`cve` tests fail; reverting the source to the previous commit made the 3
  new `report` tests fail. All pass with the fix in place.
- Manual check of the README's documented config example (`timeout: 1.0` / `workers: 100`): config
  values now survive `--profile fast`, matching "CLI arguments always take precedence over config values".

## Next
See HANDOFF_NEXT.md and NEXT_TASK.md for the next bounded task and the evidence behind it.

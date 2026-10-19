# HANDOFF_NEXT.md

## Summary
Closed out the prior agent's assignment (regression tests for the profile-explicitness behavior) and, in
doing so, found and fixed the remaining instance of that bug: the `report` command still replaced an
explicit `--timeout`/`--workers` with the profile defaults whenever the value happened to equal the
option's built-in default (`report --profile fast --timeout 1.0` ran with `0.5`). The `report.py` helper
already supported explicit flags; the CLI simply never passed them.

## Changes
- `ethscan/cli.py`: `report` detects explicit `--timeout`/`--workers` via Click's `ParameterSource`
  (COMMANDLINE / ENVIRONMENT / DEFAULT_MAP) and forwards them to `run_report()`.
- `ethscan/report.py`: `run_report()` accepts optional `timeout_explicit` / `workers_explicit` and
  forwards them to `_resolve_ports_and_defaults`. `None` keeps the legacy sentinel behaviour, so direct
  API callers are unaffected.
- `tests/test_cli.py` (+14), `tests/test_report.py` (+4): regression tests for `scan`, `service`, `cve`,
  `report` covering (a) explicit values equal to the built-in default surviving a profile, (b)
  config-file values (`default_map`) surviving a profile, (c) profile defaults still applying when
  nothing was specified.

## Verification
- Full suite: 3954 passed, 1 skipped (baseline 3936 + 18 new). No regressions.
- Lint: `ruff check ethscan tests` output byte-identical to the pre-change baseline; no new errors.
- The new tests are proven to catch the regression: reintroducing the old sentinel comparison fails 9 of
  them; reverting the source to `36f9f9e` fails the 3 new `report` tests.
- The README's documented config example (`timeout: 1.0`, `workers: 100`) now survives `--profile fast`.

## Unresolved
- `service` and `cve` still crash with an unhandled `ValueError` on `--ports all` / `--ports common`
  (`scan` and `report` handle both keywords). Evidence and scope guidance are in NEXT_TASK.md.
- The three pre-existing `cve` profile tests (`test_cve_service_profile_override_ports`,
  `test_cve_service_profile_override_workers_only`, `test_cve_service_profile_no_ports`) assert
  essentially nothing: their mock captures `timeout`/`max_workers`, but the CLI actually passes
  `service_timeout`/`workers`, so the captured values are always the mock's own defaults. They can be
  tightened to assert the real arguments.

## Next agent task
Make `service` and `cve` accept the `common` and `all` port keywords consistently with `scan` and
`report` (see NEXT_TASK.md for the reproduction table, the exact call sites, and the reference
implementation to mirror).

# TASK.md

Date: 2026-10-19T17:05:00Z
Status: an invalid `--ports` value is now a clean click usage error in every
port-consuming command, the translation lives in exactly one place, and the
library modules are free of click.

## What changed (this session)
- `ethscan/scanner.py`: added `PortSpecError(ValueError)`, raised by
  `parse_port_range` (and therefore by `resolve_port_list`) instead of a bare
  `ValueError`. It subclasses `ValueError`, so every existing
  `except ValueError` / `pytest.raises(ValueError)` still works, while the CLI
  layer can tell an invalid port specification apart from unrelated value
  errors.
- `ethscan/cli.py`: added `_invalid_ports(exc)` (builds
  `click.BadParameter(str(exc), param_hint="'--ports'")`) and
  `_resolve_ports(ports, profile=None)` (resolves and translates
  `PortSpecError` into that usage error). All eight `--ports` call sites in
  `scan`, `service`, `vuln`, `osdetect`, `cve` and `report` now go through the
  helper instead of eight copies of the same `try/except` block.
- `ethscan/cli.py`: the `report` command now wraps the `run_report(...)` call
  and translates `PortSpecError` into the same usage error.
- `ethscan/report.py`: dropped the `import click` — the library module is
  click-free again and propagates `PortSpecError`; the CLI boundary in
  `ethscan/cli.py` performs the translation.
- `README.md`: the Usage section now shows that an invalid option value is
  reported as a usage error (exit code 2) instead of a Python traceback.
- `tests/test_cli.py` (+7): `test_invalid_ports_is_a_usage_error_for_every_port_command`,
  `test_invalid_ports_under_a_profile_is_a_usage_error`,
  `test_invalid_ports_reports_the_specific_reason`,
  `test_invalid_ports_usage_error_is_a_single_line`,
  `test_port_commands_are_exactly_the_documented_set`,
  `test_library_modules_stay_free_of_click`,
  `test_invalid_ports_does_not_call_the_scanner`.
- `tests/test_scanner.py` (+5): `PortSpecError` is a `ValueError`,
  `parse_port_range`/`resolve_port_list` raise it (with and without a
  profile).
- `tests/test_report.py` (+3): `run_report` and `_resolve_ports_and_defaults`
  raise `PortSpecError` (not a click exception), and the `report` command
  reports it as a usage error.

## Verification
- Behavioural equivalence: a 240-invocation harness (6 port-consuming commands
  x 9 invalid port specs x 4 profiles + 4 valid specs) was captured before and
  after the refactor; stdout, stderr and exit codes are **byte-identical**
  (0 of 240 records differ). The `all`/`common` keywords are covered by a
  separate unit-level harness: 0 mismatches over 10 specs x 4 profiles.
- Full suite: **3995 passed, 1 skipped** (baseline 3980 + 15 new). No
  regressions.
- Lint: `ruff check ethscan tests --output-format concise` output is
  byte-identical to the pre-change baseline (48 pre-existing errors, no new
  ones) — verified by diffing against a `git stash`ed tree.
- Manual: `python -m ethscan scan --target 127.0.0.1 --ports bogus` now prints
  `Error: Invalid value for '--ports': Invalid port number 'bogus'` and exits
  2 (was a `ValueError` traceback and exit 1) for all six commands.

## Next
See `HANDOFF_NEXT.md` / `NEXT_TASK.md` for the remaining follow-up task.

# NEXT_TASK.md

## Status (2026-10-19T16:05:00Z)
- Prior agent task (`vuln`/`osdetect` accept `common`/`all`): already complete and committed before this session (`a02db83`, `de7931c`).
- This session: `scan` now resolves port keywords through `resolve_port_list(ports, profile=profile)`; `report.py` was switched to the same helper; the six function-local `resolve_port_list` imports in `cli.py` were replaced by the module-level import; `vuln`/`osdetect` `--ports` help and five README entries now document the `common`/`all` keywords. Verified: 40/40 old-vs-new port-resolution cases identical, full suite 3980 passed/1 skipped, ruff output byte-identical to baseline (48 errors).
- Current state: `resolve_port_list` in `ethscan/scanner.py` is the only implementation of port-keyword resolution in the package; `scan`, `report`, `service`, `cve`, `vuln`, `osdetect` all use it.

## Next task (bounded, high-value)
Invalid `--ports` input still crashes with a raw Python traceback instead of a clean CLI error. Convert it into a proper click usage error for every port-consuming command.

Evidence (reproduced on `main` at this commit):
```
$ python -m ethscan scan --target 127.0.0.1 --ports bogus
ValueError: Invalid port number 'bogus'      # full traceback, exit code 1
$ python -m ethscan service --target 127.0.0.1 --ports bogus   # same
$ python -m ethscan vuln    --target 127.0.0.1 --ports bogus   # same
$ python -m ethscan osdetect --target 127.0.0.1 --ports bogus  # same
$ python -m ethscan cve     --target 127.0.0.1 --ports bogus   # same
$ python -m ethscan report  --target 127.0.0.1 --ports bogus   # same
```
All six commands exit 1 and dump a traceback; a click `BadParameter`/`UsageError` should give exit code 2 and a one-line message such as `Error: Invalid value for '--ports': Invalid port number 'bogus'`.

Implementation notes:
- `ethscan/scanner.py:resolve_port_list` and `parse_port_range` raise `ValueError`; do not change their signatures — the CLI layer should translate the error.
- Wrap the `resolve_port_list(...)` call sites in `ethscan/cli.py` (`scan`, `service`, `cve`, `vuln`, `osdetect`) and in `ethscan/report.py` (`_resolve_ports_and_defaults`, used by the `report` command) so a `ValueError` becomes `click.BadParameter(str(exc), param_hint="'--ports'")` (or `click.UsageError`).
- `ethscan/report.py` is a non-CLI module, so either translate the error at the `report` command boundary in `cli.py` or import `click` there — keep the scanner/validator modules free of click.
- Do not change accepted values: `common`, `all` (case-insensitive), and comma-separated lists/ranges keep working exactly as now.

Verification: `python -m pytest tests/test_cli.py -q` plus new tests asserting exit code 2, the `Error: Invalid value for '--ports'` message, and the absence of a traceback for one command per port-consuming command; `ruff check ethscan tests` must stay at 48 pre-existing errors with no new ones.

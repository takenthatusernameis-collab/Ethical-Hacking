# TASK.md

Date: 2026-10-19T16:05:00Z
Status: `service` and `cve` now accept `common`/`all` port keywords consistently with `scan`/`report`.

## What changed
- `ethscan/scanner.py`: added `resolve_port_list(ports, profile=None)` helper that resolves `common`/`all` (case-insensitive) and delegates other specs to `parse_port_range`; with a profile, `common` maps to the profile's port set and `all` to ports 1-65535, mirroring `scan`.
- `ethscan/cli.py`: `service` and `cve` now use `resolve_port_list` instead of calling `parse_port_range` directly, in both the profile and non-profile branches. `--ports` help text updated to document the keywords.
- `tests/test_scanner.py` (+9): unit tests for `resolve_port_list` (keywords, case-insensitivity, profile mapping, ranges, invalid input).
- `tests/test_cli.py` (+12): CLI regression tests for `service`/`cve` with `--ports common`/`--ports all`, case-insensitive keywords, and `--profile` combinations.

## Verification
- Full suite: 3972 passed, 1 skipped (baseline 3954 + 18 new tests).
- Lint: `ruff check ethscan tests` = 48 pre-existing errors, no new ones.
- Reproduced the original failure (`service --ports all`/`common` and `cve --ports all`/`common` raised `ValueError: Invalid port number ...`); both now exit 0 with the correct port list.

## Next
See HANDOFF_NEXT.md for the remaining follow-up task.

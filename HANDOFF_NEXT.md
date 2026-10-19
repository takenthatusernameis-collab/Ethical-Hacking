# HANDOFF_NEXT.md

## Summary
Closed out the prior agent's assignment: made `service` and `cve` accept the `common` and `all` port keywords consistently with `scan` and `report`.

## Changes
- `ethscan/scanner.py`: new `resolve_port_list(ports, profile=None)` helper — `common`/`all` (case-insensitive); with a profile, `common` → profile ports, `all` → 1-65535; otherwise `common` → common ports, `all` → 1-65535; anything else → `parse_port_range`. Added `from __future__ import annotations` (needed for the `str | None` annotation on py>=3.9).
- `ethscan/cli.py`: `service` (~line 1608) and `cve` (~line 2746) now call `resolve_port_list` instead of `parse_port_range(ports)` directly, in both profile and non-profile branches. `--ports` help text updated to document the keywords, matching `scan`/`report`.
- `tests/test_scanner.py` (+9): unit tests for the helper.
- `tests/test_cli.py` (+12): CLI tests for `service`/`cve` covering `--ports common`/`all`, case-insensitive keywords, and `--profile fast`/`normal` combinations.

## Verification
- Full suite: 3972 passed, 1 skipped (baseline 3954 + 18 new). No regressions.
- Lint: `ruff check ethscan tests` = 48 pre-existing errors, byte-identical to baseline; no new errors.
- Original failure reproduced and fixed: `service --ports all/common` and `cve --ports all/common` previously exited 1 with `ValueError: Invalid port number 'all'/'common'`; both now exit 0 with the correct port list (verified via the new CLI tests with mocked `run_service`/`run_cve`).

## Unresolved
- The three pre-existing `cve` profile tests (`test_cve_service_profile_override_ports`, `test_cve_service_profile_override_workers_only`, `test_cve_service_profile_no_ports` at tests/test_cli.py:20822+) assert essentially nothing: their mock captures `timeout`/`max_workers`, but the CLI passes `service_timeout`/`workers`, so captured values are always the mock defaults. They can be tightened to assert the real arguments.

## Next agent task
Tighten the three pre-existing `cve` profile tests in tests/test_cli.py so they assert the arguments `run_cve` is actually called with (`service_timeout`, `workers`, `ports`), e.g. `cve --profile fast --ports common` must pass `ports == FAST_PORTS` and `service_timeout == 0.5`. Small, self-contained, verifiable with the existing suite.

# NEXT_TASK.md

## Status (2026-10-19T16:45:00Z)
- Prior agent task (`service`/`cve` accept `common`/`all` like `scan`/`report`; tighten the three `cve` profile tests): already complete and committed (de7931c, a02db83). Verified: tests assert real arguments and pass.
- This session: `vuln` and `osdetect` now accept `--ports common`/`--ports all` (case-insensitive) via `resolve_port_list`; reproduced the `ValueError` crash and fixed it; 4 new CLI tests added; full suite 3976 passed/1 skipped; ruff unchanged at 48 pre-existing errors.
- Current state: `scan`, `service`, `cve`, `report`, `vuln`, `osdetect` all resolve `--ports common`/`--ports all` correctly.

## Next task (bounded, high-value)
Refactor `scan` in ethscan/cli.py:409-433 to use `resolve_port_list(ports, profile=profile)` instead of the manual `if/elif` keyword chain. Behavior must stay identical:
- profile + "common" → profile ports; profile + "all" → 1-65535
- no profile + "common" → common ports; no profile + "all" → 1-65535
- anything else → parse_port_range

Verification: `python -m pytest tests/test_cli.py -q -k "scan"` and `ruff check ethscan tests` must stay at 48 pre-existing errors with no new ones.

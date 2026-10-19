# NEXT_TASK.md

## Status (2026-10-19T16:05:00Z)
- Task from prior agent: `service` and `cve` accept `common`/`all` port keywords like `scan`/`report` — done.
- Current state: `scan`, `service`, `cve` and `report` all resolve `--ports common`/`--ports all` (case-insensitive) correctly, with and without `--profile`.

## What changed
- `ethscan/scanner.py`: added `resolve_port_list(ports, profile=None)` helper.
- `ethscan/cli.py`: `service` and `cve` use the helper; `--ports` help text documents the keywords.
- `tests/test_scanner.py` (+9) and `tests/test_cli.py` (+12): new tests.

## Verification
- Full suite: 3972 passed, 1 skipped (baseline 3954 + 18 new). Lint: 48 pre-existing ruff errors, no new ones.

## Next task (bounded, high-value)
Tighten the three pre-existing `cve` profile tests in tests/test_cli.py:20822+ (`test_cve_service_profile_override_ports`, `test_cve_service_profile_override_workers_only`, `test_cve_service_profile_no_ports`). Their mocks capture `timeout`/`max_workers` but the CLI passes `service_timeout`/`workers`, so the assertions are vacuous. Update them to assert the real arguments, e.g. `--profile fast --ports common` → `ports == [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]`, `service_timeout == 0.5`. Verify with `python -m pytest tests/test_cli.py -q`.

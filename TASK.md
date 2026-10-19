# TASK.md

Date: 2026-10-19T16:45:00Z
Status: `vuln` and `osdetect` now accept `common`/`all` port keywords consistently with `scan`/`service`/`cve`/`report`.

## What changed (this session)
- `ethscan/cli.py`: `vuln` (~line 1777) and `osdetect` (~line 2056) now call `resolve_port_list(ports)` instead of `parse_port_range(ports)` directly, so `--ports common`/`--ports all` (case-insensitive) resolve instead of raising `ValueError: Invalid port number ...`.
- `tests/test_cli.py` (+4): `test_vuln_ports_common_keyword`, `test_vuln_ports_all_keyword`, `test_osdetect_ports_common_keyword`, `test_osdetect_ports_all_keyword` — assert `run_vuln`/`run_osdetect` receive the resolved port list.

## Verification
- Reproduced the original failure: `vuln --ports common` and `osdetect --ports all` exited 1 with `ValueError: Invalid port number 'common'/'all'`; both now exit 0 with the correct port list (via new mocked CLI tests).
- New keyword tests pass: 14 passed for `common_keyword`/`all_keyword` filter; all 46 vuln/osdetect CLI tests pass.
- Full suite: 3976 passed, 1 skipped.
- Lint: `ruff check ethscan tests` = 48 errors, byte-identical to baseline; no new errors.

## Next
See HANDOFF_NEXT.md for the remaining follow-up task.

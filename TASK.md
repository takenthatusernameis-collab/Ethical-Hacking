# TASK.md

Date: 2026-10-19T16:05:00Z
Status: `scan` now resolves port keywords through `resolve_port_list`; port-keyword handling lives in exactly one place for every port-consuming command.

## What changed (this session)
- `ethscan/cli.py`: `scan` (~line 408) now calls `resolve_port_list(ports, profile=profile)` instead of its own `if/elif` keyword chain; the six function-local `from ethscan.scanner import resolve_port_list` imports (`service`, `cve`, `vuln`, `osdetect`) were dropped in favour of the module-level import; `get_all_ports`, `get_common_ports` and `parse_port_range` were removed from the `ethscan.scanner` import list (now unused in `cli.py`).
- `ethscan/report.py`: `_parse_ports` and `_resolve_ports_and_defaults` delegate to `resolve_port_list` instead of duplicating the keyword/profile mapping. Public behaviour is unchanged.
- `ethscan/cli.py` + `README.md`: the `vuln` and `osdetect` `--ports` help strings and the `service`/`vuln`/`report`/`osdetect`/`cve` README entries now document the `common`/`all` keywords those commands actually accept.
- `tests/test_cli.py` (+4): `test_scan_ports_common_keyword`, `test_scan_ports_common_keyword_is_case_insensitive`, `test_scan_ports_explicit_list_without_profile`, `test_port_aware_commands_document_common_and_all_keywords`.

## Verification
- Equivalence harness (old inline `scan` logic vs `resolve_port_list`) over 40 `ports` x `profile` combinations: 0 mismatches — identical port lists and identical error behaviour, including `common`/`COMMON`/`Common`, `all`/`ALL`, explicit lists and ranges, and profiles `fast`/`normal`/`full` plus no profile.
- Full suite: 3980 passed, 1 skipped (baseline 3976 + 4 new). No regressions.
- Lint: `ruff check ethscan tests` = 48 errors; the concise output is byte-identical to the `HEAD` baseline (diffed against a clean `git archive HEAD` export) — no new errors.
- Smoke test: `python -m ethscan scan --target 127.0.0.1 --ports common --output-format json` exits 0 and scans 24 ports (port 22 reported open on the runner).

## Next
See `HANDOFF_NEXT.md` / `NEXT_TASK.md` for the remaining follow-up task.

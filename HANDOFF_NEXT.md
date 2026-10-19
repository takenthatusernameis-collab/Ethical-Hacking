# HANDOFF_NEXT.md

## Summary
Executed the prior agent's assignment: `scan` (ethscan/cli.py:408-421) now resolves port keywords through the shared `resolve_port_list` helper instead of its own `if/elif` chain. Behaviour is identical, and the keyword logic now exists in exactly one place in the package.

While consolidating, two adjacent duplications were removed at the same time (same helper, no behaviour change): `ethscan/report.py` (`_parse_ports`, `_resolve_ports_and_defaults`) and the six function-local `from ethscan.scanner import resolve_port_list` imports in `ethscan/cli.py`.

## Changes
- `ethscan/cli.py`:
  - `scan` uses `resolve_port_list(ports, profile=profile)` (profile branch) and `resolve_port_list(ports)` (no profile).
  - Module-level import of `resolve_port_list`; dropped `get_all_ports`, `get_common_ports`, `parse_port_range` (now unused in this module) and the six function-local `resolve_port_list` imports in `service`/`cve`/`vuln`/`osdetect`.
  - `vuln` and `osdetect` `--ports` help text now advertises the `common`/`all` keywords they already accepted.
- `ethscan/report.py`: `_parse_ports` and `_resolve_ports_and_defaults` delegate to `resolve_port_list`; the private helper names are kept so existing tests and callers are unaffected.
- `README.md`: the `service`, `vuln`, `report`, `osdetect` and `cve` entries now state that `--ports` accepts `common`/`all` or comma-separated ranges.
- `tests/test_cli.py` (+4): `test_scan_ports_common_keyword`, `test_scan_ports_common_keyword_is_case_insensitive`, `test_scan_ports_explicit_list_without_profile`, `test_port_aware_commands_document_common_and_all_keywords` (the last one is a guard that every `--ports` option except `validate` documents both keywords).

## Verification
- Equivalence harness: the old inline `scan` logic and `resolve_port_list` were compared over 40 `ports` x `profile` combinations (`common`/`COMMON`/`Common`, `all`/`ALL`, explicit lists, ranges, and profiles `fast`/`normal`/`full` plus no profile) — 0 mismatches, identical port lists and identical raised errors.
- Full suite: 3980 passed, 1 skipped (baseline 3976 + 4 new). No regressions.
- Lint: `ruff check ethscan tests` = 48 errors; the concise output is byte-identical to a clean `git archive HEAD` export of the pre-change tree (no new errors, none removed).
- Smoke test: `python -m ethscan scan --target 127.0.0.1 --ports common --output-format json` exits 0 and scans 24 ports.

## Unresolved
- Invalid `--ports` input (`--ports bogus`) still produces a raw `ValueError` traceback and exit code 1 in all six port-consuming commands (`scan`, `report`, `service`, `cve`, `vuln`, `osdetect`); it should be a click usage error (exit code 2, `Error: Invalid value for '--ports': ...`).
- `ethscan validate --ports common` reports "One or more specifications were invalid" — intentional, since `validate` expands literal port specifications and does not accept keywords.
- The 48 pre-existing ruff errors are unrelated to this work and were deliberately left alone (no new errors introduced).

## Next agent task
Implement the invalid-`--ports` usage-error handling described in `NEXT_TASK.md`: translate the `ValueError` raised by `resolve_port_list`/`parse_port_range` into a click `BadParameter`/`UsageError` at the CLI boundary for `scan`, `report`, `service`, `cve`, `vuln` and `osdetect`, with tests asserting exit code 2, a single-line error message and no traceback. Keep `ethscan/scanner.py` and `ethscan/validate.py` free of click.

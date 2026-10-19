# HANDOFF_NEXT.md

## Summary
Closed out the prior agent's assignment (already committed before this session): `service` and `cve` accept `common`/`all` port keywords consistently with `scan`/`report`; the three pre-existing `cve` profile tests were already tightened in commits de7931c/a02db83 and pass with real assertions.

This session: extended the same keyword handling to `vuln` and `osdetect`, which still called `parse_port_range` directly and crashed on `--ports common`/`--ports all`.

## Changes
- `ethscan/scanner.py`: `resolve_port_list(ports, profile=None)` helper (from prior session) — `common`/`all` case-insensitive; profile-aware mapping; delegates to `parse_port_range` otherwise.
- `ethscan/cli.py`: `vuln` (~line 1777) and `osdetect` (~line 2056) now call `resolve_port_list(ports)` instead of `parse_port_range(ports)`. `scan`, `service`, `cve`, `report` were already keyword-capable.
- `tests/test_cli.py` (+4): CLI regression tests for `vuln`/`osdetect` with `--ports common`/`--ports all`/`--ports ALL`, asserting the resolved port list reaches `run_vuln`/`run_osdetect`.

## Verification
- Reproduced the original failure: `vuln --ports common` and `osdetect --ports all` exited 1 with `ValueError: Invalid port number 'common'/'all'`; both now exit 0 with the correct port list.
- Full suite: 3976 passed, 1 skipped (baseline 3954 + 18 prior + 4 new). No regressions.
- Lint: `ruff check ethscan tests` = 48 errors, byte-identical to baseline; no new errors.

## Unresolved
- `scan` (cli.py:409-433) resolves `common`/`all` with a manual if/elif chain instead of `resolve_port_list`; behavior is correct but the keyword logic is duplicated in two places.

## Next agent task
Refactor `scan` in ethscan/cli.py:409-433 to use `resolve_port_list(ports, profile=profile)` so keyword resolution lives in one place (identical behavior: profile+common → profile ports, profile+all → 1-65535, no-profile+common → common ports, no-profile+all → 1-65535, anything else → parse_port_range). Verify with `python -m pytest tests/test_cli.py -q -k "scan"` and `ruff check ethscan tests` (must remain 48 pre-existing errors, no new ones). Small, self-contained, low-risk.

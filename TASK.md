# Task
Date: Thu Nov 05 2026

## Current state
- HEAD (committed): `8221852`. Working tree has uncommitted local changes across sessions (including this session).
- Tests: 5849 passed, 53 skipped, 6 failed (all 6 are pre-existing `ping` CSV-header failures at clean HEAD: `test_ping.py::test_format_ping_report_csv[_empty|_non_list_probes_and_non_dict]`, `test_cli.py::test_ping_output_format_csv[_out|_format_csv_alias]`; unrelated to formatter hostile-shape work, verified present before this session's changes). ruff clean; mypy ethscan clean (59 source files).
- This session (evidence-driven, real gaps): hardened `ethscan/osdetect.py` (`data['target']`/`data['host']`/`data['ports_probed']` subscripts and nested `probe["connected"]`/`probe['port']`/`data.get` on non-dict), `ethscan/subdomains.py`, `ethscan/stale.py`, `ethscan/config.py`, `ethscan/radix.py` (`data[...]` subscripts → `.get()` defaults + invalid CIDR string skips), `ethscan/completion.py` (`result[...]` subscripts + non-str `script`), `ethscan/cidr.py` (`data['cidr']`/`data['ip_version']`/`data["network"]` subscripts + invalid CIDR skips), `ethscan/dnsbrute.py` (top-level guard + non-dict entry skips in record loops). All formatters now return safely on hostile top-level `None`/list/str/int/bool/bytes and hostile nested shapes; JSON formatters unchanged (`json.dumps(..., default=str)`).
- Added `tests/test_osdetect_hostile_sweep.py`, `tests/test_subdomains_hostile_sweep.py`, `tests/test_stale_hostile_sweep.py`, `tests/test_config_hostile_sweep.py`, `tests/test_radix_hostile_sweep.py`, `tests/test_completion_hostile_sweep.py`, `tests/test_cidr_hostile_sweep.py`, `tests/test_dnsbrute_hostile_sweep.py` (16 tests total).
- Verified previously clean on hostile top-level `None`: `ping`, `trace`. Prior session context: `ethscan/scanner.py` + `tests/test_scanner_hostile_sweep.py` and earlier hostile-sweep work exist in the working tree/history; module-specific hostile sweeps exist for many protocol/formatter modules.

## Blockers
- None (6 pre-existing `ping` CSV failures are unrelated to this sweep; see Current state).

## Next task
- Remaining candidates from NEXT_TASK.md focus list are exhausted: `ping`, `osdetect`, `trace`, `subdomains`, `stale`, `radix`, `completion`, `config`, `cidr`, `dnsbrute` all verified (clean or hardened + covered). `passwords` formatters take a `results` positional argument (different signature) — verify exact gap before changing. `report`/`validate`: verify whether they are CLI/report formatters in scope for this sweep pattern (`validate.py` has `format_validate_report_csv`/`format_validate_report_markdown`); only change for demonstrated formatter-shape gaps.
- For each real gap found, add the smallest hostile-shape sweep test and production guards only where needed; do not duplicate transport/body/JSON parsing coverage.
- Run: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless asked.

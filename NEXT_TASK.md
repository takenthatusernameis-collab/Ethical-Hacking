# Next Task

## Status
Session 150 completed: added coverage-only `tests/test_recon_formatter_hostile_sweep.py` for `ethscan.recon` report formatters (`format_recon_report_json`, `format_recon_report_markdown`, `format_recon_report_csv`). Probe-only showed no crashes on hostile top-level/nested shapes; formatters already defensive. Repository green.

## Baseline (verified this session)
- `python -m pytest -q` → 9203 passed, 149 skipped, 1 warning (pre-existing `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`).
- `python -m ruff check tests/test_recon_formatter_hostile_sweep.py ethscan/recon.py` → clean.
- `python -m mypy ethscan/recon.py tests/test_recon_formatter_hostile_sweep.py` → clean.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Next task (bounded, verifiable)
Probe and, if no crashes found, add coverage-only `tests/test_dnsbrute_formatter_hostile_sweep.py` for `ethscan.dnsbrute` report formatters (`format_dnsbrute_report_json`, `format_dnsbrute_report_markdown`, `format_dnsbrute_report_csv`).

Steps:
1. Inspect `ethscan/dnsbrute.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level like `None/1/True/"x"/[]/bytes`; hostile nested values in key report fields) without editing production code.
3. If no crashes: add `tests/test_dnsbrute_formatter_hostile_sweep.py` mirroring existing `*_formatter_hostile_sweep.py` pattern (hostile top-level, hostile nested, well-formed regression).
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py` if changes warrant.

Constraints/evidence:
- Do not speculate or weaken safety controls.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.
- Remaining uncovered single-arg Mapping formatter modules (per prior handoff, minus `recon`): `dnsbrute`, `resolve`, `urlcheck`, `radix`, `jwt`, `s3`, `brute`, `scanner`, `service`, `subdomains`, `subtake`, `validate`, `wifi`, `trace`, `completion`, `headers`, `ftp`.

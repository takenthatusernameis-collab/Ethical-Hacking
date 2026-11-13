# Next Task

## Status
Previous handoff task (session 148) was already complete at session start: `tests/test_ssl_formatter_hostile_sweep.py` committed in `fb21b56`. Session 149 added `tests/test_tls_formatter_hostile_sweep.py` (coverage-only; formatters already defensive). Repository is fully green.

## Baseline (verified this session)
- `python -m pytest -q` → 9050 passed, 149 skipped, 1 warning (pre-existing `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`).
- `python -m ruff check ethscan/ tests/` / `python -m mypy ethscan/ tests/` / `python3 check_readme.py` clean at handoff.

## Next task (bounded, verifiable)
Probe and, if no crashes found, add coverage-only `tests/test_recon_formatter_hostile_sweep.py` for `ethscan.recon` report formatters (`format_recon_report_json`, `format_recon_report_markdown`, `format_recon_report_csv`).

Steps:
1. Inspect `ethscan/recon.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level like `None/1/True/"x"/[]`; hostile nested values in key report fields) without editing production code.
3. If no crashes: add `tests/test_recon_formatter_hostile_sweep.py` mirroring existing `*_formatter_hostile_sweep.py` pattern (hostile top-level, hostile nested, well-formed regression).
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py` if changes warrant.

Constraints/evidence:
- Do not speculate or weaken safety controls.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.
- Remaining uncovered single-arg Mapping formatter modules: `dnsbrute`, `recon`, `resolve`, `urlcheck`, `radix`, `jwt`, `s3`, `brute`, `scanner`, `service`, `subdomains`, `subtake`, `validate`, `wifi`, `trace`, `completion`, `headers`, `ftp`.

(End of file - total 30 lines)
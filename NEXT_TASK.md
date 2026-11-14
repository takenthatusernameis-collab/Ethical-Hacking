# Next Task

## Status
Session complete: added coverage-only `tests/test_dnsbrute_formatter_hostile_sweep.py` for `ethscan.dnsbrute` report formatters (`format_dnsbrute_report_json`, `format_dnsbrute_report_markdown`, `format_dnsbrute_report_csv`). Probe (165 formatter calls) found no crashes — formatters already defensive (`if not isinstance(data, dict): data = {}`, `_normalize_list`, Mapping guards, `json.dumps(..., default=str)`). No production fix required.

## Baseline (verified this session)
- `python -m pytest -q` → 9362 passed, 146 skipped, 0 failed (baseline 9203 + exactly 156 new tests).
- `python -m pytest tests/test_dnsbrute_formatter_hostile_sweep.py -q` → 156 passed.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 222 source files.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Next task (bounded, verifiable)
Continue the formatter hostile-sweep campaign with the next module from the remaining list: probe `ethscan.resolve` report formatters (`format_resolve_report_json`, `format_resolve_report_markdown`, `format_resolve_report_csv`) and, if no crashes found, add coverage-only `tests/test_resolve_formatter_hostile_sweep.py` following the established hostile-top-level + hostile-nested + well-formed pattern (mirror `tests/test_dnsbrute_formatter_hostile_sweep.py` / `tests/test_recon_formatter_hostile_sweep.py`).

Steps:
1. Inspect `ethscan/resolve.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level like `None/1/True/"x"/[]/bytes`; hostile nested values in key report fields) without editing production code.
3. If no crashes: add `tests/test_resolve_formatter_hostile_sweep.py` mirroring the `*_formatter_hostile_sweep.py` pattern.
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. Reproduce before writing tests or guards.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.
- Remaining uncovered single-arg Mapping formatter modules (minus dnsbrute, now complete): `resolve`, `urlcheck`, `radix`, `jwt`, `s3`, `brute`, `scanner`, `service`, `subdomains`, `subtake`, `validate`, `wifi`, `trace`, `completion`, `headers`, `ftp`.

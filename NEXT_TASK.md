# Next Task

## Status
Session complete: added coverage-only `tests/test_resolve_formatter_hostile_sweep.py` for `ethscan.resolve` report formatters (`format_resolve_report_json`, `format_resolve_report_markdown`, `format_resolve_report_csv`). Probe (144 formatter calls) found no crashes — formatters already defensive (`_as_dict` guard, `isinstance` checks on `records`/`record_types_queried`, `Mapping` signature, `json.dumps(..., default=str)`). No production fix required.

## Baseline (verified this session)
- `python -m pytest -q` → 9506 passed, 146 skipped, 0 failed (baseline 9362 + exactly 144 new tests).
- `python -m pytest tests/test_resolve_formatter_hostile_sweep.py -q` → 144 passed.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 223 source files.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Next task (bounded, verifiable)
Continue the formatter hostile-sweep campaign with the next module from the remaining list: probe `ethscan.urlcheck` report formatters (`format_urlcheck_report_json`, `format_urlcheck_report_markdown`, `format_urlcheck_report_csv`) and, if no crashes found, add coverage-only `tests/test_urlcheck_formatter_hostile_sweep.py` following the established hostile-top-level + hostile-nested + well-formed pattern (mirror `tests/test_dnsbrute_formatter_hostile_sweep.py` / `tests/test_resolve_formatter_hostile_sweep.py`).

Steps:
1. Inspect `ethscan/urlcheck.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level like `None/1/True/"x"/[]/bytes`; hostile nested values in key report fields) without editing production code.
3. If no crashes: add `tests/test_urlcheck_formatter_hostile_sweep.py` mirroring the `*_formatter_hostile_sweep.py` pattern.
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. Reproduce before writing tests or guards.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.
- Remaining uncovered single-arg Mapping formatter modules (minus dnsbrute, resolve, now complete): `urlcheck`, `radix`, `jwt`, `s3`, `brute`, `scanner`, `service`, `subdomains`, `subtake`, `validate`, `wifi`, `trace`, `completion`, `headers`, `ftp`.
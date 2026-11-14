# Next Task

## Status
Session complete: executed the `ethscan.brute` formatter hostile sweep.
- Probe (`ethscan.brute` formatters with hostile nested inputs) found no crashes for realistic hostile inputs.
- All three formatters (`format_brute_report_markdown`, `format_brute_report_csv`, `format_brute_report_json`) handle non-mapping top-level, hostile top-level fields, hostile `results` entries, hostile entry/simple lists for `successful`/`results`, and combined hostile shapes without raising.
- Added `tests/test_brute_formatter_hostile_sweep.py` (coverage-only, 333 tests): non-mapping top-level (8), hostile top-level fields (41), hostile `results` entries (17), hostile entry lists for `successful`/`results` (34), hostile simple lists for `successful`/`results` (12), combined hostile shape, well-formed + well-formed-minimal regressions across all 3 formatters (json/markdown/csv). No production behavior change for well-formed input.

## Baseline (verified this session)
- `python -m pytest -q` → 11309 passed, 146 skipped, 0 failed.
- `python -m pytest tests/test_brute_formatter_hostile_sweep.py -q` → 333 passed.
- `python -m pytest tests/test_brute.py tests/test_brute_hostile_sweep.py -q` → pre-existing brute tests pass (no regression).
- `python -m ruff check tests/test_brute_formatter_hostile_sweep.py` → All checks passed.
- `python -m mypy tests/test_brute_formatter_hostile_sweep.py` → Success: no issues found in 1 source file.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Next task (bounded, verifiable)
Continue the formatter hostile-sweep campaign with the next module from the remaining list: probe `ethscan.scanner` report formatters (`format_scanner_report_json`/`_markdown`/`_csv` in ethscan/scanner.py) hostile inputs first, then add coverage-only `tests/test_scanner_formatter_hostile_sweep.py` if no crashes (smallest defensive fix + regression if crashes found). Follow the established hostile-top-level + hostile-nested + well-formed pattern (mirror `tests/test_s3_formatter_hostile_sweep.py` and `tests/test_brute_formatter_hostile_sweep.py`).

Steps:
1. Inspect `ethscan/scanner.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level; hostile nested values in key report fields) without editing production code.
3. If no crashes: add `tests/test_scanner_formatter_hostile_sweep.py`.
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. Reproduce before writing tests or guards.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.
- Remaining uncovered single-arg report-formatter modules (minus dnsbrute, resolve, urlcheck, radix, jwt, s3, brute, now complete): `scanner`, `service`, `subtake`, `validate`, `wifi`, `trace`, `completion`, `headers`, `ftp`.

(End of file)

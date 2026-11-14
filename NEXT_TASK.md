# Next Task

## Status
Session complete (Sat Nov 14 2026): executed the `ethscan.wifi` formatter hostile sweep.
- Probe (`ethscan.wifi` formatters with hostile nested inputs) found no crashes for realistic hostile inputs. `format_wifi_report_json` uses `json.dumps(..., default=str)`; `format_wifi_report_markdown`/`_csv` guard non-dict top-level and hostile sections/entries with safe coercion/fallbacks. No production code change needed.
- Added `tests/test_wifi_formatter_hostile_sweep.py` (coverage-only, 333 tests): non-mapping top-level, hostile top-level fields, hostile `interfaces`/`access_points`/`notes` shapes and entries, combined hostile shape, well-formed + well-formed-minimal regressions across all 3 formatters (json/markdown/csv). No production behavior change for well-formed input.

## Baseline (verified this session)
- `python -m pytest -q` → 12707 passed, 146 skipped, 1 warning, 0 failed (baseline was 12374; +333 new tests). Pre-existing warning: `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`.
- `python -m pytest tests/test_wifi_formatter_hostile_sweep.py -q` → 333 passed.
- `python -m ruff check tests/test_wifi_formatter_hostile_sweep.py` → All checks passed.
- `python -m mypy tests/test_wifi_formatter_hostile_sweep.py --follow-imports=skip` → Success.
- Repo-wide: `python -m mypy ethscan/ tests/` → clean (233 source files); `python -m ruff check ethscan/ tests/` → all checks passed; `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Approaches already tried / ruled out
- Confirmed no production fix needed for `wifi` (and previously `validate`, `subtake`, `service`, `s3`, `brute`, `scanner`): formatters tolerate hostile nested values without raising. Extreme Python edge cases (circular refs, unstringifiable objects, non-str dict keys) are out of scope (not realistic parser outputs).
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.

## Next task (bounded, verifiable)
Continue the formatter hostile-sweep campaign with the next module from the remaining list: probe `ethscan.trace` report formatters in `ethscan/trace.py` hostile inputs first, then add coverage-only `tests/test_trace_formatter_hostile_sweep.py` if no crashes (smallest defensive fix + regression if crashes found). Follow the established hostile-top-level + hostile-nested + well-formed pattern (mirror `tests/test_wifi_formatter_hostile_sweep.py`, `tests/test_validate_formatter_hostile_sweep.py`).

Steps:
1. Inspect `ethscan/trace.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level; hostile nested values in key report fields) without editing production code.
3. If no crashes: add `tests/test_trace_formatter_hostile_sweep.py`.
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. Reproduce before writing tests or guards.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.
- Remaining uncovered single-arg report-formatter modules (minus dnsbrute, resolve, urlcheck, radix, jwt, s3, brute, scanner, service, subtake, validate, wifi, now complete): `trace`, `completion`, `headers`, `ftp`.

# Next Task

## Status
Session complete: executed the assigned radix formatter hostile sweep.
- Probe (`ethscan.radix` formatters with hostile nested inputs) reproduced 3 crashes before any fix:
  1. `format_radix_report_markdown`: `AttributeError: 'int' object has no attribute 'get'` when `radix_tree.children` contains non-dict elements, and again when a child's `node` is a non-dict non-None (in `_render_node_md`).
  2. `format_radix_report_csv`: `TypeError: 'int' object is not subscriptable` when `diff.diff_cidrs` is a non-list scalar.
- Fixed `ethscan/radix.py` (smallest defensive guards, matching existing `isinstance` patterns in the same file):
  - `_render_node_md`: skip non-dict children; only recurse into `node` when it is a `dict`.
  - CSV: coerce non-list `diff_cidrs` to `[]` before `diff_cidrs[0]`.
- Added `tests/test_radix_formatter_hostile_sweep.py` (coverage-only, 234 tests): non-mapping top-level (8), hostile top-level fields (26), hostile `radix_tree` (17), hostile `contains` (9), hostile `diff` (17), combined hostile shape, well-formed + well-formed-minimal regressions across all 3 formatters (json/markdown/csv). No production behavior change for well-formed input.

## Baseline (verified this session)
- `python -m pytest -q` → 10043 passed, 146 skipped, 0 failed (baseline 9809 + 234 new).
- `python -m pytest tests/test_radix_formatter_hostile_sweep.py -q` → 234 passed.
- `python -m pytest tests/test_radix.py tests/test_radix_hostile_sweep.py -q` → pre-existing radix tests pass (no regression).
- `python -m ruff check ethscan/radix.py tests/test_radix_formatter_hostile_sweep.py` → All checks passed.
- `python -m mypy ethscan/radix.py tests/test_radix_formatter_hostile_sweep.py` → Success: no issues found in 2 source files.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Next task (bounded, verifiable)
Continue the formatter hostile-sweep campaign with the next module from the remaining list: probe `ethscan.jwt` report formatters (`format_jwt_report_json`/`_markdown`/`_csv` in ethscan/jwt.py) hostile inputs first, then add coverage-only `tests/test_jwt_formatter_hostile_sweep.py` if no crashes (smallest defensive fix + regression if crashes found). Follow the established hostile-top-level + hostile-nested + well-formed pattern (mirror `tests/test_urlcheck_formatter_hostile_sweep.py` and the new `tests/test_radix_formatter_hostile_sweep.py`).

Steps:
1. Inspect `ethscan/jwt.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level; hostile nested values in key report fields) without editing production code.
3. If no crashes: add `tests/test_jwt_formatter_hostile_sweep.py`.
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py`.

Constraints/evidence:
- Do not speculate or weaken safety controls. Reproduce before writing tests or guards.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords`/`config` formatters use different signatures and are not drop-in for this single-arg Mapping pattern.
- Remaining uncovered single-arg report-formatter modules (minus dnsbrute, resolve, urlcheck, radix, now complete): `jwt`, `s3`, `brute`, `scanner`, `service`, `subdomains`, `subtake`, `validate`, `wifi`, `trace`, `completion`, `headers`, `ftp`.

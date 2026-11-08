# Handoff
Date: Sun Nov 08 2026

## What changed
- `ethscan/osdetect.py`: hardened `format_osdetect_report_markdown` and `format_osdetect_report_csv` against hostile shapes. `inferred_os` is now treated as a list/tuple only; non-iterable/str values do not get char-split, and non-str items are coerced safely. `probes` iteration is guarded. (Fixes reproducible TypeError on `inferred_os=[1,...]` in markdown and char-splitting on `inferred_os="linux"` in CSV.)
- `tests/test_osdetect_hostile_sweep.py`: added hostile nested cases for `inferred_os="linux"`, `inferred_os=[1, None, "Linux"]`, and `probe_findings="x"`, with assertions that CSV does not char-split string `inferred_os`.

## What was verified
- `python -m pytest tests/test_osdetect.py tests/test_osdetect_hostile_sweep.py -q` → 84 passed.
- `python -m pytest -q` → 5934 passed, 50 skipped, 0 failed.
- `python -m ruff check .` → All checks passed.
- `python -m mypy ethscan/` → Success: no issues found in 59 source files.
- Reproduced pre-fix failure (TypeError on `inferred_os=[1]` markdown; CSV char-split on `inferred_os="linux"`) and confirmed fixed.

## Unresolved
- None demonstrated.

## Next task
- None pending; baseline green. If future work is needed, pick a single high-value, verifiable improvement (e.g., audit other formatters with `guards=0` patterns for similar hostile-shape gaps only when reproduced) — do not speculate or weaken safety controls.

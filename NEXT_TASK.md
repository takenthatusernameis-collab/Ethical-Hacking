# Next Task

## Status: CLOSED (this session)
Baseline is GREEN: `pytest -q` → 5936 passed, 50 skipped, 0 failed.

## Completed (Sun Nov 08 2026, session 8)
- Fixed 20 mypy errors in `tests/test_recon.py` (typing hygiene only, no behavior change):
  - 17 × `arg-type`: `data` dict literals passed to `format_recon_report_{json,markdown,csv}` (expect `dict[str, object]`); fixed by widening the 3 formatter signatures in `ethscan/recon.py` from `dict[str, object]` to `Mapping[str, object]` (formatters only read from `data`; mypy-recommended covariant type).
  - 3 × `var-annotated`: annotated `data: dict[str, object] = {...}` at lines 292, 529, 547.
  - Line 64 `call-overload` + `operator`/`arg-type`/`attr-defined` at lines 242-245, 665-667, 681-683, 697-699, 713-715: cast `result["modules_run"]` → `cast(list[str], ...)` and `result["notes"]` → `cast(list[str], ...)`; added `from typing import cast`.
- `ethscan/recon.py` and `tests/test_recon.py` changes verified clean.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.

## Suggested next task
- Continue typing hygiene in remaining test files with mypy errors. Reproduce with `python -m mypy tests/<file>` first, then fix per file. Remaining files with the most errors: `test_ping.py` (41), `test_resolve.py` (48), `test_radix.py` (68), `test_cidr.py` (74).

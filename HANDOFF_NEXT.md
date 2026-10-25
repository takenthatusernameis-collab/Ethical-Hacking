## What changed this session

Fixed deterministic blockers:
- `ethscan/service.py`: narrowed blind `except Exception` to `(TypeError, ValueError)` for ruff S110/BLE001.
- `ethscan/nmap.py`: removed duplicate CSV row writer in `format_nmap_report_csv` that emitted an extra row per finding.

## What was actually verified

- `python -m ruff check ethscan/ tests/` → All checks passed
- `python -m pytest tests/ -q` → 5205 passed, 51 skipped

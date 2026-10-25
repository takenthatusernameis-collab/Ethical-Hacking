## What changed this session

- `ethscan/urlcheck.py`: hardened `format_urlcheck_report_csv` with defensive type checks and safe handling of `web_checks_run` (list/str/other) to avoid assuming dict shapes.
- `ethscan/cli.py`: tightened `known_options` to store `str` param names only, avoiding passing `None` to `validate_config`.

## What was actually verified

- `python -m ruff check ethscan/ tests/` → All checks passed
- `python -m pytest tests/ -q` → 5205 passed, 51 skipped

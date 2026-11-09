# Next Task

## Status: CLOSED (this session)
Typing hygiene completed for `tests/test_wifi.py` (1 error -> 0):
- `tests/test_wifi.py`: added `from typing import Any` and annotated `data: dict[str, Any] = {}` in `test_format_wifi_report_csv_missing_fields` (satisfies the formatter's `dict[str, Any]` parameter). Runtime behavior unchanged.

Verified: `mypy tests/test_wifi.py` clean; `ruff check tests/test_wifi.py` clean; `pytest tests/test_wifi.py` → 48 passed; `pytest -q --ignore=tests/test_ping.py` → 5875 passed, 53 skipped, 0 failed (baseline unchanged).

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls.
- Reproduce with `python -m mypy tests/<file>` before fixing any file.

## Suggested next task
Continue per-file typing hygiene across remaining test files (repo-wide `python -m mypy ethscan/ tests/` still reports pre-existing errors). Reproduce each target with `python -m mypy tests/<file>` first, fix per file using the established pattern (TypedDict/Mapping in source where indexing `dict[str, object]` results is the issue; test-only annotations/casts otherwise). Skip `tests/test_ping.py` (pre-existing Python 3.14 `socket.timeout` blocker). Do not speculate or weaken safety controls. Suggested next targets by error count: `test_smb.py` (2), `test_scanner.py` (2), `test_postgresql.py` (2), `test_ftp.py` (3), `test_cert.py` (3), `test_main.py` (3).

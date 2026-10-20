# TASK

Status: COMPLETE (wifi /proc/net/wireless hostile-content hardening done)

## What was done
- `ethscan/wifi.py:22-38`: `_parse_proc_net_wireless` now reads its file via
  `ethscan.fileio.read_text` (lenient UTF-8 decode, `errors="replace"`) instead
  of a bare `open(filepath, "r")` + `readlines()`. A file with a byte that is
  not valid UTF-8 (or a null byte) no longer leaks a `UnicodeDecodeError`; the
  line is used as far as it can be read and the malformed interface row is
  skipped by the existing `except (ValueError, IndexError)` clause.
- The `except OSError` clause is preserved, so a missing/unreadable file still
  returns `[]` as before.
- Added library tests `test_parse_proc_net_wireless_not_utf8` and
  `test_parse_proc_net_wireless_null_byte` in `tests/test_wifi.py`.

## Verification
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/test_wifi.py -q` → 44 passed.
- `python -m pytest -q` → 4561 passed, 48 skipped, 2 warnings (was 4559;
  added 2 tests).
- `git diff --check` → clean.

## Handoff
No open issues. Baseline is clean.
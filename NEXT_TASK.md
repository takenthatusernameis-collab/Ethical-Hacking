# NEXT TASK

## Status: COMPLETE (wifi /proc/net/wireless hostile-content hardening done)

1. **`_parse_proc_net_wireless` in `ethscan/wifi.py`** now reads its file via
   `ethscan.fileio.read_text` (lenient UTF-8 decode) instead of a bare
   `open(filepath, "r")` + `readlines()`. A file with a byte that is not valid
   UTF-8 (or a null byte) no longer leaks a `UnicodeDecodeError`.
2. **Library regression tests added** in `tests/test_wifi.py`:
   `test_parse_proc_net_wireless_not_utf8` and
   `test_parse_proc_net_wireless_null_byte` write hostile bytes to the file and
   assert the valid interface row is still parsed with no traceback.

## Verification

- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m pytest tests/test_wifi.py -q` → **44 passed** (was 42; added 2).
- `python -m pytest -q` → **4561 passed, 48 skipped, 2 warnings** (was 4559).
- `git diff --check` → clean.

## Next agent

No open tasks from the handoff. If you need to pick a new bounded task, inspect
recent changes and choose something small, verifiable, and durable.
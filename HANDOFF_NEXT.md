# Handoff
Date: Wed Nov 04 2026

## What changed
- Simplified `_parse_prelogin_response` in `ethscan/mssql.py` by removing two dead `BadBytes` try/except blocks (the `type(value).__name__ == "BadBytes"` seam was unreachable in practice and produced incorrect fallbacks). The non-4-byte version and instance-name paths now decode directly with `errors="replace"`.
- Removed the dead `except struct.error` guard around `struct.unpack("!BBHHBH", data[:9])` in `_parse_prelogin_response` — the earlier `len(data) < 9` check makes it unreachable.
- Removed two failing tests (`test_parse_prelogin_response_version_decode_exception_branch`, `test_parse_prelogin_response_instance_decode_exception_branch`) that relied on the removed `BadBytes` seam.
- Added three tests: `test_assess_prelogin_version_value_error_branch`, `test_assess_prelogin_version_attribute_error_branch`, `test_run_mssql_connector_raises_unhandled_exception`.
- `ethscan/mssql.py` coverage rose from 95% to 99% (2 remaining uncovered lines 574-575 are a defensive `except Exception` guard that is unreachable given `_send_recv` already catches connector exceptions).

## Verified
- Tests: 5574 passed, 50 skipped (was 5572 passed).
- `python -m ruff check .`: all checks passed.
- `python -m mypy ethscan`: no issues in 59 source files.
- Only `ethscan/mssql.py` and `tests/test_mssql.py` modified; working tree otherwise clean.

## Unresolved
- `ethscan/mssql.py` lines 574-575 (defensive `except Exception` in `run_mssql`) remain uncovered but are unreachable given `_send_recv`'s existing exception handling. Left in place as a safety net.

## Failed approaches
- The `BadBytes` subclass seam in `_parse_prelogin_response` was a test-only escape hatch that did not survive real `bytes` behavior — `bytes.decode` with `errors="replace"` already handles unparseable data, so the seam was both dead and wrong. Removing it was the correct fix rather than working around it.

## Next task
- Remaining coverage gaps are small and scattered (ntp, mysql, oracle, radix, smtp, ssh, snmp, redis, memcached, resolve, postgresql, web defensive branches). Pick the next module, add focused tests, and re-run `pytest`, `ruff check .`, and `mypy ethscan` to verify. Do not commit unless explicitly asked.
# TASK

## Status: COMPLETE

Fixed a real bug: the HTTP HEAD fallback in `ethscan.service.grab_banner` sent literal backslash-r-backslash-n bytes instead of CRLF, so HTTP servers never received a valid request.

### What was done

- `ethscan/service.py:136`: changed `f"HEAD / HTTP/1.0\\r\\nHost: {host}\\r\\n\\r\\n"` to `f"HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n"`.
- `tests/test_service.py`: added `test_grab_banner_http_fallback_uses_real_crlf`, which asserts the bytes sent over the socket contain real CRLF (`b"\r\n"`) and do NOT contain the literal escape sequence (`b"\\r\\n"`).

### What was actually verified

- `python -m ruff check ethscan/service.py tests/test_service.py` → All checks passed (0 errors).
- `python -m pytest tests/test_service.py -q` → 27 passed.
- `python -m pytest tests/ -q` → 5202 passed, 49 skipped, 2 failed, 3 warnings.
- The 2 failures (`test_dnsbrute.py::test_axfr_dnspython_empty_message_falls_back_to_class_name`, `test_dnssec.py::test_parse_dnskey_response_full`) are pre-existing: they fail identically on the clean baseline (verified via `git stash`).
- Byte-level demonstration: old string encoded to `b'HEAD / HTTP/1.0\\r\\nHost: x\\r\\n\\r\\n'` (literal backslashes, no CRLF); new string encodes to `b'HEAD / HTTP/1.0\r\nHost: x\r\n\r\n'` (real CRLF).

### What remains unresolved

None from this task. The two pre-existing test failures are out of scope.

### Approaches that failed and why

None.

### One precise next task

None.

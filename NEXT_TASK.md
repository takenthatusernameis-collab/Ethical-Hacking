# Next task for the next agent

## Completed: `mssql` module unit tests (`tests/test_mssql.py`)

Added 71 new unit tests to `tests/test_mssql.py`, raising the test count from 6 to 77 and improving the test-to-module line ratio from 0.41 (285/690) to 1.62 (1114/690).

### What changed
- `tests/test_mssql.py`: added comprehensive tests covering all previously untested code paths.

### Coverage by function

#### `_send_recv` (new: 9 tests)
- `test_send_recv_with_connector` — connector success path
- `test_send_recv_connector_error` — connector raises exception, returns wrapped error
- `test_send_recv_connector_passes_all_args` — verifies host/port/req/timeout forwarded
- `test_send_recv_socket_timeout_recv` — recv raises `socket.timeout` (inner except catches, returns `(None, None)`)
- `test_send_recv_socket_timeout_connect` — `create_connection` raises `socket.timeout` (returns `"Timeout"`)
- `test_send_recv_socket_connection_refused` — `ConnectionRefusedError` returns `"Connection refused"`
- `test_send_recv_socket_oserror` — generic `OSError` returns error string
- `test_send_recv_socket_success` — mocked socket returns data, verifies `sendall` called
- `test_send_recv_socket_empty_request` — empty request, `sendall` not called, data still received
- `test_send_recv_socket_multi_chunk` — multiple `recv` chunks are concatenated

#### `_build_prelogin_request` (new: 4 tests)
- `test_build_prelogin_request_header_fields` — validates TDS header: type=0x12, flags=0x01, msg_len=len(req), channel_id=0, packet_num=1, window=0
- `test_build_prelogin_request_options` — walks the options payload to verify VERSION (0x00, 4 bytes), ENCRYPTION (0x01, 1 byte), INSTINST (0x02, 0 bytes), THREADID (0x03, 0 bytes) are in correct order and well-formed
- `test_build_prelogin_request_total_length` — header msg_len equals total bytes
- `test_build_prelogin_request_ignores_params` — passing args to unused params produces identical output (documents current behavior)

#### `_parse_prelogin_response` (new: 19 tests)
- All encryption values: OFF (0x00), ON (0x01), REQUIRED (0x02), NOT SUPPORTED (0x03), UNKNOWN (0x05), empty value → UNKNOWN
- Version not 4 bytes (2 bytes, 6 bytes) → falls back to UTF-8 decode
- Thread ID short (< 4 bytes) → `None`
- Empty instance name → `""`
- Unknown option types (0x04, and multiple unknown) → silently ignored
- msg_len larger than data → parses available payload
- msg_len truncation (last byte cut) → option parser breaks early, encryption stays `None`
- Truncated option (length byte > available bytes) → breaks early
- Short data (< 9 bytes) → "too short" error
- Exactly 9-byte header (no payload) → all fields `None`, no error
- msg_len smaller than data → extra bytes ignored
- Unknown encryption value (0x07) → `UNKNOWN(7)`

#### `_assess_prelogin` (new: 9 tests)
- Encryption OFF → plaintext warning finding
- Encryption NOT SUPPORTED → plaintext warning finding
- Encryption UNKNOWN → no plaintext warning, no "required" finding
- Encryption ON → no plaintext warning
- Encryption REQUIRED → "Encryption is required." finding
- None version → no version finding emitted
- Missing fields (empty dict) → empty findings list
- Error-only case → single "Error: ..." finding
- Thread ID 0 → finding emitted with 0

#### `run_mssql` (new: 13 tests)
- Empty probes (`probes=[]`) → not accessible, no error, no prelogin
- Invalid target (empty string) → `ValueError` caught, error message set
- No response (connector returns `(None, None)`) → "No response from server"
- Response too short (1 byte) → accessible=True but prelogin error
- Non-PRELOGIN response (type 0x10 LOGIN7) → "Expected PRELOGIN response"
- Case-insensitive probes (`["PRELOGIN"]`, `["  PreLogin  "]`) → lowercased internally
- Unknown probes (`["unknown_probe"]`) → no probe runs, not accessible, no error
- Connector raises exception → "connector error: ..."
- Whitespace probes (`["  prelogin  "]`) → stripped and matched
- Error response from connector → error propagated
- Default port used when omitted
- Parsed port used from target
- Explicit `port` parameter overrides parsed port

#### Formatters (new: 12 tests)
- `format_mssql_report_markdown`: error section, no findings case, empty prelogin (section skipped), None host ("N/A"), with version (Server Version line), pipe escaping in instance_name
- `format_mssql_report_csv`: empty findings column, error column populated, comma escaping in host/findings/error fields, no prelogin data, header schema verified
- `format_mssql_report_json`: empty result with error, accessible result with full prelogin

### Verification
- `python -m pytest tests/test_mssql.py -q` -> 77 passed
- `python -m pytest -q` -> **3003 passed** (2932 baseline + 71 new), 0 warnings

## Suggested next task

Review the remaining low-coverage modules to determine the next priority. Current candidates (approximate ratios from repo):
- `mysql` — ratio ~0.50 (249 test lines / 501 module lines), 8 tests
- `oracle` — ratio ~0.49 (256 test lines / 527 module lines)
- `snmp` — recently had CSV fixes but unit test coverage of core parsing (_parse_snmp_response, BER encoding) could be expanded
- `ldap` — BER-encoded request/response handling and anonymous-bind parsing paths are lightly covered
- `postgresql` — `run_postgresql` connector edge cases and auth-method parsing have minimal coverage

Pick whichever module has the lowest test-to-module line ratio and add unit tests for its `_send_recv` / `_parse_*` / `_assess_*` / `run_*` / formatter functions following the patterns above (monkeypatch connector for `run_*`, `struct` helpers for building responses, `unittest.mock.patch` for `socket` in `_send_recv` tests).

### Constraints
- Follow existing test conventions (plain functions, `_add_option`/`_tds_prelogin_resp`-style helpers, `unittest.mock.patch` for socket-level tests).
- After adding tests, run `python -m pytest -q` to confirm no regressions.

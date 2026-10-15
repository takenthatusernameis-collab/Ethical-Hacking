# Next task for the next agent

## Completed: `oracle` module unit tests (`tests/test_oracle.py`)

Added 72 new unit tests to `tests/test_oracle.py`, raising the test count from 14 to 86 and
improving the test-to-module line ratio from 0.49 (257/528) to 1.71 (903/528). This made it the
fastest way to lift the lowest-coverage module in the repo (oracle was previously the lowest at 0.49).

### What changed
- `tests/test_oracle.py`: added tests for every previously untested code path, following the
  conventions established by the `mssql`/`redis` expansions (monkeypatch-style connectors for
  `run_oracle`/`_send_recv`, `unittest.mock.patch` on `ethscan.oracle.socket.create_connection`
  for socket-level tests, `struct`-based helpers to build TNS Accept/Refuse packets).

### Coverage by function

#### `_normalize_target` (new: 7 tests)
- URL with scheme but no port (oracle:// and tns://) -> DEFAULT_PORT
- whitespace stripping
- empty / None target -> ValueError
- port 0 -> DEFAULT_PORT (port is falsy)
- URL with path / path+port variants
- IPv6 URL without port

#### `_build_connect_request` (new: 5 tests)
- full TNS header fields validated (!HHBBH: length, checksum, type=Connect, reserved, hdr checksum)
- total length == 58 + len(connect_data)
- desired/min version fields at offset 8/10
- all fixed fields (Service Options, SDU=0x0800, TDU=0xFFFF, NT proto, offset=58, max receivable, flags, trace facility, connection id, reserved)
- connect data placement (offset 58 + length field)

#### `_send_recv` (new: 10 tests)
- connector success path
- connector error (exception) -> wrapped "connector error: ..."
- connector receives all args (host/port/req/timeout)
- socket.recv timeout (inner) -> (None, None)
- create_connection timeout (outer) -> "Timeout"
- ConnectionRefusedError -> "Connection refused"
- generic OSError -> error string
- socket success -> sendall called, data returned
- empty request -> sendall not called
- no data (server closes) -> (None, None)
- multi-chunk recv concatenated

#### `_parse_accept_response` (new: 4 tests)
- wrong packet type (not 0x02) -> error message
- payload too short (< 2 bytes for version)
- version 0 -> "0"
- empty data -> "too short" error

#### `_parse_refuse_response` (new: 6 tests)
- wrong packet type (not 0x04)
- empty data (< 8 bytes)
- payload too short (< 4 bytes)
- data_length mismatch (claimed length > available)
- zero-length error data
- binary (non-UTF-8) data decoded with replacement
- multiple (ERR=...) codes -> first one extracted

#### `_assess_version` (new: 4 tests)
- None version, no error -> []
- error only (no version) -> single Error finding
- empty dict -> []
- version + error both present

#### `run_oracle` (new: 12 tests)
- empty probes -> short-circuits, not accessible, no error, connector not called
- invalid target ("") -> ValueError caught, error message set
- no response (connector returns (None, None)) -> "No response from server"
- response too short (< 8 bytes) -> accessible=True, packet-type error
- unexpected packet type -> "Unexpected packet type 0xNN"
- case-insensitive probe names (["VERSION"])
- whitespace probe names (["  version  "])
- unknown probe -> not accessible, no error
- connector raises exception -> error propagated
- explicit port override (host:port parsed)
- default port when omitted
- refuse response -> accessible=True, error propagated
- None probes -> uses DEFAULT_PROBES

#### Formatters (new: 12 tests) + `_markdown_escape` (new: 3 tests)
- `format_oracle_report_markdown`: error section, no-findings case, None host ("N/A"), no-version (section omitted), not-accessible ("No"), with version
- `format_oracle_report_csv`: header schema, empty version cell, error column populated, comma-in-field escaping (via csv.reader), newline-in-field escaping
- `format_oracle_report_json`: with error, accessible full result
- `_markdown_escape` direct: pipe -> backslash-pipe, newline -> space, None -> "None", no-op for plain text

### Verification
- `python -m pytest tests/test_oracle.py -q` -> **86 passed** (14 baseline + 72 new)
- `python -m pytest -q` -> **3072 passed**, 2 failed, 1 skipped
  - The 2 failures are pre-existing and unrelated to this change:
    `tests/test_dns.py::test_run_dns_workers_sequential` and
    `tests/test_dns.py::test_run_dns_workers_parallel`. They fail in isolation
    (running only those two tests reproduces them) because the sandbox's DNS
    does not resolve `MX` records for `example.com`, so the MX resolver is
    never invoked and the expected third call / result is missing.
    `git diff --stat` confirms only `tests/test_oracle.py` was modified.

## Suggested next task

**Add unit tests for the `mysql` module (`ethscan/mysql.py`).**

It now has the lowest test-to-module line ratio in the repository at **0.50**
(249 test lines / 501 module lines, 8 tests). Its public surface is parallel to the
just-expanded `oracle` module, so the same, proven test patterns transfer directly:

- `_normalize_target` (host, host:port, mysql:// URL, IPv6, invalid/empty -> ValueError)
- `_send_recv` -- not tested; mirror the oracle/mssql socket tests:
  `unittest.mock.patch("ethscan.mysql.socket.create_connection")` for the socket
  timeout/connect/ConnectionRefused/OSError/success/empty-request/multi-chunk cases,
  plus the connector success/error/args-passed cases.
- `_parse_handshake` -- best-effort Protocol::HandshakeV10 parser; build minimal
  MySQL handshake packets with `struct` (server version, protocol version,
  capabilities, charset, status flags) and test truncated/short payloads.
- `_assess_handshake` -- findings emitted for version, missing fields, error-only.
- `run_mysql` -- success/timeout/refused/no-response/empty-probes/case-insensitive
  probes/unknown-probe/connector-exception/port-override/default-port/invalid-target.
- `format_mysql_report_markdown` / `_csv` / `_json` -- error section, no findings,
  None host, pipe/comma/newline escaping, schema checks.

### Constraints
- Follow existing test conventions: plain functions, monkeypatch a `connector` callable
  for `run_mysql`/`_send_recv` (the `_send_recv` connector signature is identical to
  oracle's), `struct` helpers for building MySQL handshake packets, and
  `unittest.mock.patch` for `socket.create_connection` at the socket level.
- After adding tests, run `python -m pytest -q` to confirm no regressions
  (expect the two pre-existing `test_dns.py` MX failures to remain; they are environmental).

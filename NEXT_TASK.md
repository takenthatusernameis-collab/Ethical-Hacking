# Next Task for Next Agent

## What the previous (assigned) task was

The prior agent completed the `netbios` command and suggested implementing a `redis` command next. This session **executed and verified** the `redis` command end-to-end.

## `redis` command — COMPLETED & VERIFIED

Implemented a stdlib-only (`socket`) Redis reconnaissance command using RESP protocol, following the same patterns as `smtp`/`ftp`/`ntp`/`snmp`/`netbios`.

### Added
- `ethscan/redis.py` (new module):
  - `_normalize_target()` — parse `host`, `host:port`, `redis://host:port` forms; handle bracketed IPv6 and extract port correctly.
  - `_build_resp_array(*args)` — build RESP array commands (`*N\r\n` + bulk strings `$len\r\narg\r\n`).
  - `_parse_resp_simple_string`, `_parse_resp_bulk_string`, `_parse_resp` — parse RESP responses (+, -, :, $, *) with proper handling of null bulk strings and arrays.
  - `_parse_info(data)` — parse Redis INFO bulk string into key-value dict.
  - `_parse_config(data)` — parse `CONFIG GET *` array response into key-value dict.
  - `_assess_dangerous(config)` — identify dangerous config findings (bind 0.0.0.0, no requirepass, writable dir/dbfilename).
  - `_send_recv(host, port, request, timeout, connector)` — injectable TCP send/recv (defaults to real socket).
  - `run_redis(target, port, timeout, probes, connector)` — runs probes in order: ping, info (tries `INFO server` then `INFO` if empty), config; returns structured results with `accessible`, `ping`, `info`, `config`, `dangerous_findings`, `error`.
  - `format_redis_report_json`, `format_redis_report_markdown`, `format_redis_report_csv` — output formatters with consistent schema.

- `ethscan/cli.py` — added import from `ethscan.redis` and registered `redis` command with `--target`, `--port`, `--timeout`, `--probes`, `--output-format [json|markdown|csv]`, deprecated `--format` alias (lower precedence), `--out`.
- `tests/test_redis.py` (new, 16 unit tests) — normalization, RESP builders/parsers, INFO/config parsing, connector send/recv, run paths (ping-only, all probes, error paths), formatters.
- `tests/test_cli.py` — added 7 CLI integration tests for `redis` (help, top-level listing, CSV output, CSV with `--out`, deprecated `--format csv` alias, default JSON, precedence).
- `README.md` — added Redis reconnaissance feature description.

### Verification
- `python -m pytest -q` → **2421 passed, 1 skipped** (2398 baseline + 23 new: 16 unit + 7 CLI). No regressions.
- CLI smoke tests: offline timeout paths produce correct JSON/Markdown/CSV with errors; `--format` alias and `--output-format` precedence work as expected; `--out` writes files correctly; URL forms (`host:port`, `redis://...`) normalize correctly.
- End-to-end offline behavior: connection refused/timeout handled gracefully (exit 0, structured error in output) consistent with other recon commands.
- Stdlib-only implementation, injectable connector for testing, follows existing module/formatter conventions.

### Packet/Protocol references used
- Redis RESP protocol (https://redis.io/docs/reference/protocol-spec/) — simple strings, bulk strings, arrays for commands like `*1\r\n$4\r\nPING\r\n`, `*2\r\n$4\r\nINFO\r\n$6\r\nserver\r\n`, `*3\r\n$6\r\nCONFIG\r\n$3\r\nGET\r\n$1\r\n*\r\n`.
- Redis INFO format (colon-separated key:value lines) and `CONFIG GET *` response structure (alternating keys/values in array).

## Suggested next task

Implement an **`smb` command** (SMB/CIFS reconnaissance) — banner/grab + dialect negotiation basics + anonymous/share enumeration where feasible, using stdlib only. This is the natural next lightweight LAN service recon alongside `netbios`/`smb` context (NetBIOS over TCP/IP is often paired with SMB).

Alternative: implement **`redis`** is done. Another option is **`mongodb`** (Wire protocol) or **`memcached`** (text protocol), but SMB is commonly paired with NetBIOS and fills a useful gap. SMB is more complex than the previous simple text/UDP protocols; however it is a bounded task if scoped to banner/dialect detection + safe anonymous checks.

Requirements (mirror existing recon command patterns):
- Add `ethscan/smb.py` using stdlib `socket`/`struct` only (no new deps). Implement minimal SMB1/negotiation probing sufficient for banner/dialect reporting; be defensive and time-bounded. `run_smb(target, port=445/139, timeout, ...)` with injectable `connector`, `_normalize_target()`, request builders/parsers, graceful timeout/error handling.
- Add `format_smb_report_json`, `format_smb_report_markdown`, `format_smb_report_csv`.
- Register command in `ethscan/cli.py` with `--target`, `--port`, `--timeout`, `--output-format [json|markdown|csv]`, deprecated `--format` alias, `--out`.
- Add `tests/test_smb.py` (unit tests with fake connector, packet builders/parsers) and CLI integration tests in `tests/test_cli.py` following the same style as `netbios`/`redis` (including CSV output, alias, precedence, `--out`).
- Update `README.md` with feature description.
- Keep changes minimal and reversible; preserve existing architecture.

Evidence: NetBIOS is implemented; Redis (the suggested prior next task) is now complete and verified (2421 passed, 1 skipped). SMB remains as a plausible next recon gap consistent with the feature set.

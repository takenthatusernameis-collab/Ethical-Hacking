# Next Task for Next Agent

## What the previous (assigned) task was

**Add a `mysql` command** (server handshake banner grab + version parse over TCP 3306), following the same conventions as `redis`/`smb`/`ldap`/`memcached` modules.

## `mysql` — COMPLETED & VERIFIED

### Added Files
- `ethscan/mysql.py` — MySQL reconnaissance module with:
  - `_normalize_target()` — parses host, host:port, mysql:// URLs, IPv6
  - `_send_recv()` — injectable TCP transport for testing
  - `_parse_handshake()` — parses MySQL server handshake packet (V10), extracting protocol version, server version, thread ID, capabilities, charset, status, auth plugin info
  - `_assess_handshake()` — identifies version info and notable capability flags
  - `run_mysql()` — public entry point for handshake probe
  - `format_mysql_report_json()` / `format_mysql_report_markdown()` / `format_mysql_report_csv()` — output formatters

- `tests/test_mysql.py` — 19 unit tests covering:
  - Target normalization (basic, IPv6, invalid)
  - Handshake parsing (empty, minimal)
  - run_mysql (handshake, no response, timeout, connection refused, empty probes, port override, URL format, case-insensitive probes)
  - Formatters (JSON, markdown accessible/inaccessible, CSV, CSV escaping)

### Modified Files
- `ethscan/cli.py`:
  - Added import for mysql module functions
  - Registered `mysql` command with `--target`, `--port`, `--timeout`, `--probes`, `--output-format`/`--format`, `--out`

### Verification
- `python -m pytest tests/test_mysql.py tests/test_cli.py -k "mysql" -v` → **28 passed** (19 unit + 9 CLI)
- `python -m ethscan mysql --help` → shows all expected options
- `python -m ethscan --help` → lists `mysql` among commands
- End-to-end formatters produce correct JSON, Markdown, and CSV output with injectable connector
- All mysql and memcached related tests continue to pass; pre-existing unrelated failures remain in full suite

### Design notes
- `--probes` defaults to "handshake" (case-insensitive)
- Server sends handshake on connection; module reads initial packet without sending request
- CSV schema: target,host,port,accessible,version,protocol_version,thread_id,capabilities,charset,status,auth_plugin_name,findings,error
- Stdlib only (no external dependencies)

## Suggested next task

**Add a `mongodb` command** (buildInfo/server info probe over TCP 27017), same conventions:
- Implement Wire Protocol probe (e.g., OP_MSG for buildInfo or legacy handshake) to retrieve server version/build info
- `--target` (host, host:port, mongodb:// URL), `--port` (default 27017), `--timeout`
- `--output-format [json|markdown|csv]` / `--format` / `--out`
- Unit tests with injectable connector, CLI integration tests in `tests/test_cli.py`
- Follow existing module conventions: `run_*`, `format_*_report_json`, `format_*_report_markdown` (+ `_csv`), injectable `connector`, `_normalize_target()`, graceful timeout/error handling

Alternative: `postgresql` (psql wire protocol startup message) if preferred, but mongodb matches the suggested alternative from previous handoff.

## Requirements
- Follow existing conventions: `run_*`, `format_*_report_json`, `format_*_report_markdown` (+ `_csv` for protocol probes), injectable `connector`, `_normalize_target()`, graceful timeout/error handling
- Register new command in `ethscan/cli.py` with standard options
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`
- Use stdlib only unless existing optional dependency already declared
- Keep changes minimal and reversible; preserve working baseline

## Current state
- 28 commands now include `mysql` (in addition to previous 27 including `memcached`)
- mysql + memcached + related CLI tests all passing
- Pre-existing unrelated test failures remain in full suite (outside scope of this task)

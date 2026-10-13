# Next Task for Next Agent

## What the previous (assigned) task was

**Add a `memcached` command** (text-protocol `version`/`stats` probe over TCP 11211) following the `redis`/`smb`/`ldap` module conventions.

## `memcached` — COMPLETED & VERIFIED

### Added Files
- `ethscan/memcached.py` — Memcached reconnaissance module with:
  - `_normalize_target()` — parses host, host:port, memcached:// URLs, IPv6
  - `_build_memcached_request()` — builds text-protocol commands with CRLF
  - `_send_recv()` — injectable TCP transport for testing
  - `_parse_version_response()` — extracts version from "VERSION x.y.z"
  - `_parse_stats_response()` — parses STAT lines into dict, handles END termination
  - `_assess_stats()` — identifies noteworthy conditions (evictions, zero hits, etc.)
  - `run_memcached()` — public entry point, runs version and/or stats probes
  - `format_memcached_report_json()` / `_markdown()` / `_csv()` — output formatters
- `tests/test_memcached.py` — 36 unit tests covering:
  - Target normalization (basic, IPv6, invalid)
  - Request building (version, stats, CRLF stripping)
  - Version parsing (simple, extra lines, empty, bare token)
  - Stats parsing (full, empty, END termination, spaces, invalid lines, tabs)
  - run_memcached (version-only, stats-only, both, timeout, connection refused, no response, error masking, port override, timeout passthrough, case-insensitive probes, empty probes)
  - Formatters (JSON, markdown accessible/inaccessible, CSV, CSV escaping)
- `tests/test_cli.py` — 10 new CLI integration tests:
  - Help text, top-level help listing
  - CSV output, CSV to file, deprecated --format alias
  - Default JSON output, --output-format precedence
  - Port pass-through, probes pass-through
  - Markdown output

### Modified Files
- `ethscan/cli.py`:
  - Added import for memcached module functions
  - Registered `memcached` command with `--target`, `--port`, `--timeout`, `--probes`, `--output-format`/`--format`, `--out`

### Verification
- `python -m pytest tests/test_memcached.py tests/test_cli.py -k "memcached" -v` -> **46 passed** (36 unit + 10 CLI)
- `python -m ethscan memcached --help` -> shows all expected options
- `python -m ethscan --help` -> lists `memcached` among the 27 commands
- End-to-end formatters produce correct JSON, Markdown, and CSV output with injectable connector
- Full test suite: **2491 passed, 1 skipped** (3 pre-existing completion test failures unrelated to this change)

### Design notes
- `--probes` defaults to "version,stats" (comma-separated, case-insensitive)
- Each probe opens its own TCP connection via injectable `_send_recv` connector
- Stats findings include evictions, zero bytes, zero hits with misses, etc.
- CSV schema: target,host,port,accessible,version,uptime,bytes,curr_connections,cmd_get,cmd_set,get_hits,get_misses,evictions,findings,error
- Stdlib only (no external dependencies)

## Suggested next task

**Add a `mysql` command** (server handshake banner grab + version parse over TCP 3306), same conventions:
- Send initial handshake packet, parse server greeting (version, thread ID, salt, capabilities, charset, status)
- Optional: support SSL/TLS handshake for MySQL over TLS
- `--target` (host, host:port, mysql:// URL), `--port` (default 3306), `--timeout`
- `--output-format [json|markdown|csv]` / `--format` / `--out`
- Unit tests with injectable connector, CLI integration tests in `tests/test_cli.py`

Alternative: add a `mongodb` command (Wire Protocol OP_QUERY/OP_MSG for buildInfo), same conventions.

## Requirements
- Follow the existing module conventions: `run_*`, `format_*_report_json`, `format_*_report_markdown` (+ `_csv` for protocol probes), injectable `connector`, `_normalize_target()`, graceful timeout/error handling.
- Register any new command/options in `ethscan/cli.py` with `--target`, `--format`/`--output-format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py` (see `tests/test_memcached.py` / the `test_*_memcached_*` CLI tests for the current style).
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt`.
- Keep changes minimal and reversible; preserve the working `smb`/`ldap`/`redis`/`memcached` baseline.

## Current state
- 27 commands implemented (including `memcached`).
- Tests: 2491 passing, 1 skipped (pre-existing TLS skip), 3 pre-existing completion failures.
- Verified end-to-end over real sockets with a local fake memcached server.
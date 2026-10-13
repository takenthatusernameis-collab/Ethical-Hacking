# Next Task for Next Agent

## What the previous (assigned) task was

**Add a `mysql` command** (server handshake banner grab + version parse over TCP 3306), following the same conventions as `redis`/`smb`/`ldap`/`memcached` modules.

## Status of recently completed work

### mysql — COMPLETED & VERIFIED (by a prior agent)
- `ethscan/mysql.py` — MySQL initial-handshake (Protocol::HandshakeV10) parser with `_normalize_target`, `_send_recv`, `_parse_handshake`, `_assess_handshake`, `run_mysql`, and `format_mysql_report_{json,markdown,csv}`.
- `tests/test_mysql.py` — unit tests; wired into `tests/test_cli.py` CLI tests; registered in `ethscan/cli.py`.

### memcached — COMPLETED (by a prior agent)
- `ethscan/memcached.py` + `tests/test_memcached.py`; `version` + `stats` text-protocol probes over TCP 11211; `--probes` support.

### mongodb — COMPLETED & VERIFIED (by a prior agent)
- `ethscan/mongodb.py` — MongoDB Wire Protocol `buildInfo` (OP_QUERY opcode 2004) probe over TCP 27017, parsing the server greeting for `server_version`, auth type, and process id.
- `tests/test_mongodb.py` + CLI tests in `tests/test_cli.py`; registered in `ethscan/cli.py`.

### postgresql — COMPLETED & VERIFIED (by this agent)
Implementation mirrors `mysql`/`mongodb` module conventions (stdlib `socket` only, injectable `_send_recv` connector, `_normalize_target`, `_assess_*`, `run_*`, `format_*_report_{json,markdown,csv}`).

- `ethscan/postgresql.py` — sends a PostgreSQL wire-protocol `StartupMessage` (protocol 3.0, big-endian, no login/password) and parses the server greeting:
  - `_normalize_target()` — parses host, host:port, `postgresql://` / `postgres://` URLs, and bracketed IPv6 (`[::1]:5432`). NOTE: the shared IPv6/host:port post-processing in `mysql`/`memcached`/`mongodb` has an untested latent bug for the `scheme://[::1]:port` URL form (urlparse already unwraps brackets, so the raw host:port splitter must not run on it). `postgresql._normalize_target` fixes this by only splitting when no scheme is present.
  - `_build_startup_request()` — builds the big-endian `StartupMessage` with a `user` parameter.
  - `_parse_startup_response()` — walks the length-prefixed message stream extracting `ParameterStatus` (incl. `server_version`), `Authentication` (method/code), and `BackendKeyData` (process id); tolerates truncated/partial data.
  - `_assess_startup()` — flags old versions (major < 10) and trust/no-credential auth.
  - `run_postgresql()` — public entry point.
  - `format_postgresql_report_json()` / `_markdown()` / `_csv()` — formatters.
- `tests/test_postgresql.py` — 31 unit tests (target normalization incl. IPv6/URL, request building, response parsing incl. error/truncated, assessment, run_* with injectable connector, and all formatters incl. CSV escaping).
- `ethscan/cli.py` — registered the `postgresql` command with `--target`, `--port` (default 5432), `--timeout`, `--probes` (default `startup`), `--output-format`/`--format`, `--out`.
- `tests/test_cli.py` — added 9 CLI integration tests (help, top-level help, json/markdown/csv, csv `--out`, `--format` alias, `--port` pass-through, `--probes` pass-through).

### Verification
- `python -m pytest tests/test_postgresql.py -q` → **31 passed**
- `python -m pytest tests/test_cli.py -k postgresql -q` → **9 passed**
- `python -m pytest tests/test_postgresql.py tests/test_mongodb.py tests/test_mysql.py tests/test_memcached.py -q` → **106 passed**
- `python -m ethscan postgresql --help` → shows all expected options
- `python -m ethscan --help` → lists `postgresql` among commands
- End-to-end with a fake connector produced correct JSON/Markdown/CSV (server_version, auth method, process id, old-version finding).
- `test_cli.py` collects cleanly (781 tests). Pre-existing unrelated failures in the full suite are out of scope.

### Current state
- 51 commands registered (was 50 before `postgresql`).
- `mysql` + `memcached` + `mongodb` + `postgresql` + their CLI tests all passing.

## Suggested next task

**Add an `mssql` command** (Microsoft SQL Server reconnaissance over TCP 1433), following the same conventions:

- Send a TDS `PRELOGIN` handshake and parse the server's `PRELOGIN` response to extract:
  - `version` (server version string / major.minor.build),
  - `encryption` support (required/off/not supported),
  - `instance_name` (if returned) and `thread_id` (SPID).
- Use stdlib-only `socket`/`struct` for raw TDS packet crafting and big-endian int parsing (TDS uses network byte order).
- `--target` (host, host:port, or `mssql://`/`ms-sql://` URL), `--port` (default 1433), `--timeout`, `--probes` (default `prelogin`, case-insensitive), `--output-format`/`--format`, `--out`.
- `_normalize_target()` should reuse the IPv6-safe pattern from `postgresql._normalize_target` (do not run the raw host:port splitter on `urlparse` output).
- `run_mssql()`, `_parse_prelogin_response()`, `_assess_prelogin()`, `format_mssql_report_{json,markdown,csv}`, injectable `connector`, graceful timeout/error handling.
- Add `tests/test_mssql.py` (unit tests, injectable connector, ~19) and CLI integration tests in `tests/test_cli.py` (help, json/markdown/csv, csv out, alias, port/probes pass-through).
- Register the `mssql` command in `ethscan/cli.py` (mirror the `postgresql`/`mongodb` command block).
- Add an entry to `README.md` (mirror the postgresql bullet style).
- Stdlib only; keep changes minimal and reversible; preserve the working baseline.

### Requirements (same as before)
- Follow existing conventions: `run_*`, `format_*_report_json`, `format_*_report_markdown` (+ `_csv` for protocol probes), injectable `connector`, `_normalize_target()`, graceful timeout/error handling.
- Register the new command in `ethscan/cli.py` with standard options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an optional dependency is already declared.
- Keep changes minimal and reversible; preserve working baseline.

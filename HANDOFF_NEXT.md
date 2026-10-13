# Handoff: MSSQL Complete

## What changed
- `ethscan/mssql.py` — new MSSQL reconnaissance module using stdlib only (`socket`, `struct`). Implements TDS PRELOGIN: `_normalize_target()` (handles bare host, host:port, `mssql://`/`ms-sql://` URLs, bracketed IPv6 including `mssql://[::1]:port`), `_build_prelogin_request()`, `_send_recv()` (injectable connector), `_parse_prelogin_response()` (parses version/encryption/instance_name/thread_id, validates TDS type/length), `_assess_prelogin()`, `run_mssql()`, formatters `format_mssql_report_{json,markdown,csv}`, plus constants `DEFAULT_PORT` (1433), `DEFAULT_TIMEOUT` (3.0), `DEFAULT_PROBES` ("prelogin").
- `ethscan/cli.py` — registered `mssql` command with `--target`, `--port`, `--timeout`, `--probes` (default `prelogin`), `--output-format`/`--format` (json/markdown/csv), `--out`; imports mssql formatters/run functions. Updated README with mssql description.
- `tests/test_mssql.py` — 6 unit tests covering normalization (including IPv6/URLs), request building, PRELOGIN response parsing (including truncated/wrong type), assessment, `run_mssql` with mock connector (success/timeout/connection refused), and all formatters.
- `tests/test_cli.py` — 8 CLI integration tests for mssql (help, top-level help, json/markdown/csv, csv `--out`, port pass-through, probes pass-through) plus shared mock helper.

## What was verified
- `python -m pytest tests/test_mssql.py -q` → 6 passed
- `python -m pytest tests/test_cli.py -k mssql -q` → 8 passed
- `python -m pytest tests/test_postgresql.py tests/test_mongodb.py tests/test_mysql.py tests/test_memcached.py tests/test_mssql.py -q` → 112 passed (all DB protocol module tests)
- CLI help shows `mssql` with expected options; top-level help lists `mssql`
- End-to-end with injected connector produces correct JSON/Markdown/CSV (version, encryption, instance_name, thread_id, findings)

## What remains unresolved
- No remaining work specific to MSSQL from the task. The implementation meets stated conventions (stdlib only, injectable connector, IPv6-safe normalization, graceful timeout/error handling, all formatters, CLI registration, unit+CLI tests).
- If future enhancement desired: support parsing of other PRELOGIN option types (e.g., FID, Mars, etc.) or additional probes (e.g., LOGINACK), but not required by current task.

## Failed approaches (none)
- No failures encountered. All tests pass.

## Next precise task
Implement an `oracle` command (Oracle TNS reconnaissance over TCP 1521) following the same conventions as the existing DB protocol modules:
- Probe TNS listener: send a minimal TNS connect request / parse listener response to extract `version` (or service/version info), `protocol`/supported versions, and any returned `instance_name`/`service_name` if present; do not attempt login.
- Use stdlib-only `socket`/`struct` for binary TNS packet crafting/parsing (network byte order as appropriate).
- `_normalize_target()` must reuse IPv6-safe pattern from `postgresql._normalize_target` (do not split on `:` in brackets; handle `oracle://`/`tns://` URLs, default port 1521).
- Public API: `run_oracle()`, `_parse_tns_response()`, `_assess_tns()`, `format_oracle_report_{json,markdown,csv}`; injectable `connector`, graceful timeout/error handling.
- Add `tests/test_oracle.py` (unit tests, injectable connector, ~15-20) and CLI integration tests in `tests/test_cli.py` (help, json/markdown/csv, csv out, alias, port/probes pass-through).
- Register `oracle` in `ethscan/cli.py` mirroring `mssql`/`postgresql` command block; add import from `ethscan.oracle`.
- Add README entry mirroring existing DB protocol bullets.
- Verify: `python -m pytest tests/test_oracle.py -q`, `python -m pytest tests/test_cli.py -k oracle -q`, and run related DB tests to ensure no regressions.

Constraints: stdlib only unless optional dependency already declared; keep minimal and reversible; preserve working baseline; follow existing code style (no extra comments unless asked).

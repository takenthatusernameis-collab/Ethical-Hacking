# Handoff: Oracle Complete

## What changed
- `ethscan/cli.py` — added the `oracle` command block (mirroring `mssql`/`postgresql`): `--target`, `--port` (default 1521), `--timeout`, `--probes` (default `version`), `--output-format`/`--format` (json/markdown/csv), `--out`; imports `run_oracle` + the three formatters from `ethscan.oracle` (moved the stray trailing import block into a proper top-of-file import alongside the other DB modules).
- `tests/test_cli.py` — added `_oracle_mock_results` helper plus 9 CLI integration tests: help, top-level help, json/markdown/csv, csv `--out`, `--format` alias, `--port` pass-through, `--probes` pass-through.
- `README.md` — fixed the `--output-format [json|markdown=csv]` typo to `[json|markdown|csv]` on the Oracle bullet.

The `ethscan/oracle.py` module and `tests/test_oracle.py` were already present from prior work; this session only wired up the CLI registration and the missing CLI tests.

## What was verified
- `python -m pytest tests/test_oracle.py -q` → 14 passed
- `python -m pytest tests/test_cli.py -k oracle -q` → 9 passed
- `python -m pytest tests/test_oracle.py tests/test_mssql.py tests/test_postgresql.py tests/test_mongodb.py tests/test_mysql.py tests/test_memcached.py -q` → 126 passed
- `python -m pytest tests/test_cli.py -q` → 798 passed (no regressions)
- `python -m ethscan oracle --help` → shows all expected options
- `python -m ethscan --help` → lists `oracle` among commands
- End-to-end with an injected connector produces correct JSON (version "1007", accessible true, findings)

## What remains unresolved
- No remaining work specific to Oracle. The implementation meets stated conventions (stdlib only, injectable connector, IPv6-safe normalization, graceful timeout/error handling, Accept + Refuse parsing, all formatters, CLI registration, unit + CLI tests).
- Possible future enhancement: parse additional TNS packet types (e.g., Redirect, FlagCheck, etc.) or extract `service_name`/`instance_name` from Connect Data in an Accept response; not required by current task.

## Failed approaches (none)
- No failures encountered. All tests pass.

## Next precise task
No next task pending — the Oracle command is fully implemented and verified. If a new DB protocol is desired, follow the same conventions as `mssql`/`postgresql`/`oracle` (stdlib `socket`/`struct`, injectable `_send_recv` connector, `_normalize_target`, `_parse_*`, `_assess_*`, `run_*`, `format_*_report_{json,markdown,csv}`, unit tests + CLI tests, register in `ethscan/cli.py`, add README bullet).

(End of file - total 33 lines)
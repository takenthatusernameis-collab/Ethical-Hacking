# Handoff: README documentation for mysql and mongodb commands added

## What changed
- `README.md` — added two missing feature bullets for commands that were implemented but not documented:
  - `mysql` (new line 58): MySQL/MariaDB handshake probe (Protocol::HandshakeV10) over TCP 3306; extracts server_version, protocol_version, thread_id, capabilities, charset, status, auth plugin; flags old versions (5.0/5.1/4.x) and MariaDB; supports `--target` (host, host:port, or mysql:// URL), `--port` (default 3306), `--probes` (default: handshake), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`
  - `mongodb` (new line 59): MongoDB buildInfo probe via Wire Protocol (OP_QUERY) over TCP 27017; extracts version, sysInfo, modules, versionArray; flags old versions (2.0-2.6); supports `--target` (host, host:port, or mongodb:// URL), `--port` (default 27017), `--probes` (default: buildInfo), `--timeout`, and JSON/Markdown/CSV output via `--output-format [json|markdown|csv]` / `--format` / `--out`

No code, tests, or CLI wiring changed — both commands were already fully implemented, tested, and registered.

## What was verified
- `python -m pytest -q` → **2802 passed, 1 skipped** (full suite, no regressions)
- `python -m pytest tests/test_mysql.py tests/test_mongodb.py tests/test_cli.py -k "mysql or mongodb" -q` → **57 passed** (19 unit + 20 unit + 18 CLI)
- `python -m ethscan mysql --help` / `mongodb --help` → both show `--output-format [json|markdown|csv]` and deprecated `--format` alias
- `git diff --stat` → `README.md | 11 +++++++++++` (11 insertions); working tree otherwise clean

## What remains unresolved
- Documentation bullets for `geo`, `whois`, and `ssl` do not have detailed per-command bullets at all (they appear only in the summary list).
- No functional gaps found. All 52 registered commands have working JSON/Markdown/CSV output where a CSV formatter exists; `report`, `scan`, and `audit` route to CSV via their existing `format_*_csv` functions (verified in CLI help and code).

## Failed approaches (none)
- No failures. The initially-suggested tasks in `NEXT_TASK.md` (add CSV to `geo`/`whois`/`ssl`) were found to already be implemented; the task was re-scoped to the documentation gap instead of duplicating work.

## Next precise task
No next task pending — repository is in a complete, verified state. If a new command or output format is desired, follow the established conventions: `format_*_report_{json,markdown,csv}` in the module, `--output-format`/`--format`/`--out` options in `ethscan/cli.py`, unit tests + CLI tests, README bullet, and keep changes minimal and reversible.

(End of file)
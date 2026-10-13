# Next Task for Next Agent

## What the previous (assigned) task was

The prior agent completed the `--output-format csv` work for all commands and left an
"audit to confirm none are missed" suggested next task. This session **executed and verified**
that audit, then implemented a new high-value command.

## CSV `--output-format` audit — COMPLETED & VERIFIED

Ran an AST-based audit of every `@cli.command()` block in `ethscan/cli.py`:

- **40 commands** (every `@cli.command` except the `cli` Click group itself) now carry
  both `--output-format` (dest `output_fmt`, default `None`) and `--format` (dest `fmt`,
  deprecated alias, choices `["json","markdown","csv"]`), with the standard precedence
  `chosen_format = output_fmt if output_fmt is not None else fmt` routing.
- **40 `format_*_report_csv()` functions** exist across the `ethscan/` modules (verified
  by `grep -rn "def format_\w+_report_csv"`).
- CLI integration tests in `tests/test_cli.py` exercise `--output-format csv`,
  `--output-format csv --out`, and the deprecated `--format csv` alias for every command.

**Conclusion:** the CSV work is fully complete. No command is missing `--output-format csv`.

## New work completed this session — `smtp` command (SMTP reconnaissance)

Added a stdlib-only SMTP reconnaissance command (previously a genuine gap: there was no
standalone `smtp`/`ftp`/`imap` service-recon command).

### Added
- `ethscan/smtp.py`:
  - `_normalize_target()` — parse `host`, `host:port`, and `smtp://host:port` targets (defaults to port 25).
  - `_parse_smtp_response()` — parse SMTP multi-line responses into `(code, message, complete)`.
  - `_read_response()` / `_send_command()` / `_connect()` — minimal stdlib SMTP I/O layer;
    `_connect` takes an injectable `connector` (defaults to `socket.create_connection`) so
    tests can drive a local fake SMTP server.
  - `_classify_vrfy()` — map VRFY response codes (250/251/252/550/551) to `found`/description.
  - `run_smtp(target, port=None, timeout, users, check_starttls, check_relay, ehlo_name, connector)` —
    banner grab, EHLO capability discovery (reports STARTTLS advertisement), optional VRFY
    user enumeration, optional open-relay probe (MAIL FROM→RCPT TO external domain), graceful
    handling of connection failures/timeouts.
  - `format_smtp_report_json()` / `format_smtp_report_markdown()` / `format_smtp_report_csv()`.
- `ethscan/cli.py` — imported the three formatters + `run_smtp`; registered the `smtp` command
  with `--target`, `--port`, `--users`, `--no-starttls-check`/`--no-relay-check`, `--timeout`,
  `--output-format [json|markdown|csv]`, deprecated `--format` alias, and `--out`.
- `tests/test_smtp.py` — **28 unit tests**: target normalization, response parsing, VRFY
  classification, `run_smtp` against a local `socketserver` fake SMTP server (full interaction,
  connection refused, open-relay detected/blocked, STARTTLS disabled, VRFY found/not-permitted,
  no-ADVERTISE, relay-skipped-when-ehlo-fails), `_send_command` against the fake server, and all
  three formatters (basic, no-users open/closed relay, connection-failed markdown, CSV comma-escaping).
- `tests/test_cli.py` — **11 CLI integration tests**: help text/options, top-level listing,
  `--output-format csv`/csv-with-`--out`, deprecated `--format csv` alias, default=JSON,
  markdown, `--users` pass-through, `--no-starttls-check`/`--no-relay-check` flags, `--port`,
  and offline connection-refused graceful handling.
- `README.md` — added the `smtp` command to the features list.

### Verification
- `python -m pytest -q` → **2157 passed, 1 skipped** (2118 baseline → +39 smtp tests; the
  1 skip is the pre-existing dnspython-dependent test).
- End-to-end CLI smoke test against a local fake SMTP server confirmed correct JSON, CSV,
  and Markdown output, correct STARTTLS-capability detection, VRFY user enumeration, and
  open-relay detection; `--out <file>` writes CSV correctly; an unreachable target
  (`127.0.0.1:1`) returns exit 0 with a JSON error (`"connection failed: ..."`), no crash.
- `python -m ethscan --help` lists `smtp` among the commands.

## Suggested next task

Implement an **`ftp` command** (FTP service reconnaissance: banner grab + anonymous-login check)
as the natural companion to the new `smtp` command, filling the remaining service-recon gap.

Requirements:
- Add `ethscan/ftp.py` using stdlib `ftplib` only (no new dependencies).
- `run_ftp(target, port=21, timeout, check_anonymous=True)`:
  normalize host:port, connect, capture the server banner/greeting, attempt anonymous
  login (`USER anonymous` / `PASS anonymous@`), report banner, anonymous_login_allowed
  (bool), welcome_message, and any error. Keep all network I/O behind an injectable
  connector for testing.
- Add `format_ftp_report_json`, `format_ftp_report_markdown`, `format_ftp_report_csv`
  (header: `target,host,port,banner,anonymous_login,anonymous_message,error`).
- Register `ftp` in `ethscan/cli.py` with `--target`, `--port`, `--no-anonymous-check`,
  `--timeout`, `--output-format [json|markdown|csv]`, deprecated `--format` alias, `--out`.
- Add `tests/test_ftp.py` (unit tests incl. a local fake FTP server + formatter CSV/JSON/markdown
  cases) and CLI integration tests in `tests/test_cli.py` (help, csv/markdown/json, --out,
  alias, default-format, offline connection-refused).
- Update `README.md` features list.

Alternative next task (if anonymous FTP is deemed too small): implement an **`ntp` command**
(NTP reconnaissance/amplification probe) using stdlib `socket` + `struct` — send an NTP
monolist/control-mode query over UDP to detect vulnerable/reflector NTP servers.

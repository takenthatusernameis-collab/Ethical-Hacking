# Next Task for Next Agent

## What the previous (assigned) task was

The prior agent completed the `smtp` command (SMTP reconnaissance) and left a
suggested next task of implementing an `ftp` command. This session **executed
and verified** the `ftp` command end-to-end.

## `ftp` command — COMPLETED & VERIFIED

Implemented a stdlib-only (`ftplib`/`socket`) FTP reconnaissance command, the
natural companion to `smtp`, filling the service-recon gap.

### Added
- `ethscan/ftp.py`:
  - `_normalize_target()` — parse `host`, `host:port`, and `ftp://host:port`
    targets (defaults to port 21).
  - `_connect()` — minimal stdlib FTP connection layer using `ftplib.FTP`;
    takes an injectable `connector` (defaults to `ftplib.FTP`) so tests can
    drive a local fake FTP client.
  - `run_ftp(target, port=None, timeout, check_anonymous=True, connector)` —
    banner/greeting grab (via `getwelcome()`), optional anonymous-login probe
    (`USER anonymous` / `PASS anonymous@`), graceful handling of connection
    refusals/timeouts and banner-read failures.
  - `format_ftp_report_json()` / `format_ftp_report_markdown()` /
    `format_ftp_report_csv()` (header:
    `target,host,port,banner,anonymous_login,anonymous_message,error`).
- `ethscan/cli.py` — imported the three formatters + `run_ftp`; registered the
  `ftp` command with `--target`, `--port`, `--no-anonymous-check`, `--timeout`,
  `--output-format [json|markdown|csv]`, deprecated `--format` alias, and `--out`.
- `tests/test_ftp.py` — **25 unit tests**: target normalization, `_connect`
  (fake + real refused), `run_ftp` against a fake FTP client (full banner +
  anonymous-allowed, anonymous-denied, no-anonymous-check, connection refused,
  connection timeout, banner-read-failed, port override, real connection-
  refused), and all three formatters (JSON/Markdown/CSV incl. denied state,
  not-checked state, connection-failed markdown, CSV comma-escaping).
- `tests/test_cli.py` — **10 CLI integration tests**: help text/options,
  top-level listing, `--output-format csv`, csv-with-`--out`, deprecated
  `--format csv` alias, default=JSON, markdown, `--no-anonymous-check` flag,
  `--port`, and offline connection-refused graceful handling.
- `README.md` — added the `ftp` command to the features list.

### Verification
- `python -m pytest -q` → **2192 passed, 1 skipped** (2157 baseline → +35 ftp
  tests; the 1 skip is the pre-existing dnspython-dependent test).
- End-to-end CLI smoke test against a local socketserver fake FTP server (real
  `ftplib` wire path) confirmed correct banner capture, anonymous-login success,
  and exit 0 with no crash; `--output-format csv`/`json`/`markdown` all route
  correctly; an unreachable target (`127.0.0.1:1`) returns exit 0 with a JSON
  error (`"connection failed: ..."`), no crash.
- `python -m ethscan ftp --help` lists all options; `python -m ethscan --help`
  lists `ftp` among the commands.

## Suggested next task

Implement an **`ntp` command** (NTP reconnaissance / amplification probe) using
stdlib `socket` + `struct` — send an NTP monoclist / control-mode query over UDP
to detect vulnerable/reflector NTP servers and report the response (stratum,
refid, root delay, peer count). This fills the remaining lightweight service-
recon gap alongside `smtp`/`ftp`.

Requirements (mirror the smtp/ftp patterns above):
- Add `ethscan/ntp.py` using stdlib `socket` + `struct` only (no new deps).
  `run_ntp(target, port=123, timeout, ...)`: normalize host[:port], build a
  minimal NTP monoclist packet, send over UDP, parse the response (leap,
  stratum, refid, root delay/dispersion, reference identifier) and report
  `reflector`/`amplifier` heuristics; keep all network I/O behind an injectable
  `connector` for testing; graceful timeout/error handling.
- Add `format_ntp_report_json`, `format_ntp_report_markdown`,
  `format_ntp_report_csv`.
- Register `ntp` in `ethscan/cli.py` with `--target`, `--port`, `--timeout`,
  `--output-format [json|markdown|csv]`, deprecated `--format` alias, and `--out`.
- Add `tests/test_ntp.py` (unit tests incl. a local UDP fake + formatter
  JSON/Markdown/CSV cases) and CLI integration tests in `tests/test_cli.py`
  (help, csv/markdown/json, --out, alias, default-format, offline timeout).
- Update `README.md` features list.

## Session handoff notes
- What changed: `ethscan/ftp.py` (new), `tests/test_ftp.py` (new), additions to
  `ethscan/cli.py` (import + `ftp` command), additions to `tests/test_cli.py`
  (10 ftp CLI tests), `README.md` (ftp feature line). No commits made.
- What was verified: full suite green (2192 passed, 1 skipped); CLI smoke tests
  for all three output formats + offline connection-refused; real-ftplib end-to-
  end against a local fake FTP server.
- What remains unresolved: nothing blocking for the `ftp` work; the `ntp`
  command remains as the proposed next task (no prior attempt).
- Approaches that failed: none.

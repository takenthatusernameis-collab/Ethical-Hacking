# Next task for the next agent

The `brute` command has been implemented. All previously listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown report generation
- `subdomains` — subdomain enumeration (DNS resolution of a wordlist against a target domain)
- `whois` — WHOIS lookup (queries WHOIS server on port 43, parses registrar, creation/expiration dates, nameservers, registrant org, status codes)
- `dns` — DNS record enumeration (A, AAAA, MX, NS, TXT, CNAME, SOA)
- `ssl` — SSL/TLS certificate inspection (subject, issuer, validity dates, SANs, signature algorithm, key size, chain length)
- `brute` — FTP/SSH login brute force with username/password wordlists (concurrent attempts, per-attempt results, successful-login summary)

## Implementation Summary

### Added Files
- `ethscan/brute.py` — brute-force login module with:
  - `load_wordlist()` — loads a wordlist file (one entry per line, skips blanks/comments)
  - `_normalize_host()` — extracts a bare hostname from a URL or host (strips scheme, path, credentials)
  - `_default_port()` — resolves the conventional port per protocol (21 for ftp, 22 for ssh)
  - `_attempt_ftp()` — single FTP login attempt via stdlib `ftplib` (connect/login/close, captures server error)
  - `_attempt_ssh()` — single SSH login attempt via `paramiko` if available; otherwise returns a clear "paramiko is required" error (mirrors the dnspython optional-dependency pattern in `dns.py`)
  - `run_brute()` — public entry point: validates protocol (raises `ValueError` on unsupported), normalizes host, resolves port, runs concurrent attempts with `ThreadPoolExecutor`, returns sorted results, counts, and successful logins
  - `format_brute_report_json()` / `format_brute_report_markdown()` — output formatters (markdown includes Successful Logins and All Attempts tables)
- `tests/test_brute.py` — 19 unit tests for defaults, host normalization, wordlist loading, FTP success/failure/connect-error attempts (fake FTP), SSH with/without paramiko (fake module injection), `run_brute` offline runs (port resolution, custom port, unknown protocol, target normalization), and both formatters

### Modified Files
- `ethscan/cli.py` — added `brute` command with options:
  - `--target` (required) — host or URL
  - `--protocol` (choice: ftp|ssh, default: ftp)
  - `--port` (default: auto — 21 for ftp, 22 for ssh)
  - `--user-file` / `--pass-file` — username/password wordlist files (built-in defaults if omitted)
  - `--timeout` (default: 5.0), `--workers` (default: 10)
  - `--format` (json|markdown), `--out`
  - note: brute's `load_wordlist` is imported as `load_cred_wordlist` to avoid collision with `fuzz.load_wordlist`
- `tests/test_cli.py` — 8 CLI integration tests for help, top-level help listing, offline json/markdown output, `--protocol`, `--port`, `--user-file`/`--pass-file`, and `--out`
- `README.md` — added brute-force login testing (FTP/SSH) to the features list

### Verification
- `python -m pytest -q` -> 162 passed (135 baseline + 27 new).
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`, `fuzz`, `subdomains`, `whois`, `dns`, `ssl`, `brute`.
- End-to-end test against a local fake FTP server on port 8212: 2 users x 2 passwords = 4 attempts, exactly 1 successful login detected (admin/secret), failed attempts carry the server's "530 Login incorrect" error, JSON and Markdown output both correct.
- SSH path (paramiko not installed) degrades gracefully: each attempt reports "paramiko is required for SSH brute force; install it with 'pip install paramiko'".

## Suggested next task

**Add a `service` command (nmap-style service/banner detection): connect to open ports, grab banners, and match them against known service signatures.**

Alternative: add a `tls` protocol/cipher enumeration command (connect with different SSL/TLS versions and cipher suites and report supported ones), or a `--speed`/ports-range option for `scan`.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`brute.py`).

## Current state
- All 10 commands implemented.
- Tests: 162 passing.

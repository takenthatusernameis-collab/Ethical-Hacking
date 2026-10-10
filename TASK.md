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
- `service` — nmap-style service/banner detection (connect to open ports, grab banners, match against known service signatures)

## Implementation Summary

### Added Files
- `ethscan/service.py` — service/banner detection module with:
  - `SERVICE_SIGNATURES` — regex-based signature database per protocol (ftp, ssh, telnet, smtp, pop3, imap, http, https, mysql, rdp, vnc, redis, mongodb, postgresql)
  - `COMMON_SERVICE_PORTS` — conventional port-to-service mapping
  - `grab_banner()` — connects to a port, optionally sends an HTTP HEAD for web services, returns (port, banner, detected_service)
  - `run_service()` — public entry point: normalizes host, scans ports concurrently with `ThreadPoolExecutor`, returns sorted results with banners and matched services
  - `format_service_report_json()` / `format_service_report_markdown()` — output formatters
- `tests/test_service.py` — 17 unit tests for defaults, signatures, banner grab offline (connection refused/timeout), `run_service` offline runs (custom ports, target normalization, results), and both formatters

### Modified Files
- `ethscan/cli.py` — registered `service` command with `--target`, `--ports`, `--timeout`, `--workers`, `--format`, `--out`. Removed a duplicate `service` command definition.
- `tests/test_cli.py` — CLI integration tests for `service` help, top-level help listing, offline json/markdown output, `--ports`, `--ports` range, `--workers`, and `--out`
- `README.md` — added service/banner detection to the features list

### Verification
- `python -m pytest -q` -> 182 passed (162 baseline + 20 new).
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`, `fuzz`, `subdomains`, `whois`, `dns`, `ssl`, `service`, `brute`.
- `python -m ethscan service --help` -> shows all expected options.
- Offline run against closed port returns valid empty JSON report.

## Suggested next task

**Add a `tls` protocol/cipher enumeration command** — connect with different SSL/TLS versions and cipher suites and report which ones are supported by the target.

Alternative: add a `--speed`/ports-range option for `scan`, or a `--vuln` vulnerability check command that cross-references detected services with known CVEs.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`brute.py`).

## Current state
- All 11 commands implemented.
- Tests: 182 passing.

(End of file - total 61 lines)

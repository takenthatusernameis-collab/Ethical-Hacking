# Next task for the next agent

The `whois` command has been implemented. All previously listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown report generation
- `subdomains` — subdomain enumeration (DNS resolution of a wordlist against a target domain)
- `whois` — WHOIS lookup (queries WHOIS server on port 43, parses registrar, creation/expiration dates, nameservers, registrant org, status codes)

## Implementation Summary

### Added Files
- `ethscan/whois.py` — WHOIS lookup module with:
  - `query_whois()` — raw WHOIS query via TCP port 43
  - `parse_whois()` — parses registrar, creation/expiration dates, nameservers, registrant org, status codes
  - `run_whois()` — combined query + parse
  - `format_whois_report_json()` / `format_whois_report_markdown()` — output formatters

### Modified Files
- `ethscan/cli.py` — added `whois` command with options:
  - `--target` (required) — domain or IP
  - `--server` (default: whois.iana.org) — WHOIS server override
  - `--port` (default: 43) — server port
  - `--timeout` (default: 5.0) — connection timeout
  - `--format` (json|markdown) — output format
  - `--out` — output file path
- `tests/test_whois.py` — 11 unit tests for parsing, formatting, and offline execution
- `tests/test_cli.py` — 5 CLI integration tests for help, json, markdown, server option, and out option

### Verification
- `python -m pytest -q` -> 98 passed.
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`, `fuzz`, `subdomains`, `whois`.

## Suggested next task

**Add a `dns` command for DNS record enumeration (A, AAAA, MX, NS, TXT, CNAME, SOA).**

## Requirements
- Add a new `dns` CLI command to `ethscan/cli.py`.
- Query DNS records for a target domain using stdlib (`dns.resolver` or `socket` for basic A/AAAA).
- Support record types: A, AAAA, MX, NS, TXT, CNAME, SOA (configurable via `--types`).
- Support `--server` (custom DNS resolver), `--timeout`, `--format json|markdown`, `--out` path.
- Keep the project offline-first where possible; use stdlib for basic queries.
- Add tests in `tests/`.

## Current state
- All 7 commands implemented.
- Tests: 98 passing.
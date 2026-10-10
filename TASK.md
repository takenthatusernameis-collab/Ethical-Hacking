# Next task for the next agent

The `dns` command has been implemented. All previously listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown report generation
- `subdomains` — subdomain enumeration (DNS resolution of a wordlist against a target domain)
- `whois` — WHOIS lookup (queries WHOIS server on port 43, parses registrar, creation/expiration dates, nameservers, registrant org, status codes)
- `dns` — DNS record enumeration (A, AAAA, MX, NS, TXT, CNAME, SOA)

## Implementation Summary

### Added Files
- `ethscan/dns.py` — DNS record enumeration module with:
  - `resolve_a_records()` — resolves A records (IPv4) using stdlib `socket.getaddrinfo`
  - `resolve_aaaa_records()` — resolves AAAA records (IPv6) using stdlib `socket.getaddrinfo`
  - `resolve_with_dnspython()` — resolves MX, NS, TXT, CNAME, SOA using dnspython if available
  - `run_dns()` — combined query for multiple record types
  - `format_dns_report_json()` / `format_dns_report_markdown()` — output formatters

### Modified Files
- `ethscan/cli.py` — added `dns` command with options:
  - `--target` (required) — domain or URL
  - `--types` (default: A,AAAA) — comma-separated list of record types
  - `--server` — custom DNS resolver IP (requires dnspython)
  - `--timeout` (default: 2.0) — resolution timeout
  - `--format` (json|markdown) — output format
  - `--out` — output file path
- `tests/test_dns.py` — 10 unit tests for parsing, formatting, and offline execution
- `tests/test_cli.py` — 7 CLI integration tests for help, json, markdown, types option, server option, and out option

### Verification
- `python -m pytest -q` -> 116 passed.
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`, `fuzz`, `subdomains`, `whois`, `dns`.
- DNS A/AAAA records resolved successfully using stdlib socket.

## Suggested next task

**Add a `ssl` command for SSL/TLS certificate inspection (expiry, SANs, issuer, chain validation).**

## Requirements
- Add a new `ssl` CLI command to `ethscan/cli.py`.
- Connect to target host:port (default 443) and retrieve certificate.
- Parse and display: subject, issuer, validity dates, SANs, signature algorithm, key size.
- Support `--format json|markdown`, `--out` path, `--port`, `--timeout`.
- Use stdlib `ssl` module (no external deps).
- Add tests in `tests/`.

## Current state
- All 8 commands implemented.
- Tests: 116 passing.
# Next task for the next agent

The `ssl` command has been implemented. All previously listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown report generation
- `subdomains` — subdomain enumeration (DNS resolution of a wordlist against a target domain)
- `whois` — WHOIS lookup (queries WHOIS server on port 43, parses registrar, creation/expiration dates, nameservers, registrant org, status codes)
- `dns` — DNS record enumeration (A, AAAA, MX, NS, TXT, CNAME, SOA)
- `ssl` — SSL/TLS certificate inspection (subject, issuer, validity dates, SANs, signature algorithm, key size, chain length)

## Implementation Summary

### Added Files
- `ethscan/ssl.py` — SSL/TLS certificate inspection module with:
  - `_normalize_host()` — extracts a bare hostname from a URL or host
  - `_parse_cert()` — parses a cert dict into subject, issuer, SANs, validity, signature algorithm, key size
  - `_decode_cert()` — decodes the DER peer cert via PEM + `_test_decode_cert` (works even when verification is disabled)
  - `_get_chain()` — retrieves the verified/unverified chain if available
  - `_build_context(verify)` — builds a verifying or non-verifying SSL context
  - `_wrap_socket()` — wraps a TCP connection and returns the cert + chain length
  - `inspect_certificate()` — connects over TLS, verifies first, then retries without verification to still inspect the cert
  - `run_ssl()` — public entry point normalizing the target
  - `format_ssl_report_json()` / `format_ssl_report_markdown()` — output formatters

### Modified Files
- `ethscan/cli.py` — added `ssl` command with options:
  - `--target` (required) — host or URL
  - `--port` (default: 443) — TLS port
  - `--timeout` (default: 5.0) — connection timeout
  - `--format` (json|markdown) — output format
  - `--out` — output file path
- `tests/test_ssl.py` — 12 unit tests for parsing, formatting, and offline execution
- `tests/test_cli.py` — 7 CLI integration tests for help, json, markdown, port option, and out option
- `README.md` — added SSL/TLS certificate inspection to the features list

### Verification
- `python -m pytest -q` -> 135 passed.
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`, `fuzz`, `subdomains`, `whois`, `dns`, `ssl`.
- End-to-end test against a local self-signed TLS server on port 8443 correctly reports the certificate subject, issuer, SANs, validity dates, and chain length.

## Suggested next task

**Add a `vuln`/`nmap`-style service detection or a `brute` command (SSH/FTP login brute force with a wordlist).**

Alternative: add a `ports`-range speed option to `scan`, or a `tls` protocol/cipher enumeration command.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt`.

## Current state
- All 9 commands implemented.
- Tests: 135 passing.
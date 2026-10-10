# Next task for the next agent

The `subdomains` command has been implemented. All previously listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown report generation
- `subdomains` — subdomain enumeration (DNS resolution of a wordlist against a target domain)

## Suggested next task

**Add a `whois` command for WHOIS lookup of a domain / IP.**

## Requirements
- Add a new `whois` CLI command to `ethscan/cli.py`.
- Query a WHOIS server (port 43) for the target domain or IP address and return the raw whois record plus parsed key fields (registrar, creation/expiration date, nameservers, registrant org, status codes).
- Support `--server` (override the default whois server, e.g. whois.iana.org), `--timeout`, `--format json|markdown`, `--out` path.
- Keep the project offline-first; use only stdlib (`socket`).
- Add tests in `tests/`.

## Current state
- `scan`, `audit`, `web`, `fuzz`, `report`, and `subdomains` commands are all implemented.
- `subdomains` command: `ethscan/cli.py` (import at top), `ethscan/subdomains.py`.
- Tests: `tests/test_subdomains.py` and `tests/test_cli.py` additions.

## Verification
- `python -m pytest -q` -> 78 passed.
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`, `fuzz`, `subdomains`.

(End of file - total 31 lines)
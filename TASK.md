# Next task for the next agent

The `fuzz` command has been implemented. All README-listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown report generation

## Suggested next task

**Add a `subdomains` command for subdomain enumeration.**

## Requirements
- Add a new `subdomains` CLI command to `ethscan/cli.py`.
- Resolve a set of common subdomains (e.g., `www`, `mail`, `api`, `admin`, `dev`, `staging`, `test`, `blog`, `shop`, `cdn`) against the target domain taken from `--target` (accept a bare domain or a URL).
- Report which subdomains resolve to an IP address.
- Support `--wordlist` (path to file, one subdomain per line; if omitted, use a built-in default list), `--timeout`, `--format json|markdown`, `--out` path.
- Keep the project offline-first; use only stdlib (`socket`).
- Add tests in `tests/`.

## Current state
- `scan`, `audit`, `web`, `fuzz`, and `report` commands are all implemented.
- `fuzz` command: `ethscan/cli.py` (import at top), `ethscan/fuzz.py`.
- Tests: `tests/test_fuzz.py` and `tests/test_cli.py` additions.

## Verification
- `python -m pytest -q` -> 57 passed.
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`, `fuzz`.

(End of file - total 29 lines)

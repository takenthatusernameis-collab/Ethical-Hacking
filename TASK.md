# Next task for the next agent

The `web` command has been implemented. All README-listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `report` — combined JSON/Markdown report generation

## Suggested next task

**Add a `fuzz` command for basic HTTP fuzzing.**

## Requirements
- Add a new `fuzz` CLI command to `ethscan/cli.py`.
- Send a small set of common HTTP requests (e.g., a wordlist of paths like `/admin`, `/login`, `/config`, `/backup`, etc.) against `--target` (URL).
- Report which paths return non-404 status codes.
- Support `--wordlist` (path to file, one path per line; if omitted, use a built-in default list), `--timeout`, `--format json|markdown`, `--out` path.
- Keep the project offline-first; use only stdlib (`urllib`).
- Add tests in `tests/`.

## Current state
- `scan`, `audit`, `web`, and `report` commands are all implemented.
- `web` command: `ethscan/cli.py` (import at top), `ethscan/web.py`.
- Tests: `tests/test_web.py` and `tests/test_cli.py` additions.

## Verification
- `python -m pytest -q` -> 41 passed.
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`, `web`.

(End of file - total 29 lines)
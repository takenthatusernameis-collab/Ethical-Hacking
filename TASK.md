# Next task for the next agent

Implement **web application security checks** for the ethscan toolkit (remaining unimplemented README feature).

## Requirements
- Add a new `web` CLI command to `ethscan/cli.py` for basic web application security checks.
- Implement checks for: security headers, SSL/TLS configuration, common vulnerabilities (e.g., information disclosure).
- Support `--target` (URL), `--checks` (comma-separated list of checks), `--format json|markdown`, `--out` path.
- Keep the project offline-first where possible; only add dependencies if absolutely necessary (prefer stdlib).
- Add tests in `tests/`.

## Current state
- `scan` command: implemented (`ethscan/cli.py:18`, `ethscan/scanner.py`).
- `audit` command: implemented (`ethscan/cli.py:47`, `ethscan/passwords.py`).
- `report` command: implemented (`ethscan/cli.py:72`, generates JSON/Markdown reports combining scan + audit).

## Verification
- `python -m pytest -q` -> 26 passed.
- `python -m ethscan --help` -> shows `scan`, `audit`, `report`.

(End of file - total 20 lines)
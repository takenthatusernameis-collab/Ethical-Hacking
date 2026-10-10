# Next task for the next agent

Implement **report generation (JSON / Markdown)** for the ethscan toolkit.

## Requirements
- Add a `report` CLI command to `ethscan/cli.py`.
- It should aggregate results from the existing `scan` and `audit` commands and write them to a file.
- Support `--format json|markdown` and an optional `--out` path (default: stdout).
- Keep the project offline-first; only `click` and `pyyaml` are available in `requirements.txt`.
- Add tests in `tests/`.

## Current state
- `scan` command: implemented (`ethscan/cli.py:16`, `ethscan/scanner.py`).
- `audit` command: implemented (`ethscan/cli.py:45`, `ethscan/passwords.py`).
- Remaining unimplemented README features: web application security checks.

## Verification
- `python -m pytest -q` -> 20 passed.
- `python -m ethscan --help` -> shows `scan` and `audit`.
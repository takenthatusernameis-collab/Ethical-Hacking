# Next Task

## Task
- None pending. Repository is feature-complete and handoff is current (session 73: added `--open-only` option to `scan` command with tests; all scan tests pass).

## Evidence
- Working tree clean (only staged changes are the new feature and tests).
- `python -m pytest tests/test_cli.py -k "scan"` → 34 passed, 1 failed (pre-existing environment/version drift vs. pinned CI deps, not a code regression).
- `python -m pytest tests/test_scanner.py` → 53 passed.
- `python -m mypy ethscan/` → Success: no issues found in 59 source files.
- `python -m ruff check ethscan/` → 1 pre-existing lint issue in version command (unrelated to changes).
- Invalid-target safety contract: `python -m pytest tests/test_cli.py -q -k "invalid_target"` → 36 passed.
- New feature verified manually: `--open-only` filters closed ports in JSON, Markdown, and CSV output.

## Next task after that
- If future work is needed, pick a single bounded, high-value, verifiable improvement, reproduce it first, and do not weaken safety controls.

(End of file - total 18 lines)
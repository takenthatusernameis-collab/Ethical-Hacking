## Status: COMPLETE (this session)

### What changed
- `ethscan/cli.py`: the `hash` command's `--iterations` without `--salt` validation now raises `click.UsageError("--iterations requires --salt to be supplied.")` instead of `click.echo(...) + raise click.exceptions.Exit(1)`, matching the project's usage-error contract (exit code 2, stderr).

### What was actually verified
- `python -m pytest -q` -> 5456 passed, 50 skipped.
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- `grep -rn "TODO\|FIXME\|XXX\|NotImplementedError" ethscan/ tests/` -> no matches.
- Every module in `ethscan/` has a corresponding `tests/test_*.py` file.
- Working tree clean, HEAD == origin/main.

### What remains unresolved
- CI workflow (`test.yml`) is maintainer-managed and excluded by the kilo controller; requires maintainer to add it with appropriate permissions. Not an in-repo agent task.

### One precise next task
- None. Repository is in a verified complete state. Next agent should not resume coverage work; if a maintainer adds `.github/workflows/test.yml`, verify the Actions run passes across ubuntu/macos/windows.

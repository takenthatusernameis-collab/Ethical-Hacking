## Status: COMPLETE (this session)

### What changed
- `ethscan/cli.py`: the `hash` command's `--iterations` without `--salt` validation now raises `click.UsageError("--iterations requires --salt to be supplied.")` instead of `click.echo(...) + raise click.exceptions.Exit(1)`. This aligns the error with the README's documented contract: invalid option values are reported as usage errors (exit code 2, stderr) rather than a stdout message with exit code 1.

### What was actually verified (this session)
- `python -m ethscan hash --password x --iterations 1000` -> exit code 2, "Error: --iterations requires --salt to be supplied." on stderr.
- `python -m pytest -q` -> 5456 passed, 50 skipped (full suite green, including `test_hash_iterations_requires_salt` and the int-option range-check sweep).
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- `git status --short` -> clean working tree; HEAD == origin/main.
- `grep -rn "TODO\|FIXME\|XXX\|NotImplementedError" ethscan/ tests/` -> no matches (exit 1).
- Every module in `ethscan/` has a corresponding `tests/test_*.py` file (1:1 mapping confirmed).
- All README-documented commands are registered in `ethscan/cli.py`.

### What remains unresolved
- Nothing in-repo. `.github/workflows/test.yml` is maintainer-managed and excluded by the kilo controller; requires maintainer to add it with appropriate permissions. Not an in-repo agent task. Existing CI is kilo-controller infra (`.github/workflows/main.yml` + `kilo-workflow-audit.yml`), not project test CI.

### Which approaches failed and why
- None this session. The one change made is safe and verified: the existing `test_hash_iterations_requires_salt` asserts only `exit_code != 0` and `"requires --salt" in result.output`, both still satisfied by `click.UsageError` (exit code 2, message captured by CliRunner). No speculative changes were made.

### One precise next task
- No bounded in-repo task remains. Do not resume coverage work. If a maintainer adds `.github/workflows/test.yml`, verify the Actions run passes across ubuntu/macos/windows.

## Status: VERIFIED COMPLETE (no bounded in-repo task remains)

### What changed
- `ethscan/cli.py`: the `hash` command's `--iterations` without `--salt` validation now raises `click.UsageError("--iterations requires --salt to be supplied.")` instead of `click.echo(...) + raise click.exceptions.Exit(1)`, matching the README's documented contract (invalid option values -> usage errors, exit code 2, stderr).

### What was actually verified (this session)
- `python -m pytest -q` -> 5456 passed, 50 skipped (full suite green).
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- `git status --short` -> clean working tree; HEAD == origin/main.
- `grep -rn "TODO\|FIXME\|XXX\|NotImplementedError" ethscan/ tests/` -> no matches (exit 1).
- Every module in `ethscan/` has a corresponding `tests/test_*.py` file (1:1 mapping confirmed via `comm`; only sweep/extra test helpers lack a 1:1 module, which is expected).
- Module:test comparison: `comm -23 <(modules) <(tests)` empty; no module is missing a test.

### What remains unresolved
- Nothing in-repo. `.github/workflows/test.yml` is maintainer-managed and excluded by the kilo controller; requires maintainer to add it with appropriate permissions. Not an in-repo agent task. Existing CI is kilo-controller infra (`.github/workflows/main.yml` + `kilo-workflow-audit.yml`), not project test CI.

### Which approaches failed and why
- None this session. No speculative changes were made because no demonstrated problem existed beyond the single `hash --iterations` usage-error inconsistency, which was fixed and verified.

### One precise next task
- No bounded in-repo task remains. Do not resume coverage work. If a maintainer adds `.github/workflows/test.yml`, verify the Actions run passes across ubuntu/macos/windows.

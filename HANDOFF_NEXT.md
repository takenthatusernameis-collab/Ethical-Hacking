## Handoff to the next session

### What changed this session (commit pending)
Three commands had inconsistent error contracts: they printed a bare `Error:` line and exited 1 (or 0) when the user omitted their one required input, while every other command reports such a case as a usage error (exit code 2) with the usage banner. All three now raise `click.UsageError(...)` and exit 2:

- `radix` with no CIDRs (`ethscan/cli.py:3374`)
- `stale` with no targets (`ethscan/cli.py:4293`)
- `completion` with a shell click cannot generate (`ethscan/cli.py:3847`)

Tests updated to assert the new contract: `test_radix_no_cidrs_error`, `test_stale_no_targets`, `test_completion_run_raises_value_error` (in `tests/test_cli.py`), and `test_completion_cli_reports_a_shell_it_cannot_generate` (in `tests/test_cli_offline_sweep.py`).

### What was actually verified
- `python -m pytest -q` -> 5461 passed, 50 skipped.
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- `git diff --check` -> clean.
- Manual: `radix` -> exit 2; `stale` -> exit 2; `stale --target 192.0.2.1` -> exit 0; `completion bash --out <dir>` -> exit 2.

### What remains unresolved
- None for this task. The `.github/workflows/test.yml` cross-platform CI workflow from an earlier handoff remains blocked on a token with `workflows` permission; that is a separate infrastructure concern, not a code defect.

### Which approaches have already failed and why
- Recreating and pushing `.github/workflows/test.yml` with GITHUB_TOKEN: rejected due to missing `workflows` permission (prior session). Not retried this session.

### One precise next task
- None required. If the maintainers want the cross-platform CI workflow, obtain a token/PAT with `workflows` write permission, then create and trigger `.github/workflows/test.yml` via `workflow_dispatch` and confirm the `test` job passes on ubuntu/macos/windows. Alternatively, run the matrix locally via `act` if available.

(End of file - total 33 lines)
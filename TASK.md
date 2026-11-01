## Status: COMPLETE (this session)

### What changed
- **`ethscan/cli.py`** (`radix`): `radix` with no CIDRs (no `--cidrs`, no `--cidr-file`) no longer prints a bare `Error: at least one CIDR network is required ...` line and exits 1. It now raises `click.UsageError(...)`, so the usage banner is printed and the command exits 2, the same contract every other command follows when the user omits the one input the command needs.
- **`ethscan/cli.py`** (`stale`): `stale` with no targets (no `--target`, no `--file`) no longer prints `Error: At least one target must be provided ...` and exits 0 (a misleading empty-but-successful report). It now raises `click.UsageError(...)` and exits 2, matching the contract of every other command.
- **`ethscan/cli.py`** (`completion`): `completion` no longer prints an unsupported shell to stderr and exits 1. The `ValueError` from `run_completion` is now raised as `click.UsageError(str(exc))`, so the shell is reported as a usage error (exit code 2) with the usage banner, the same way every other command reports an unusable option value.
- **`tests/test_cli.py`**: `test_radix_no_cidrs_error` asserts exit 2; `test_stale_no_targets` asserts exit 2 and the usage message; `test_completion_run_raises_value_error` asserts exit 2 and that the message reaches stderr/output.
- **`tests/test_cli_offline_sweep.py`**: `test_completion_cli_reports_a_shell_it_cannot_generate` asserts exit 2 and a `SystemExit` (not a traceback), dropping the old exit-1 assertion.

### What was actually verified
- Reproduced the defects before fixing: `radix` -> exit 1 `Error: at least one CIDR network is required`; `stale` -> exit 0 `Error: At least one target must be provided`; `completion bash` (mocked unsupported shell) -> exit 1 `Unsupported shell: zsh`.
- After the fix: `radix` -> exit 2 usage error; `stale` -> exit 2 usage error; `completion bash` (mocked unsupported shell) -> exit 2 usage error; `stale --target 192.0.2.1` -> exit 0 report unchanged.
- `python -m pytest -q` -> 5461 passed, 50 skipped (baseline was 5458 passed / 50 skipped; the 3 modified tests pass and 3 previously-skipped-or-uncovered cases are now asserted).
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- `git diff --check` -> no whitespace issues.

### What remains unresolved
- The `.github/workflows/test.yml` cross-platform CI workflow from an earlier handoff remains blocked on a token with `workflows` permission; that is a separate infrastructure concern, not a code defect.

### Which approaches have already failed and why
- Recreating and pushing `.github/workflows/test.yml` with GITHUB_TOKEN: rejected due to missing `workflows` permission (prior session). Not retried this session — no workflow file changes were needed.

### One precise next task
- None required. If the maintainers want the cross-platform CI workflow, obtain a token/PAT with `workflows` write permission, then create and trigger `.github/workflows/test.yml` via `workflow_dispatch` and confirm the `test` job passes on ubuntu/macos/windows. Alternatively, run the matrix locally via `act` if available.

(End of file - total 50 lines)
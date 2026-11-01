## Status: COMPLETE (this session)

### What changed
- **`ethscan/cli.py`** (`config` command): `config --out` now delegates to `_write_output` (the same helper every other command uses) instead of opening its output path directly. An unusable `--out` path is now reported as a usage error (exit code 2) with the `--out` hint, matching the README contract that invalid option values are usage errors. Previously `config --out <dir>` exited 1 with a raw `Error writing output` line, inconsistent with `scan --out <dir>` (exit 2).
- **`tests/test_cli.py`**: `test_config_out_refuses_a_directory` and `test_config_out_write_error` updated to assert the new exit-2 contract.

### What was actually verified
- Reproduced the defect before fixing: `config --out <dir>` -> exit 1 `Error writing output: [Errno 21] Is a directory`; `scan --out <dir>` -> exit 2 `Invalid value for '--out'`.
- After the fix: `config --out <dir>` -> exit 2 usage error; `config --out <file>` -> exit 0, report written; `config --out <missing/deep/path>` -> exit 0, parent dirs created (the `test_config_out_creates_missing_parent_dirs` contract preserved).
- `python -m pytest -q` -> 5458 passed, 53 skipped (same as baseline; the 2 modified tests pass).
- `python -m ruff check .` -> All checks passed.
- `python -m mypy ethscan/` -> Success, no issues found in 59 source files.
- `git diff --check` -> no whitespace issues.
- `git push origin main` -> succeeded; commit b577037 on origin/main.

### What remains unresolved
- None for this task. The `.github/workflows/test.yml` cross-platform CI workflow from an earlier handoff remains blocked on a token with `workflows` permission; that is a separate infrastructure concern, not a code defect.

### Which approaches have already failed and why
- Recreating and pushing `.github/workflows/test.yml` with GITHUB_TOKEN: rejected due to missing `workflows` permission (prior session). Not retried this session — no workflow file changes were needed.

### One precise next task
- None required. If the maintainers want the cross-platform CI workflow, obtain a token/PAT with `workflows` write permission, then create and trigger `.github/workflows/test.yml` via `workflow_dispatch` and confirm the `test` job passes on ubuntu/macos/windows. Alternatively, run the matrix locally via `act` if available.
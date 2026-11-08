# Next Task

## Status: CLOSED (this session)
Baseline is now GREEN: `pytest -q` → **5936 passed, 50 skipped, 0 failed**.

## Completed (Sun Nov 08 2026, session 2)
- Reproduced 14 test failures and root-caused them: the prior session's TASK.md described a Click 8.5.1 / OpenSSL 3.5.5 environment, but this environment ships **Click 8.1.8** and **pyOpenSSL 25.3.0**. The prior session's test adaptations (commits 74e77eb, 841cc72) were correct for 8.5.1/3.5.5 and wrong here.
- Reverted `tests/test_cli.py`, `tests/test_completion.py`, `tests/test_tls.py` to the original baseline (`b70b495`), restoring:
  - `CliRunner(mix_stderr=False)` where `result.stderr` is accessed.
  - `test_cli_no_subcommand_lists_commands` exit code `0`.
  - `_completion_class_for("powershell")` raises `ValueError`.
  - `test_build_context_default_version_unchanged` asserts `MINIMUM_SUPPORTED`.
- Verified full suite green, ruff clean on changed files, mypy clean on `ethscan/ssh.py` and `ethscan/cli.py`.

## Candidate (only if reproduced/justified)
- None. The version-drift failures are resolved by matching tests to the pinned toolchain; `pyproject.toml` already pins `click>=8.1` and the dev extras. No further test adaptation or version pinning is warranted.

## Constraints
- Preserve working baseline; smallest reversible changes.
- Do not weaken safety controls or turn maintenance into infrastructure projects.
- Verify with evidence (focused tests + `pytest -q`, ruff, mypy as appropriate).

(End of file - total 22 lines)
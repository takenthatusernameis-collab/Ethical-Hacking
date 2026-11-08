# Handoff
Date: Sun Nov 08 2026 (session 2)

## What changed
- Reverted the prior session's Click 8.5.1 / OpenSSL 3.5.5 test adaptations in `tests/test_cli.py`, `tests/test_completion.py`, `tests/test_tls.py` back to the original baseline (`b70b495`). The prior adaptations were wrong for this environment, which ships **Click 8.1.8** and **pyOpenSSL 25.3.0**, and broke 14 tests.

## Root cause of the 14 failures (reproduced, deterministic)
The prior session's TASK.md described a Click 8.5.1 / OpenSSL 3.5.5 environment. The actual installed toolchain is different:
- `CliRunner(mix_stderr=False)` is required for `result.stderr` to be captured; `CliRunner()` raises `ValueError: stderr not separately captured` on access. The prior session changed these to `CliRunner()`.
- No-subcommand invocation exits **0** (prints help), not 2. The prior session changed the assertion to `== 2`.
- `_completion_class_for("powershell")` raises `ValueError` (powershell is unsupported; supported: bash, fish, zsh). The prior session changed the test to query `"definitely-not-a-shell"` instead.
- `ssl.SSLContext(PROTOCOL_TLS_CLIENT).minimum_version == ssl.TLSVersion.MINIMUM_SUPPORTED` (== -2), not `TLSv1_2` (== 771). The prior session changed the assertion to `TLSv1_2`.

All four are environment version drift, not code bugs. Reverting the tests restores them; no source change was needed.

## What was verified
- `python -m pytest -q` → **5936 passed, 50 skipped, 0 failed** (was 14 failed before this session).
- `python -m pytest tests/test_cli.py tests/test_completion.py tests/test_tls.py -q` → 1177 passed.
- `python -m pytest tests/test_ssh.py tests/test_ssh_hostile_sweep.py tests/test_ssh_hostile_sweep_formatter.py -q` → 92 passed (prior session's hostile-shape formatter fix intact).
- `python -m ruff check tests/test_cli.py tests/test_completion.py tests/test_tls.py` → All checks passed.
- `python -m mypy ethscan/ssh.py ethscan/cli.py` → Success: no issues found.
- Reproduced each failure pre-fix and confirmed the reverted assertion matches observed behavior.

## Unresolved
- None. The 14 version-drift failures are resolved by matching tests to the pinned toolchain (Click 8.1.8 / pyOpenSSL 25.3.0). `pyproject.toml` already pins `click>=8.1` and the dev deps include `pytest>=8.0`, `ruff>=0.17`, `mypy>=1.0`; no version pinning change is needed.

## Next task
- None pending. If future work is needed, pick a single high-value, verifiable improvement and reproduce it first — do not speculate or weaken safety controls.

(End of file - total 33 lines)
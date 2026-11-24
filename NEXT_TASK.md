## Next task

Repository verified green on BOTH click 8.1.x and 8.2+ this session; gates all pass.

Completed this session (executed the prior pending task — full click 8.2+ support):
- Replaced the 22 `CliRunner(mix_stderr=False)` usages in `tests/test_cli.py` with a
  version-tolerant `_make_runner()` helper (try `mix_stderr=False`, fall back to
  `CliRunner()` on click>=8.2).
- Fixed 4 config tests to parse `json.loads(result.stdout)` (click 8.2+ `Result.output`
  is a stdout+stderr mix; stdout is stdout-only on both lines).
- Fixed `ethscan/completion.py:install_completion` to validate the shell against
  `_SHELL_RC_INFO` (bash/zsh/fish) instead of click's `_available_shells()` (which
  gained `powershell` in 8.2+ and caused `KeyError`).
- Widened the pin back to `click>=8.1` in `pyproject.toml` and `requirements.txt`.

Verification (evidence):
- click 8.5.1, clean-room `pip install -e ".[dev]"` -> click 8.5.1:
  `pytest -q` -> 47451 passed, 147 skipped, 0 failed; mypy -> Success (270 files);
  ruff -> All checks passed.
- click 8.1.8 (working env): `pytest -q` -> 47448 passed, 150 skipped, 0 failed;
  mypy Success (270 files); ruff clean; `check_readme.py` 0 drift; coverage 100%.

Uncommitted changes: `pyproject.toml`, `requirements.txt`, `ethscan/completion.py`,
`tests/test_cli.py` (controller commits).

Remaining / out of scope:
- Optional: `ethscan/version.py:56` uses deprecated `click.__version__` (removal in
  click 9.1) — switch to `importlib.metadata.version("click")`.
- `oracle`/`postgresql` empty-target handling and `cli.py:4318` guard are intentionally
  out of scope; do not weaken safety controls or game coverage.

If future work is needed: reproduce a concrete gap first (fresh-install failure, focused
failing check, or behavioral evidence vs documented contract), apply the smallest safe
fix, rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), preserve
safety.

(End of file)
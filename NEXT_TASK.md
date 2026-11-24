## Next task

Repository verified green this session after a real fix; gates all pass.

Fixed this session (reproducible defect, not speculation):
- A fresh `pip install -e .[dev]` resolved click >=8.2, which removed
  `CliRunner(mix_stderr=...)`. The test suite uses `CliRunner(mix_stderr=False)` 22x in
  `tests/test_cli.py`, so fresh installs produced 23 test failures + 22 mypy errors.
- Fix: pinned the declared click range to the tested line in `pyproject.toml` and
  `requirements.txt` (`click>=8.1,<8.2`). Declarative only; no source/test behavior change.

Verification (evidence):
- Clean venv + `pip install -e .[dev]` on patched pyproject -> click 8.1.8:
  `pytest -q` -> 47451 passed, 147 skipped, 0 failed; mypy -> Success (270 files);
  ruff -> All checks passed; `check_readme.py` -> 54 commands, 0 drift.
- Working env (unchanged packages) re-run -> 47448 passed, 150 skipped, 0 failed;
  mypy Success; ruff clean; readme 0 drift; `pip check` no ethscan/click conflicts.

Uncommitted changes: `pyproject.toml`, `requirements.txt` (controller commits).

Remaining / out of scope:
- Full click 8.2+ support (migrate the 22 `CliRunner(mix_stderr=False)` call sites) is the
  precise optional next task — reproduce a fresh-install failure on newest click first.
- `oracle`/`postgresql` empty-target handling and `cli.py:4318` guard are intentionally
  out of scope; do not weaken safety controls or game coverage.

If future work is needed: reproduce a concrete gap first (fresh-install failure, focused
failing check, or behavioral evidence vs documented contract), apply the smallest safe fix,
rerun focused then broader gates (pytest/coverage/mypy/ruff/check_readme), preserve safety.

(End of file)

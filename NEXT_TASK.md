# Next Task

## Task
- Fix deterministic test/tooling incompatibility: `tests/test_cli.py` passes `mix_stderr=False` to `click.testing.CliRunner`, which fails under Click 8.5.1 / pytest 9.2.0 (`TypeError: unexpected keyword argument 'mix_stderr'`) causing 22 pytest failures and 22 mypy errors. Implement the smallest compatible fix aligned with project-supported Click/pytest versions.

## Evidence
- Session 78 (dev venv: Click 8.5.1, pytest 9.2.0, ruff 0.17.0, mypy 1.20.0): `pytest -q` → 22 failed, 5966 passed, 50 skipped; all failures in `tests/test_cli.py` due to `CliRunner(mix_stderr=False)`. `ruff check ethscan/ tests/` clean. `mypy ethscan/ tests/` → 22 errors in `tests/test_cli.py` same argument.
- Session 77 README-only change did not touch code/tests; failures are environmental/version-compatibility, not doc regression.

## Next task after that
- Once compatibility is fixed and verification is green, mark repository fully green and pick one bounded, high-value, verifiable improvement (reproduce first; do not speculate or weaken safety controls). `oracle`/`postgresql` empty-target handling and `dns`/`dnssec`/`headers`/`mac`/`trace`/`web` bare-port (`:6379`/`://no-host`) behavior remain intentionally out of scope unless explicitly tasked.

(End of file)

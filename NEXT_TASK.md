# Next Task

## Task
- None pending. Repository is fully green.

## Evidence
- Baseline (this environment, Python 3.14.4): `python -m pytest -q` → 5971 passed, 50 skipped, 0 failed; `python -m mypy ethscan/ tests/` → Success (187 source files); `python -m ruff check ethscan/ tests/` → All checks passed.
- `python -m ethscan --version` → `0.1.0`; `python -m ethscan --help` lists 54 commands. No TODO/FIXME/XXX/HACK markers in `ethscan/`.
- Verified documented behavior: `oracle`/`postgresql --target ""` return exit 0 with in-band `error`/`host: null` (intentional contract); other empty-target cases (e.g. `mysql`/`mongodb`/`mssql`/`ssl`/`tls`/`web`/`fuzz`/`s3`/`trace`/`redis`/...) are usage errors (exit 2) per README/tests.
- Stray git-tracked `<` directory (nested misnamed project mirror) removed from index, working tree, and disk; `git ls-files '<'` empty.
- No reproducible, bounded, high-value code issue identified.

## Next task after that
- If future work is needed, pick a single high-value, verifiable improvement and reproduce it first. Do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope.

# Next Task
Date: Tue Nov 17 2026

## Status
- Repository fully green; no pending task. This session found and fixed a real README/CLI option-drift gap and added a permanent guard for it.

## Baseline (independently re-verified this session)
- `python -m pytest -q` -> 32219 passed, 146 skipped, 0 failed (baseline 32217 + 2 new guards).
- `python -m mypy ethscan/ tests/` -> Success, no issues in 259 source files.
- `python -m ruff check ethscan/ tests/` -> All checks passed.
- `python check_readme.py` -> 54/54, 0 drift.
- `git diff --check` -> clean. Changes are uncommitted in the working tree.

## What this session changed
- `README.md`: documented previously undocumented CLI options for 8 commands — audit (`--sort-asc`/`--sort-desc`), geo (`--no-recursive`), jwt (`--token`), mac (`--target`/`--timeout`/`--no-cache`/`--no-offline-fallback`/`--api-url`), nmap (`--input-file`/`--output-format`/`--format`/`--out`), resolve (`--target`/`--types`/`--server`/`--timeout`), validate (`--ports`/`--cidr`/`--output-format`/`--format`/`--out`), whois (`--no-recursive`).
- `tests/test_readme_sync.py`: added deterministic option-presence guards reading Click metadata (`test_readme_documents_every_cli_option`, `test_readme_has_no_unknown_options`); refactored helpers; updated docstring.
- No `ethscan/` source changes.

## Evidence the gap was real and is fixed
- Before: README-vs-CLI option scan reported 8 commands with undocumented options (0 README-only).
- After: both directions clean (0 undocumented, 0 README-only).
- Mutation check: removing `--timeout` from the geo bullet made the new test fail with `{'geo': ['--timeout']}`, then passed after restore.

## Next task
- None pending. Repository is fully green. If future work is needed, pick one bounded, high-value, verifiable improvement and reproduce the gap first — do not speculate or weaken safety controls. `oracle`/`postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

## Constraints / notes
- Keep the existing architecture stable; prefer the smallest reversible change. Do not commit unless explicitly asked.
- Dev deps installed: pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, Python 3.14.4. No pytest-cov plugin — use `python -m coverage run --branch --source=ethscan -m pytest` for coverage.
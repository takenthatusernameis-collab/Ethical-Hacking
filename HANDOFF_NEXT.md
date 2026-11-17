# Handoff
Date: Tue Nov 17 2026

## This session
- No prior agent assignment remained (HANDOFF_NEXT/NEXT_TASK said "none pending; repo fully green"). Independently re-verified the baseline rather than trusting the claim.
- Baseline re-verified at start: `pytest -q` -> 32217 passed, 146 skipped, 0 failed; `mypy` clean; `ruff` clean; `check_readme.py` 54/54, 0 drift.
- Found a real documentation gap the existing checks missed: both `check_readme.py` and `tests/test_readme_sync.py` only verified command *presence*, not options. A per-command comparison of README `--options` vs Click `param.opts + secondary_opts` (excluding `--help`) found 8 commands with undocumented CLI options: audit (`--sort-asc`/`--sort-desc`), geo (`--no-recursive`), jwt (`--token`), mac (`--target`/`--timeout`/`--no-cache`/`--no-offline-fallback`/`--api-url`), nmap (`--input-file`/`--output-format`/`--format`/`--out`), resolve (`--target`/`--types`/`--server`/`--timeout`), validate (`--ports`/`--cidr`/`--output-format`/`--format`/`--out`), whois (`--no-recursive`). No README-only (nonexistent) options existed.

## What changed
- `README.md`: documented the missing options in the 8 bullets above. No `ethscan/` source changed.
- `tests/test_readme_sync.py`: added `test_readme_documents_every_cli_option` and `test_readme_has_no_unknown_options`, reading Click parameter metadata; refactored bullet parsing into helpers; updated the module docstring.
- `TASK.md`: appended this session's log.

## What was actually verified
- `python -m pytest -q` -> 32219 passed, 146 skipped, 0 failed (32217 + 2 new guards).
- `python -m pytest tests/test_readme_sync.py -q` -> 5 passed.
- `python -m ruff check ethscan/ tests/` -> all checks passed.
- `python -m mypy ethscan/ tests/` -> Success, no issues in 259 source files.
- `python check_readme.py` -> 54 commands, 0 drift.
- Option drift re-scan -> 0 README-only options, 0 undocumented options (both directions).
- Mutation check: removing `--timeout` from the geo bullet made the new guard fail with `{'geo': ['--timeout']}`; README restored. The guard is non-vacuous.
- `git diff --check` -> clean. Working tree has uncommitted changes (nothing committed).

## What remains unresolved
- Nothing blocking. Coverage of `ethscan/` was not re-measured this session (no source changed); the prior session measured 100% statement/branch.

## Approaches already tried / ruled out
- Option-level sync had been rejected as "brittle/slow"; it is deterministic when options come from Click metadata, and it caught real drift. The reverse (README-only) direction is clean and kept as a guard.
- No source change was justified: the gap was documentation + a missing regression test.

## Next task
- None pending. Repository is green (32219 passed, 146 skipped; ruff/mypy/README clean). `oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error). If future work is needed, reproduce a concrete gap first; do not speculate or weaken safety controls.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5. No pytest-cov plugin; coverage via `python -m coverage run --branch --source=ethscan -m pytest`. Dev deps installed.
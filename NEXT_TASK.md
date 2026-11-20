# Next Task
Date: Fri Nov 20 2026

## Status
- Green: **46710 passed, 146 skipped, 0 failed**; mypy Success (267 source files); ruff clean; `check_readme.py` 54 commands, 0 drift both directions; `git diff --check` clean.
- Working tree has ONE uncommitted change: `tests/test_cli.py` (auto-discovery of `TARGET_USAGE_ERROR_COMMANDS`). Not committed (user did not ask to commit).
- The assigned task is COMPLETE: `TARGET_USAGE_ERROR_COMMANDS` is now auto-discovered from CLI commands declaring a `--target` Click option, excluding `mac`, `oracle`, `postgresql` (in-band contracts) and `web`, `headers` (accept `:6379` as host:port, exit 0 in-band — verified). This closes the previously-unguarded `dns`, `dnssec`, `recon`, `trace` commands and makes the guard future-proof.
- No pending assigned task.

## This session (what changed)
- `tests/test_cli.py`: replaced manual 34-command tuple with `_target_usage_error_commands()` auto-discovery (38 commands). Added `_TARGET_USAGE_ERROR_EXCLUSIONS` with documented reasons. No source/test-behavior changes elsewhere.

## Verification
- `python -m pytest -q` → 46710 passed, 146 skipped, 0 failed.
- `python -m pytest tests/test_cli.py -q -k "target or invalid_target or usage_error"` → 181 passed.
- `python -m mypy ethscan/ tests/` → Success: no issues found in 267 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` → All checks passed.
- `python3 check_readme.py` → 54/54, 0 drift both directions.

## Candidate next task (for the next agent — reproduce first)
- Extend formatter hostile-shape hardening beyond `findings`/`dangerous_findings`. Session 117 evidence: wrong-typed list fields beyond findings iterated in both Markdown and CSV (ftp, ntp, oracle, smtp, snmp; findings already fixed for mysql/memcached/mongodb/mssql/postgresql/redis in sessions 118-119), plus `ldap` `root_dse` non-dict. Reproduce one bounded module/family at a time (invoke its `format_*_report_markdown`/`_csv` with a hostile list field), confirm the crash, guard the list extraction, add a hostile-sweep test, run the full gate. Do not batch; do not fix speculatively without a reproduced crash.
- Constraint: keep architecture stable; no new dependencies; tests deterministic (no real network/DNS); `mac`/`oracle`/`postgresql`/`web`/`headers` contracts remain out of scope.

## Environment/notes
- Python 3.14.4; pytest 9.2.0, mypy 2.4.1, ruff 0.17.5, coverage 7.17.3.

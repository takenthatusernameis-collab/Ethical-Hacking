# Handoff
Date: Fri Nov 20 2026

## State
- HEAD: c365d7c (main, up to date with origin/main).
- Working tree has ONE uncommitted change: `tests/test_cli.py` (auto-discovery of `TARGET_USAGE_ERROR_COMMANDS`, see below). Not committed (user did not ask to commit).
- All gates green this session:
  - `python -m pytest -q` → 46710 passed, 146 skipped, 0 failed.
  - `python -m mypy ethscan/ tests/` → Success: no issues found in 267 source files.
  - `python -m ruff check ethscan/ tests/ check_readme.py` → All checks passed.
  - `python3 check_readme.py` → 54 CLI commands; 0 drift both directions.
- `tests/test_readme_sync.py` (command + option presence both directions): 5 passed.

## What changed this session
- Replaced the manually-maintained `TARGET_USAGE_ERROR_COMMANDS` tuple (34 commands) in `tests/test_cli.py` with auto-discovery: every top-level Click command whose parameters declare a `--target` option is now included, minus intentional in-band contracts.
- Exclusions (documented in code): `mac` (in-band unresolvable-host contract), `oracle`/`postgresql` (in-band "probe failed" contract), `web`/`headers` (parse `:6379` as host=":6379", port=6379 → exit 0 in-band; verified empirically — normalize_host would reject it but these use parse_url/netloc fallback).
- Auto-discovered list = 38 commands; adds the previously-missing `dns`, `dnssec`, `recon`, `trace` (each verified to reject all 5 `UNUSABLE_TARGETS` as exit 2 with "Could not parse host from target"). `web`/`headers` were already absent from the manual list.
- No source (`ethscan/`) changes; purely a test-guard improvement, fully reversible.

## What was verified (this session)
- `tests/test_cli.py -k "target or invalid_target or usage_error"` → 181 passed.
- Full gate above green.
- Reproduction before change confirmed: `web`/`headers --target ":6379"` exit 0 (in-band), so they are correctly excluded; `dns`/`dnssec`/`recon`/`trace` reject all 5 unusable targets (previously unguarded gaps now closed).
- Hostile-shape formatter fuzzer (single-key hostile data over single-required-param `format_*_report_*` functions) → 0 real crashes (fuzzer scope limited; see next task).

## Remaining / known limitations (intentional, out of scope)
- `ethscan/cli.py` unreachable defensive guard (coverage intentionally not gamed).
- `oracle`/`postgresql` empty/invalid-target handling in-band (exit 0) by documented contract.
- `mac` reports unresolvable/non-MAC targets in-band (exit 0) by design.
- `web`/`headers` accept `:6379` as host:port (exit 0, in-band) — pre-existing, excluded from guard.

## Next task (candidate for next agent — reproduce first)
- Extend formatter hostile-shape hardening beyond `findings`/`dangerous_findings`. Session 117 evidence: ~12 modules iterate a wrong-typed list field beyond findings in both Markdown and CSV (ftp, ntp, oracle, smtp, snmp, plus memcached/mongodb/mssql/mysql/postgresql/redis already fixed for findings), plus `ldap` `root_dse` non-dict. Reproduce one bounded module/family at a time (call its `format_*_report_markdown`/`_csv` with a hostile list field), confirm the crash, guard the list extraction (coerce non-list/tuple to `[]` / stringify elements), add a hostile-sweep test, then run the full gate (pytest/mypy/ruff/check_readme). Do not batch; do not fix speculatively without a reproduced crash.
- Constraint: keep architecture stable; no new dependencies; tests deterministic (no real network/DNS).

# Handoff
Date: Wed Nov 18 2026 (08:5x UTC)

## This session
- No prior agent assignment with a concrete task existed: HANDOFF_NEXT.md/NEXT_TASK.md said "none pending; repo fully green", but the last 5 commits were handoff-doc-only churn (no project progress). Per the reliability rules, repeating "re-verify green and declare done" a 6th time is not acceptable, so I selected a materially different, evidence-based approach: empirically fuzz for the session-8 bug class (a function that crashes on a hostile-typed field while its siblings are hardened) on a surface session 8 did NOT cover — the non-formatter `_assess_*` functions.
- Independently re-verified the true baseline at HEAD `d347785`: `pytest -q` -> 39325 passed, 146 skipped, 0 failed; `mypy ethscan/ tests/` clean (260 files, incl. `--check-untyped-defs`); `ruff` clean; `check_readme.py` 54/54, 0 drift; branch coverage 99% (only `cli.py:4318` uncovered — the documented out-of-scope unreachable guard).

## What changed
- `ethscan/mysql.py` (`_assess_handshake`, 1 line + comment): `v_lower = version.lower()` -> `version = str(version); v_lower = version.lower()`. A hostile non-string `server_version` (int/float/bool/bytes/list/dict) previously raised `AttributeError`/`TypeError` from `.lower()`/`.split()`; now it is rendered, matching the `str()` coercion already used by sibling assessors (`_assess_prelogin`, `_assess_version`, `_assess_smtp_version`, `_assess_ntp_version`, `_assess_ldap_version`). Byte-identical for valid string input.
- `ethscan/mongodb.py` (`_assess_buildinfo`, 1 line + comment): `v_lower = version.lower()` -> `v_lower = str(version).lower()`. Same hostile-field crash class; same sibling-consistent fix. Byte-identical for valid strings.
- `tests/test_mysql.py` (+14): added `test_assess_handshake_hostile_version_never_raises` (parametrized over int/float/bool/bytes/list/dict).
- `tests/test_mongodb.py` (+15): added `test_assess_buildinfo_hostile_version_never_raises` (same matrix).
- No behavior change for valid input; no production API/signature changes.

## What was actually verified
- Repro before fix: `_assess_handshake({"server_version": 123})` -> `AttributeError: 'int' object has no attribute 'lower'`; same for float/bool/bytes/list/dict. `_assess_buildinfo({"version": 123})` -> identical. `None` returns `[]` (falsy `if version:`), which is correct.
- Fix verified: all hostile values now render (e.g. `MySQL/MariaDB server version: 123`); valid strings unchanged (`5.7.0`, `10.5.10-MariaDB`, `5.1.50`, `2.4.1`).
- Regression guard proven: reverting the mongodb fix makes the new test fail 6/6 (`AttributeError`/`TypeError`); with the fix it passes.
- `python -m pytest tests/test_mysql.py tests/test_mongodb.py -q` -> 143 passed.
- `python -m pytest -q` -> 39337 passed, 146 skipped, 0 failed (was 39325; +12 new parametrized cases, baseline otherwise unchanged).
- `python -m mypy ethscan/ tests/` -> Success, no issues in 260 source files.
- `python -m ruff check ethscan/ tests/ check_readme.py` -> All checks passed.
- `python check_readme.py` -> 54 commands, 0 drift both directions.
- `python -m coverage run --branch --source=ethscan -m pytest -q` -> TOTAL 15762 stmts, 1 miss, 5962 branches, 1 partial, 99%; `ethscan/mysql.py` and `ethscan/mongodb.py` both 100%.
- `git diff --check` -> clean; `git status` -> only the 4 intended files modified.

## What remains unresolved
- `ethscan/cli.py:4318` defensive `UsageError("Shell argument is required when not using --install")` remains the sole branch-coverage gap — unreachable via the CLI (positional `shell` defaults to "bash" and is choice-validated). Intentionally out of scope: do not add `# pragma: no cover`, remove the guard, or require shell without an explicit task/evidence.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope (exit 0, in-band error) per documented contract.

## Approaches already tried / ruled out
- Manual code inspection + hand-rolled fuzzers over `_assess_*`, `_parse_*` (random bytes), JSON consumers (geo/cve/cert/jwt), and formatters: the ONLY genuine crashes found were the two `_assess_*` version-field cases fixed here. The many `_parse_*` `ValueError`s are intentional guards caught by callers (verified `run_ldap` wraps in `except Exception`; `_parse_ldap_response` catches internally). Wrong-typed-top-level-arg "crashes" from the fuzzer are type-contract noise (internal funcs always receive parser-produced dicts), not reachable bugs — not fixed.
- Rejected broadening `_assess_*` to guard every field with `str()` speculatively: only the two version fields had the unguarded `.lower()`/`.split()` pattern that the fuzzer proved crashes; the rest already coerce or try/except.
- Did not weaken safety/validation or touch CI/workflow files (maintainer-managed; the controller restores them).

## Next task
- None pending from current evidence. Repository is green (39337 passed; mypy/ruff/README clean; changed files 100% covered; only the documented `cli.py:4318` guard uncovered). If future work is needed, pick one bounded, verifiable improvement and reproduce the gap first (failing check/test or behavioral evidence vs documented contract) before implementing. Two concrete, evidence-backed leads for a future session if desired:
  1. A permanent repo-wide *dynamic* hostile-field fuzzer test that asserts every `_assess_*`/`format_install_report_*`/`format_completion_report_*` survives hostile field values (the existing `test_all_formatters_hostile_contract.py` only covers `format_*_report_*` single-arg formatters; `_assess_*` are not covered repo-wide). Must account for intentional `ValueError` in `_parse_*` (do not assert "never raise" on parsers).
  2. The `oracle`/`postgresql` empty-target handling and `cli.py:4318` remain out of scope unless explicitly tasked.
- Do not speculate on a green baseline; do not commit unless explicitly asked.

## Environment/notes
- Python 3.14.4, pytest 9.2.0, mypy 2.4.1, ruff 0.17.5. `rg` not installed; use `grep`/Grep tool. Coverage via `python -m coverage run --branch --source=ethscan -m pytest` (no pytest-cov plugin). No commit/push performed (not requested). Working tree has the 4 intended file changes.

(End of file)
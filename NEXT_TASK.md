# Next Task

## Status
Session complete (Sat Nov 14 2026): added a per-field hostile contract test to `tests/test_all_formatters_hostile_contract.py`.
- Injects a single hostile field into an otherwise-valid report dict across all 157 single-argument formatters × 15 fields × 7 hostile values, asserting `str` return and parseable JSON for `*_report_json` variants.
- No production code changed; purely test addition, fully reversible.

## Baseline (verified this session)
- `python -m pytest tests/test_all_formatters_hostile_contract.py -q` → 18685 passed (was 2200; +16485 new cases).
- `python -m pytest -q` → 31927 passed, 146 skipped, 1 warning, 0 failed (baseline was 15442 passed, 146 skipped, 1 warning; +16485 tests).
- `python -m mypy tests/test_all_formatters_hostile_contract.py --follow-imports=skip` → Success.
- `python -m ruff check tests/test_all_formatters_hostile_contract.py` → All checks passed.
- `python -m mypy ethscan/ tests/` → Success: no issues found.
- `python -m ruff check ethscan/ tests/` → All checks passed.
- `python3 check_readme.py` → 54/54, README and CLI in sync.

## Blockers
- None.

## Approaches already tried / ruled out
- Per-field and multi-field hostile fuzzing across all formatters (+ nmap NMapResult): 0 crashes (~617k calls). Formatters already defensive; no production fix needed. Not a fixable finding.
- JSON top-level-object assertion too strict; hostile non-mapping input renders as parseable JSON string per documented contract.
- `oracle`/`postgresql` empty-target handling out of scope per contract.
- Extreme Python edge cases (circular refs, unstringifiable objects, non-str dict keys) out of scope.

## Next task
None queued. The repo is fully green (31927 passed, 146 skipped, 0 failed). `oracle` and `postgresql` empty-target handling remains intentionally out of scope per their documented contract (exit 0, in-band error).

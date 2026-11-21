# Next Task

## Status: no genuine pending task; repo verified green (this session)

This session was verification-only. Fast gates + full suite re-run independently confirmed the baseline is unchanged:

- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift both directions
- `mypy ethscan/ tests/` -> Success (268 source files)
- `pytest -q` -> **46758 passed, 146 skipped, 0 failed** (baseline unchanged)
- `coverage report --fail-under=100` -> exit 0 (100%)

The scanner service-detection feature (`scanner.grab_banner`, `scanner.scan_ports_with_service`, CLI `--service-detect`, markdown/CSV `service_detect` branches) added in `f9487f9` is fully implemented AND tested at 100% coverage.

## Do not re-implement / do not "fix" (already done / intended)
- Service detection — now fully implemented AND tested at 100%.
- All 146 skips are intentional structural skips; none indicate a coverage gap.
- `hash --check` 32-char ambiguity (md5 preferred; use `--algorithm` for ntlm/md4) — DOCUMENTED + TESTED design, not a bug.
- `oracle`/`postgresql` empty-target in-band handling — documented contract (exit 0).
- `ethscan/cli.py` completion non-install unreachable guard (`# pragma: no cover`) — documented limitation.
- `coverage.json` is current (100%); do not treat a stale value as ground truth — regenerate with `python -m coverage run --source=ethscan -m pytest` then `python -m coverage json`.

## Next session guidance
1. Run the fast gates first: `ruff`, `mypy`, `check_readme.py`. If all green, run `python -m pytest -q` once and `coverage report` to confirm; if green, stop.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work; repo is at a verified steady state at 100% coverage.
3. Do not count control-marker-only (handoff-doc) commits as progress; make a real, verifiable change or leave the tree clean.
4. Optional evidence-gated investigations (do NOT start without reproducing a problem first):
   - Audit other test files ordered after `test_main.py` for string-form monkeypatch of `ethscan.cli` that may silently exercise real paths.
   - The `ethscan/cli.py` completion `effective_shell is None` guard is unreachable; only touch if a task explicitly asks.
5. If the orchestration keeps invoking sessions here, the correct outcome is a clean tree + honest "verified green, no gap" handoff — not invented changes.

(End of file)
# Next Task

## Status: service-detection coverage gap CLOSED this session

The scanner service-detection feature (`scanner.grab_banner`, `scanner.scan_ports_with_service`, CLI `--service-detect`, and the markdown/CSV `service_detect` formatter branches) added in `f9487f9` had **zero tests**. Fresh coverage before this session was 99.73% (44 missing lines: scanner.py 70-92, 115-126, 328, 337-338, 347-350, 367, 377-378; cli.py 996-998). The prior "100%" claim came from a stale committed `coverage.json` (initial import `ad9ab30`).

This session added `tests/test_scanner_service_detect.py` (14 tests) and regenerated `coverage.json`. Fresh evidence:

- `ruff check ethscan/ tests/ check_readme.py` -> All checks passed
- `check_readme.py` -> 54 commands, 0 drift
- `mypy ethscan/ tests/` -> Success (268 source files)
- `pytest -q` -> **46758 passed, 146 skipped, 0 failed**
- `coverage report` -> **100% (16081 stmts, 0 miss)**; `--fail-under=100` exits 0

## Test-pollution trap (read before writing more CLI tests)
- `tests/test_main.py` pops `ethscan.cli` from `sys.modules` (and doesn't restore it). Test files ordered after `test_main.py` that import `cli` at module load and then use a **string** monkeypatch target on `ethscan.cli.*` will patch the wrong module and hit the **real network**. Use object-form: `import ethscan.cli as cli_module` + `monkeypatch.setattr(cli_module, "attr", ...)`.

## Do not re-implement / do not "fix" (already done / intended)
- Service detection (`grab_banner`, `scan_ports_with_service`, `--service-detect`, formatter branches) — now fully implemented AND tested at 100%.
- All 146 skips are intentional structural skips; none indicate a coverage gap.
- `hash --check` 32-char ambiguity (md5 preferred; use `--algorithm` for ntlm/md4) — DOCUMENTED + TESTED design, not a bug.
- `oracle`/`postgresql` empty-target in-band handling — documented contract (exit 0).
- `ethscan/cli.py` completion non-install unreachable guard (`# pragma: no cover`) — documented limitation.
- `coverage.json` is now current (100%); do not treat a stale value as ground truth — regenerate with `python -m coverage run --source=ethscan -m pytest` then `python -m coverage json`.

## Next session guidance
1. Run the fast gates first: `ruff`, `mypy`, `check_readme.py`. If all green, run `python -m pytest -q` once and `coverage report` to confirm; if green, stop.
2. Only select new work if a genuine gap is REPRODUCED first (reproduce before changing). Do not fabricate work; repo is at a verified steady state at 100% coverage.
3. Do not count control-marker-only (handoff-doc) commits as progress; make a real, verifiable change or leave the tree clean.
4. Optional evidence-gated investigations (do NOT start without reproducing a problem first):
   - Audit other test files ordered after `test_main.py` for string-form monkeypatch of `ethscan.cli` that may silently exercise real paths.
   - The `ethscan/cli.py` completion `effective_shell is None` guard is unreachable; only touch if a task explicitly asks.
5. If the orchestration keeps invoking sessions here, the correct outcome is a clean tree + honest "verified green, no gap" handoff — not invented changes.

(End of file)
# Next Task

## Status
Previous handoff task completed (session 147): added permanent formatter hostile-sweep coverage for `fuzz` (coverage-only; formatters already defensive). Repository is fully green.

## Baseline (verified this session)
- `python -m pytest -q` → 8632 passed, 149 skipped, 1 warning (pre-existing `RuntimeWarning` in `tests/test_cli_cov_gaps.py::test_cli_main_guard_executes`).
- `python -m ruff check ethscan/ tests/` / `python -m mypy ethscan/ tests/` / `python3 check_readme.py` reported clean at handoff.

## Next task (bounded, verifiable)
Probe and, if no crashes found, add coverage-only `tests/test_nmap_formatter_hostile_sweep.py` for `ethscan.nmap` report formatters (`format_nmap_report_json`, `format_nmap_report_markdown`, `format_nmap_report_csv`).

Steps:
1. Inspect `ethscan/nmap.py` formatter signatures and expected report shape.
2. Probe hostile inputs first (non-mapping top-level like `None/1/True/"x"/[]`; hostile nested values in key report fields such as hosts/ports/scripts/results/target/notes) without editing production code.
3. If no crashes: add `tests/test_nmap_formatter_hostile_sweep.py` mirroring existing `*_formatter_hostile_sweep.py` pattern (hostile top-level, hostile nested, well-formed regression).
4. If crashes: make the smallest defensive formatter fix, then add regression coverage.
5. Verify focused tests, then targeted ruff/mypy on touched files; run full suite and `python3 check_readme.py` if changes warrant.

Constraints/evidence:
- Do not speculate or weaken safety controls.
- `oracle`/`postgresql` empty-target handling remains intentionally out of scope per documented contract (exit 0, in-band error).
- `passwords` formatters use a different multi-arg signature and are not a drop-in for this pattern.

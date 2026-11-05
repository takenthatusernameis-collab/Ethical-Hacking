# Next Task
Continue evidence-driven formatter hostile-shape hardening for modules whose `format_*_report_markdown`/`format_*_report_csv` raise on hostile top-level/non-dict or hostile nested report shapes and lack `tests/test_*hostile_sweep.py` formatter-shape coverage.

`ethscan/scanner.py` is done: `format_scan_report_markdown`/`format_scan_report_csv` now guard hostile top-level non-dict data; `tests/test_scanner_hostile_sweep.py` added. Verified: 55 scanner tests passed; full suite 5832 passed/50 skipped/0 failed; ruff clean; mypy clean.

Focus (pick one real gap at a time, verify before changing):
- `ethscan/service.py` formatters raised on hostile top-level `None` in probe (`AttributeError`/`TypeError`); assess coverage/gap and add smallest sweep+guards if needed.
- Other confirmed raises without hostile-sweep coverage: `recon`, `resolve`, `s3`, `ping`, `osdetect`, `wifi`, `trace`, `subdomains`, `stale`, `radix`, `completion`, `config`, `cidr`, `dnsbrute`. Prioritize modules on common CLI/report paths and those with clear, local fixes. `passwords` formatters take a `results` positional argument (different signature) — verify the exact gap before changing.

Constraints:
- Preserve baseline; smallest reversible change.
- Add guards/tests only for demonstrated real gaps (no transport/body/JSON parsing duplication).
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

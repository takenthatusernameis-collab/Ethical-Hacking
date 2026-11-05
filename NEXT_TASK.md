# Next Task
Continue evidence-driven formatter hostile-shape hardening only for modules with demonstrated `format_*_report_markdown`/`format_*_report_csv` raises on hostile top-level/non-dict or hostile nested report shapes that lack `tests/test_*hostile_sweep.py` coverage.

Done in recent sessions (verified, present in working tree/history): `service`, `scanner`, `recon`, `resolve`, `s3`, `osdetect`, `subdomains`, `stale`, `config`, `radix`, `completion`, `cidr`, `dnsbrute`, `passwords`, `validate`, `report`. Verified already clean (no change needed): `ping`, `trace`, `wifi`. Hostile sweep tests added for `trace` and `wifi` in this session (`tests/test_trace_hostile_sweep.py`, `tests/test_wifi_hostile_sweep.py`).

This session also fixed a real hostile-shape gap in `ethscan/wifi.py` `format_wifi_report_csv` (non-list `interfaces`/`access_points`/`notes` raised `TypeError`/`AttributeError`) and added `default=str` to the `trace`/`wifi` JSON formatters so hostile `bytes` top-level values serialize (matching `cidr`/`validate`/`report`).

The formatter hostile-shape sweep now covers every module with `format_*_report_markdown`/`format_*_report_csv`. No remaining modules in scope.

Constraints:
- Preserve baseline; smallest reversible change.
- Add guards/tests only for demonstrated real gaps (no transport/body/JSON parsing duplication).
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

Known pre-existing failures (do not confuse with regressions; unrelated to this sweep): none remaining — the 6 `ping` CSV-header failures were fixed earlier by always emitting the CSV header row in `format_ping_report_csv`.

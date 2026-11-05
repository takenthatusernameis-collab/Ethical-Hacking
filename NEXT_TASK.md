# Next Task
Continue evidence-driven formatter hostile-shape hardening only for modules with demonstrated `format_*_report_markdown`/`format_*_report_csv` raises on hostile top-level/non-dict or hostile nested report shapes that lack `tests/test_*hostile_sweep.py` coverage.

Done in recent sessions (verified, present in working tree/history): `service`, `scanner`, `recon`, `resolve`, `s3`, `osdetect`, `subdomains`, `stale`, `config`, `radix`, `completion`, `cidr`, `dnsbrute`. Verified already clean (no change needed): `ping`, `trace`, `wifi`.

Remaining to verify (one at a time, probe first):
- `passwords` — formatters take a `results` positional argument (different signature) — verify exact gap before changing.
- `validate` — has `format_validate_report_csv`/`format_validate_report_markdown` — verify whether CLI/report formatter in scope; probe hostile shapes.
- `report` — verify whether it is a CLI/report formatter in scope for this sweep pattern.

Constraints:
- Preserve baseline; smallest reversible change.
- Add guards/tests only for demonstrated real gaps (no transport/body/JSON parsing duplication).
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

Known pre-existing failures (do not confuse with regressions; unrelated to this sweep): 6 `ping` CSV-header failures present at clean HEAD.

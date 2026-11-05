# Next Task
Continue evidence-driven formatter hostile-shape hardening for modules whose `format_*_report_markdown`/`format_*_report_csv` raise on hostile top-level/non-dict or hostile nested report shapes and lack `tests/test_*hostile_sweep.py` formatter-shape coverage.

Done in recent sessions (verified, present in working tree/history): `service`, `scanner`, `recon`, `resolve`, `s3`. Probes showed `wifi` formatters do not raise on hostile top-level `None` (verify before changing).

Focus (pick one real gap at a time, verify before changing):
- Probe-identified `None`/hostile-shape raises without hostile-sweep formatter coverage (verify signatures; some may already be guarded): `ping`, `osdetect`, `trace`, `subdomains`, `stale`, `radix`, `completion`, `config`, `cidr`, `dnsbrute`. Prioritize modules on common CLI/report paths and those with clear, local fixes.
- `passwords` formatters take a `results` positional argument (different signature) — verify the exact gap before changing.
- `report`/`validate`/others: verify whether they are CLI/report formatters in scope for this sweep pattern; only change for demonstrated formatter-shape gaps.

Constraints:
- Preserve baseline; smallest reversible change.
- Add guards/tests only for demonstrated real gaps (no transport/body/JSON parsing duplication).
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

# Next Task
Continue evidence-driven formatter hostile-shape hardening for modules whose `format_*_report_markdown`/`format_*_report_csv` raise on hostile top-level/non-dict or hostile nested report shapes and lack `tests/test_*hostile_sweep.py` formatter-shape coverage.

Focus (pick one real gap at a time, verify before changing):
- `ethscan/vuln.py` formatters raised on hostile top-level `None` in quick probe; assess coverage/gap and add smallest sweep+guards if needed.
- Other probes showed raises in wifi, trace, subdomains, stale, scanner, service, recon, resolve, s3, radix, ping, passwords (audit formatters), osdetect, completion, config, cidr, dnsbrute — prioritize modules on common CLI/report paths and those with clear, local fixes.

Constraints:
- Preserve baseline; smallest reversible change.
- Add guards/tests only for demonstrated real gaps (no transport/body/JSON parsing duplication).
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

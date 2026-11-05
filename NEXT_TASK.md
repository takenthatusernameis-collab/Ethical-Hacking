# Next Task
Audit formatter modules for hostile report-shape gaps (evidence-driven) where `format_*_report_markdown`/`format_*_report_csv` may subscript/`.get` top-level `data` without `isinstance(data, dict)` or iterate nested containers without guards, and where no hostile-shape sweep test exists. Prioritize modules that accept pipeline/CLI report data and have JSON/formatter paths similar to `tls`/`ssl`.

Focus:
- Grep evidence: `grep -n "def format" ethscan/*.py` vs modules missing `isinstance(data, dict)` in formatters and lacking `tests/test_*hostile_sweep.py` coverage for formatter shapes.
- Add the smallest `tests/test_<module>_hostile_sweep.py` and production guards only for demonstrated real gaps (hostile top-level/nested shapes raise or produce unsafe behavior).
- Do not duplicate transport/body/JSON-parse coverage; keep changes minimal.

Constraints:
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update `TASK.md`/`HANDOFF_NEXT.md`/`NEXT_TASK.md`; do not commit unless explicitly asked.

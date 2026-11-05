# Next Task
Audit `ethscan/tls.py` report formatters for hostile report-shape gaps not already covered by `tests/test_tls.py` and transport/HTTP hostile sweeps (evidence-driven). Add the smallest `tests/test_tls_hostile_sweep.py` and production guards only if a real gap exists.

Focus:
- Formatter top-level/nested hostile shapes (non-dict `data`, hostile `cert`/`chain`/field containers) that can reach CLI/reporting.
- Avoid duplicating existing `tests/test_tls.py` cases and transport-focused tests.
- Grep for other formatter modules lacking top-level `isinstance(data, dict)` guards if tls is clean; prioritize by evidence.

Constraints:
- Preserve baseline; smallest reversible change.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update handoff files; do not commit unless explicitly asked.

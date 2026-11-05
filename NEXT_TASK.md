# Next Task
Audit `ethscan/ssl.py` report formatters for hostile report-shape gaps not already covered by `tests/test_ssl.py` and transport/HTTP hostile sweeps (evidence-driven). Add the smallest `tests/test_ssl_hostile_sweep.py` and production guards only if a real gap exists.

Focus (evidence-driven):
- Formatter top-level/nested hostile shapes (non-dict `data`, hostile `cert`/`chain`/field containers) that can reach CLI/reporting; SSL uses TLS sockets (not covered by http sweep), but this pass targets formatter robustness only.
- Avoid duplicating existing `tests/test_ssl.py` cases and transport-focused tests.
- Grep for other formatter modules lacking top-level `isinstance(data, dict)` guards if ssl is clean; prioritize by evidence.

Constraints:
- Preserve baseline; smallest reversible change.
- Add focused tests only where a real gap is evidenced; do not modify production code unless required to report a hostile input safely.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update handoff files; do not commit unless explicitly asked.
# Next Task
Audit `ethscan/fuzz.py` for hostile cache/file/response-shape gaps not already covered by `tests/test_http_hostile_sweep.py` transport/body coverage and existing `tests/test_fuzz.py`, and add the smallest bounded sweep only if a real gap is evidenced.

Focus (evidence-driven):
- Any file/cache/JSON parsing or wordlist/path handling gaps (malformed inputs, hostile shapes) and stale/offline fallback behavior if applicable.
- Unnamed transport/parse error types reported as result fields, never raised.
- Avoid duplicating `tests/test_http_hostile_sweep.py` transport/body cases and existing fuzz tests; add focused tests only for uncovered parser/shape gaps.

Constraints:
- Preserve baseline; smallest reversible change.
- Add focused tests only where a real gap is evidenced; do not modify production code unless required to report a hostile input safely.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update handoff files; do not commit unless explicitly asked.

Evidence this session: `ethscan/subtake.py` audited — no cache/file/JSON parsing; DNS/HTTP transport errors handled; http sweep + bad-status-line test cover HTTP body/transport. Real formatter gap found: `format_subtake_report_csv` raised on hostile `all_results` entries (non-dict) / hostile top-level; Markdown raised on hostile top-level. Smallest fix added (type guards/`get` defaults); `tests/test_subtake_hostile_sweep.py` added (15 tests). Full suite: 5809 passed, 50 skipped. Ruff/mypy clean.

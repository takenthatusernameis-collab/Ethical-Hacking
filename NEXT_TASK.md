# Next Task
Audit `ethscan/s3.py` for hostile cache/API/response-shape gaps not already covered by `tests/test_http_hostile_sweep.py`, and add the smallest bounded sweep only if a real gap is evidenced.

Focus (evidence-driven):
- Any file/cache/JSON parsing paths (malformed/non-JSON/non-dict/non-finite values, hostile entry shapes) and stale/offline fallback behavior if applicable.
- Unnamed transport/parse error types reported as result fields, never raised.
- Avoid duplicating `tests/test_http_hostile_sweep.py` transport/body cases; add focused tests only for uncovered parser/shape gaps.

Constraints:
- Preserve baseline; smallest reversible change.
- Add focused tests only where a real gap is evidenced; do not modify production code unless required to report a hostile input safely.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update handoff files; do not commit unless explicitly asked.

Evidence this session: `ethscan/cve.py` audited — cache parsing already resilient (`load_json` errors/non-dict -> empty cache, non-dict entries filtered; `_is_cache_valid` rejects hostile timestamps; stale offline fallback copies cached mapping). Added `tests/test_cve_hostile_sweep.py` (42 tests) covering hostile cache bodies, hostile timestamps, non-dict entry filtering, and stale/offline fallback with hostile cached shapes. Targeted cve: 124 passed. Full suite: 5794 passed, 50 skipped. Ruff/mypy clean.

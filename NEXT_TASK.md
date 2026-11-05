# Next Task
Audit `ethscan/cve.py` for hostile cache/API/JSON shape gaps not already covered by `tests/test_http_hostile_sweep.py`, and add the smallest bounded sweep only if a real gap is evidenced.

Focus (evidence-driven):
- Cache/file parsing paths (malformed/non-JSON/non-dict/non-finite timestamps, hostile entry shapes) and stale offline fallback behavior.
- Unnamed transport/parse error types reported as result fields, never raised.
- Avoid duplicating `tests/test_http_hostile_sweep.py` transport/body cases; add focused tests only for uncovered parser/cache gaps.

Constraints:
- Preserve baseline; smallest reversible change.
- Add focused tests only where a real gap is evidenced; do not modify production code unless required to report a hostile input safely.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update handoff files; do not commit unless explicitly asked.

Evidence this session: `ethscan/geo.py` and `ethscan/mac.py` audited — cache/transport paths already resilient for inspected cases. Added `tests/test_geo_hostile_sweep.py` and `tests/test_mac_hostile_sweep.py` (32 tests total) covering hostile cache bodies, stale hostile/offline fallback, and unnamed transport error reporting. Targeted geo/mac: 154 passed. Full suite: 5752 passed, 50 skipped. Ruff/mypy clean.

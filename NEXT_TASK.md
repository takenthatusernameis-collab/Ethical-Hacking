# Next Task
Audit `ethscan/fuzz.py` for hostile cache/file/response-shape/wordlist gaps not already covered by `tests/test_http_hostile_sweep.py` and existing `tests/test_fuzz.py`, and add the smallest bounded sweep only if a real gap is evidenced.

Focus (evidence-driven):
- Any file/cache/JSON parsing or wordlist/path handling gaps (malformed inputs, hostile shapes) and stale/offline fallback behavior if applicable.
- Unnamed transport/parse error types reported as result fields, never raised.
- Avoid duplicating `tests/test_http_hostile_sweep.py` transport/body cases and existing fuzz tests; add focused tests only for uncovered parser/shape gaps.

Constraints:
- Preserve baseline; smallest reversible change.
- Add focused tests only where a real gap is evidenced; do not modify production code unless required to report a hostile input safely.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Update handoff files; do not commit unless explicitly asked.

Evidence this session: `ethscan/fuzz.py` audited — no cache/file/JSON parsing; transport errors already caught (unnamed `Exception` guard); http sweep covers HTTP body/transport. Real gaps found: `format_fuzz_report_markdown` raised on hostile top-level (subscripted `data['target']` etc.) and hostile `all_results`/`findings` entries (non-dict); `format_fuzz_report_csv` raised on hostile top-level (`data.get` on non-dict) and hostile `all_results`/`findings` entries; `run_fuzz` raised on hostile wordlist entries (non-string paths hit `_join_url`'s `.lstrip`). Smallest fixes added (isinstance guards, `.get` defaults, non-string path filtering); `tests/test_fuzz_hostile_sweep.py` added (18 tests). Full suite: 5838 passed, 50 skipped. Ruff/mypy clean.
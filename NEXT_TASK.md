# Next Task
Audit remaining modules that parse untrusted/network/cache input but lack a dedicated hostile sweep file, and add the smallest bounded sweep(s) with evidence.

Evaluate candidates not covered by a dedicated `test_*_hostile_sweep.py`: `geo`, `mac`, `cve`, `s3`, `subtake`, `fuzz`, `urlcheck`, `web`, `headers` (all touched by `tests/test_http_hostile_sweep.py` — check for parser/cache/file gaps beyond transport/body hostility), and `resolve`/`subdomains`/`stale`/`ping`/`osdetect`/`scanner`/`service` (transport/sweep coverage exists in protocol/other sweeps — confirm no cache/parser gaps). `cert` now covered this session.

Constraints:
- Preserve baseline; smallest reversible change.
- Add focused tests only where a real gap is evidenced; do not duplicate existing sweep coverage.
- Verify: targeted pytest for new/affected tests, then full `python3 -m pytest -q`, `python3 -m ruff check .`, `python3 -m mypy ethscan`.
- Do not commit unless explicitly asked.

Evidence this session: `ethscan/cert.py` cache/transport paths audited; cache loading and hostile entry extraction already resilient (uses lenient JSON load, dict filtering, stale-cache fallback, broad fetch exception handling, defensive extraction/formatting). Added `tests/test_cert_hostile_sweep.py` (18 tests) covering hostile cache file contents, stale hostile cache fallback, unnamed transport error types, failed fetch reporting, and hostile entry shapes. Full suite: 5720 passed, 50 skipped.

# Next Task
Audit remaining modules that parse untrusted/network input but lack a dedicated hostile sweep file, and add the smallest bounded sweep(s) with evidence.

Candidates to evaluate (no dedicated `test_*_hostile_sweep.py`): `cert` (CT API JSON parsing/caching paths), `scanner`/`service`/`ping`/`osdetect` transport edges beyond protocol sweep coverage if gaps exist, `tls`/`ssl` now covered this session. `resolve`, `dns`, `subdomains`, `stale`, `whois` have transport/error coverage in existing sweeps — confirm no parser-gap remains.

Constraints:
- Preserve baseline; smallest reversible change.
- Add focused tests only where a real gap is evidenced; do not duplicate existing sweep coverage.
- Verify: targeted pytest for new/affected tests, then full `pytest`, `ruff check .`, `mypy ethscan`.
- Do not commit unless explicitly asked.

Evidence this session: `ethscan/ssl._parse_cert` crashed on `issuer=None` (hostile decoded cert); fixed + covered by `tests/test_ssl_hostile_sweep.py` (17 tests) and `tests/test_tls_hostile_sweep.py` (11 tests). Full suite: 5702 passed, 50 skipped.

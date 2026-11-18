# Next Task
Date: Wed Nov 18 2026

## Status
- Green: 39813 passed, 146 skipped, 0 failed; mypy/ruff clean; README 54/54
  with 0 drift; full-suite branch coverage 100% except the documented
  unreachable `ethscan/cli.py` guard.
- This session fixed DNS-name normalization swallowing URL ports and IPv6
  brackets across the DNS/recon modules (see TASK.md session 10).

## This session (what changed)
- `ethscan/dns.py`, `dnssec.py`, `dnsbrute.py`, `subdomains.py`, `recon.py`,
  `stale.py`, `subtake.py`: `_normalize_domain` delegates to
  `ethscan.target.normalize_host` instead of returning `urlparse(...).netloc`.
  Previously `http://127.0.0.1:8080/` became the DNS name `127.0.0.1:8080`
  (all queries failed); `dnssec` derived parent zone `com:8080.`; dnssec and
  dnsbrute kept IPv6 brackets (`[::1]:8080`).
- Tests: corrected port assertions, added IPv6 bracket/port cases and an
  end-to-end `run_dns` regression (+8 tests total).

## Verified
- Before: `run_dns("http://127.0.0.1:8080/", ["A"])["records"] == {'A': []}`;
  after: `{'A': ['127.0.0.1']}` and `domain == "127.0.0.1"`.
- `python -m ethscan dns --target http://127.0.0.1:8080/ --types A
  --format json` -> domain `127.0.0.1`, A `["127.0.0.1"]`.
- Focused tests 502 passed; full suite 39813 passed / 146 skipped;
  mypy Success (261 files); ruff clean; `check_readme.py` 54/54;
  `git diff --check` clean; touched modules 100% branch coverage.

## Next task
- `ethscan/hash.py::_infer_algorithm` should reject non-hex digests.
  Evidence:
  - `_infer_algorithm("z"*32)` -> `"md5"` (docstring promises a hex digest).
  - `run_check("x", "z"*32)` -> `{'algorithm': 'md5', 'match': False,
    'error': None}`; a garbage/typo digest is reported as a plain password
    mismatch instead of the existing "Could not infer algorithm from digest
    length ..." error.
  Reproduce first, then validate hex before length matching (e.g.
  `int(candidate, 16)` inside try/except, or a hex-digit check), keep the
  empty/whitespace behavior (`None`), and add tests for non-hex strings of
  every known digest length plus positive md5/sha1/sha256/sha512 cases.
  Do not change the explicit-algorithm `run_check` contract without evidence.
  Re-run pytest/mypy/ruff/check_readme/full coverage; keep `hash.py` at 100%.

## Known limitations (intended, out of scope)
- `ethscan/cli.py:4318` is a documented unreachable defensive guard.
- `oracle`/`postgresql` report an unusable target in-band (exit 0) by contract.
- PBKDF2 + NTLM remains intentionally unsupported.

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- No new dependencies; tests must be deterministic.
- Do not commit manually; the workflow controller commits and verifies pushes.

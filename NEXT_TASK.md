# Next Task
Date: Wed Nov 18 2026

## Status
- Repository green: 39794 passed, 149 skipped, 0 failed; mypy/ruff clean;
  README in sync (54 commands); `ethscan/hash.py` at 100% coverage.
- Prior assignment complete: PBKDF2-HMAC-MD4 fallback implemented, tested,
  verified against the PHP oracle, and 100% hash.py coverage.

## This session (what changed)
- Reconciled stale handoff docs with the committed tree; no source change was
  required because `_compute_pbkdf2_hash` already routed md4 to the pure
  Python `_pbkdf2_hmac_md4` fallback when `_hashlib_name` returns None.
- Added `test_pbkdf2_hmac_md4_dklen_too_large` in tests/test_hash.py covering
  ethscan/hash.py:137 (`dklen too large`), bringing `ethscan/hash.py` to
  100% coverage.

## Verified
- `pytest tests/test_hash.py tests/test_cli.py -q -k "md4 or pbkdf2 or ntlm"` -> 30 passed.
- `pytest -q` -> 39794 passed, 149 skipped.
- `mypy ethscan/ tests/` -> Success (261 files); `ruff` clean;
  `check_readme.py` -> 54 commands, 0 drift; `git diff --check` clean.
- Coverage: `ethscan/hash.py` 100%, 0 missing.

## Known limitation (intended, out of scope)
- PBKDF2 + NTLM remains intentionally unsupported (NTLM is not a byte-oriented
  hash); the `Algorithm '...' does not support PBKDF2 (no hashlib name.)`
  error path and its tests stay intact.

## Next task
- None pending. The baseline is clean and green; no defect or gap is
  demonstrated. If the next agent selects a self-directed bounded task, a
  coverage sweep of the next-lowest-covered module in ethscan/ is a reasonable
  starting point (do not turn coverage into an infrastructure project absent a
  demonstrated gap).

## Constraints / notes
- Keep architecture stable; do not weaken validation/exit-code contracts.
- `ethscan/cli.py:4318` is a documented unreachable completion guard; leave it.
- Do not commit manually; the workflow controller commits and verifies pushes.

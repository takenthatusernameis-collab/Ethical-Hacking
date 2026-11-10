# Next Task

## Task
- None pending. Repository is fully green.

## Evidence
- Baseline (this session): `pytest -q` → 5961 passed, 50 skipped, 0 failed; `mypy ethscan/cli.py` → clean; `ruff check ethscan/cli.py` → all checks passed.
- Fixed `ethscan/cli.py:_validate_enum_target` so unparseable URL targets (`http://[::1`, `[::1`, `http://example.com]`) reported by the enum-target commands (`brute`, `s3`, `subdomains`, `subtake`, `dnsbrute`) keep `parse_url`'s `Invalid IPv6 URL` message instead of being masked as `Could not parse host from target`. Empty/hostless targets still report `Could not parse host from target ...` (exit 2).
- Full suite green: 5961 passed, 50 skipped, 0 failed.

## Next task after that
- If future work is needed, pick a single high-value, verifiable improvement and reproduce it first. Do not speculate or weaken safety controls.

# Next Task

## Task
- None pending. Repository is fully green.

## Evidence
- Baseline (this session): `pytest -q` -> 5962 passed, 50 skipped, 0 failed; `ruff check` -> all checks passed; `mypy ethscan/ tests/test_cli.py` -> no issues.
- Added regression test `test_enum_target_command_rejects_empty_and_unparseable_targets` covering the empty-host and unparseable-URL paths of `_validate_enum_target` for all 13 enum-target commands (brute, cve, dnsbrute, fuzz, osdetect, report, s3, stale, subdomains, subtake, urlcheck, vuln, recon).
- The session-48 fix to `ethscan/cli.py:_validate_enum_target` is intact: unparseable URL targets (`http://[::1`, `[::1`, `http://example.com]`) keep `parse_url`'s `Invalid IPv6 URL` message; empty/hostless targets still report `Could not parse host from target ...` (exit 2).

## Next task after that
- If future work is needed, pick a single high-value, verifiable improvement and reproduce it first. Do not speculate or weaken safety controls.

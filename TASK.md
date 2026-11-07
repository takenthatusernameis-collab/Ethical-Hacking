# Task
Date: Sat Nov 07 2026

## Current state
- Full suite (this environment, verified): `5903 passed, 50 skipped`.
- `python3 -m ruff check .`: all checks passed. `python3 -m mypy ethscan`: Success, 59 source files.
- Prior session fixed TLS test order assumptions; full sweep clean.

## This session
- **Demonstrated gap (reproduced):** `subdomains`, `subtake`, `dnsbrute`, `s3` (and `recon --subdomains-wordlist`) read a user-supplied wordlist via `load_subdomain_wordlist` before validating/normalizing `--target`. If target parsing/normalization would fail with `TargetSpecError` (e.g. malformed IPv6 URL like `http://[invalid`) or if wordlist read raises, the wordlist I/O (side effect) could occur before clean rejection; in the tested case with a mocked read error the behavior was problematic (exit 1 with empty/exception leaking). Also host validation differs across commands.
- **Fix (smallest reversible):** Added `_validate_enum_target()` in `ethscan/cli.py` using `parse_url` on `https://`-prefixed target (matching module normalization style) and call it before wordlist reads in `subdomains`, `subtake`, `dnsbrute`, `s3`, and `recon`. Added `parse_url` import to CLI. Invalid targets now reported as usage errors (exit code 2) before any wordlist file I/O; existing module-level validation/TargetSpecError translation unchanged.
- **Verified:** Targeted tests `tests/test_cli.py tests/test_s3.py tests/test_subdomains.py tests/test_dnsbrute.py tests/test_subtake.py` → `1344 passed`. Invalid-target cases with wordlist-read mocked now surface target usage error before I/O. Normal paths unchanged.

## Blockers
- None demonstrated.

## Next task
- If no demonstrated gap remains, scan for another CLI option/callback where a side effect (file read/network init) happens before validation/rejection, or a silent-accept validation gap, in a materially different area from exhausted sweeps. Stop at first reproduced gap; smallest guard/test only. Keep baseline green. Update handoffs; do not commit unless asked.

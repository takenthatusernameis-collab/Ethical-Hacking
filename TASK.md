# Task
Date: Thu Nov 05 2026

## Current state
- HEAD on origin/main; working tree has local uncommitted changes (not committed).
- Tests: 5720 passed, 50 skipped, 0 failed; `ruff` clean; `mypy ethscan` clean (59 files).
- Coverage complete across all 59 modules (100%).
- Module-specific hostile sweeps cover: cert, dns, dnssec, ftp, http (shared), ldap, memcached, mongodb, mssql, mysql, netbios, ntp, oracle, postgresql, redis, smb, smtp, snmp, ssh, ssl, tls, whois. `cert` hostile sweep added this session (`tests/test_cert_hostile_sweep.py`).
- `ethscan/ssl._parse_cert` previously hardened for hostile decoded cert fields (covered by ssl/tls sweeps).

## Blockers
- None.

## Next task
- Audit remaining modules that parse untrusted/network/cache input for dedicated hostile-sweep gaps (e.g., `geo`, `mac`, `cve`, `s3`, `subtake` have cases in `tests/test_http_hostile_sweep.py`; `resolve`, `dns`, `subdomains`, `stale`, `ping`, `osdetect`, `scanner`, `service` have protocol/transport coverage — confirm parser/cache gaps). Prefer the smallest bounded addition with focused evidence. Do not commit unless explicitly asked.

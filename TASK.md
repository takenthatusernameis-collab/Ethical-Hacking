# Next task for the next agent

The `tls` command has been implemented. All previously listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown report generation
- `subdomains` — subdomain enumeration (DNS resolution of a wordlist against a target domain)
- `whois` — WHOIS lookup (queries WHOIS server on port 43, parses registrar, creation/expiration dates, nameservers, registrant org, status codes)
- `dns` — DNS record enumeration (A, AAAA, MX, NS, TXT, CNAME, SOA)
- `ssl` — SSL/TLS certificate inspection (subject, issuer, validity dates, SANs, signature algorithm, key size, chain length)
- `brute` — FTP/SSH login brute force with username/password wordlists (concurrent attempts, per-attempt results, successful-login summary)
- `service` — nmap-style service/banner detection (connect to open ports, grab banners, match against known service signatures)
- `tls` — TLS protocol/cipher enumeration (per-version handshake probes with pinned min/max TLS version, per-cipher probes with pinned OpenSSL cipher string, negotiated cipher/protocol reporting, obsolete-version findings)

## Implementation Summary

### Added Files
- `ethscan/tls.py` — TLS enumeration module with:
  - `TLS_VERSIONS` — default probe order (TLSv1, TLSv1_1, TLSv1_2, TLSv1_3)
  - `VERSION_ALIASES` — case-insensitive string aliases (e.g. "tls1.2", "TLSv1_2") mapped to `ssl.TLSVersion` members
  - `COMMON_CIPHERS` — 16 common TLS<=1.2 OpenSSL cipher names (TLS 1.3 suite names cannot be pinned via stdlib `set_ciphers()`, so they are reported as per-cipher errors when explicitly requested)
  - `OBSOLETE_VERSIONS` — versions flagged in findings when supported (SSLv3, TLSv1, TLSv1_1)
  - `probe_version()` — pins `SSLContext` min/max to one TLS version, handshakes, reports negotiated cipher/protocol
  - `probe_cipher()` — pins `SSLContext` to one cipher via `set_ciphers()`, handshakes, reports negotiated protocol version
  - `enumerate_tls()` — concurrent probing via `ThreadPoolExecutor`, sorted results, supported-version/cipher summaries, notes
  - `run_tls()` — public entry point: normalizes host (URL/bare), delegates to `enumerate_tls`
  - `format_tls_report_json()` / `format_tls_report_markdown()` — output formatters (markdown includes summary, findings, and full per-probe tables with error truncation/escaping)
- `tests/test_tls.py` — 25 unit tests: defaults, host normalization, version alias resolution, per-probe offline behavior (connection refused, non-selectable ciphers, invalid specs), `run_tls` structure/ordering/defaults/custom lists/invalid versions/notes, both formatters, error truncation/escaping

### Modified Files
- `ethscan/cli.py` — registered `tls` command with `--target`, `--port`, `--versions`, `--ciphers`, `--timeout`, `--workers`, `--format`, `--out`. Invalid version names print "Unknown TLS versions: ... Valid versions: ..." (mirrors the `dns` unknown-types pattern).
- `tests/test_cli.py` — 10 CLI integration tests: `tls` help, top-level help listing, offline json/markdown output, `--port`, `--versions`, `--ciphers`, `--workers`, `--out`, and unknown-version handling.
- `README.md` — added TLS protocol/cipher enumeration to the features list.

### Verification
- `python -m pytest -q` -> 217 passed (182 baseline + 35 new).
- `python -m ethscan --help` -> lists `tls` among the 12 commands.
- `python -m ethscan tls --help` -> shows all expected options.
- Live checks against local `openssl s_server` instances: a TLS 1.2-only server reports only TLSv1_2 supported (14/16 ciphers; ECDHE-ECDSA correctly rejected with an RSA cert) and a TLS 1.3-only server reports only TLSv1_3 supported with negotiated cipher TLS_AES_256_GCM_SHA384.

## Suggested next task

**Add a `--vuln` vulnerability check command** — cross-reference detected services/versions (from `service` and `ssl` banners) with a small built-in CVE/weakness database (e.g. old OpenSSH/ProFTPD/vsftpd versions, SSLv3/TLSv1 enabled, weak ciphers) and report matches.

Alternative: add a `--speed`/ports-range preset option for `scan`, or a `dnsbrute`/axfr-style DNS zone transfer attempt.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`brute.py`).

## Current state
- All 12 commands implemented.
- Tests: 217 passing.

(End of file - total 61 lines)

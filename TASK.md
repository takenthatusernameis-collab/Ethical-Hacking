# Next task for the next agent

The `vuln` command has been implemented. All previously listed features are now complete:
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
- `vuln` — vulnerability checks (live service/banner detection cross-referenced with a built-in CVE/weakness database; optional `--tls-file`/`--ssl-file` inputs from the `tls`/`ssl` commands for protocol, weak-cipher, and certificate weakness findings; `--severity` filtering)

## Implementation Summary

### Added Files
- `ethscan/vuln.py` — vulnerability check module with:
  - `BANNER_SIGNATURES` — regex signatures extracting (product, version) from banners (OpenSSH, ProFTPD, vsftpd, Pure-FTPd, FileZilla, Dovecot, Postfix, Exim)
  - `SERVICE_VULNS` — 6 service CVE entries with inclusive/exclusive version-range specs (CVE-2016-6210, CVE-2018-15473, CVE-2016-0777, CVE-2016-0778 for OpenSSH; CVE-2015-3306 for ProFTPD 1.3.0–1.3.5; VSFTPD-2.3.4-BACKDOOR exact match)
  - `PROTOCOL_VULNS` — protocol weaknesses (SSLv3/POODLE CVE-2014-3566, TLSv1/BEAST CVE-2011-3389, TLSv1_1 deprecated RFC 8996)
  - `CIPHER_VULNS` — weak-cipher patterns matched against supported cipher names (RC4 CVE-2013-2566, DES/3DES Sweet32 CVE-2016-2183, NULL ciphers, export-grade EXP FREAK CVE-2015-0204)
  - `CERTIFICATE_VULNS` — certificate checks (RSA key < 2048 bits, MD5/SHA-1 signature algorithms)
  - `VULN_DB` — combined database (SERVICE_VULNS + PROTOCOL_VULNS + CIPHER_VULNS + CERTIFICATE_VULNS)
  - `parse_banner()` — extracts (product, version) from a raw banner
  - `version_in_range()` — version-range matching with inclusive/exclusive bounds (numeric component tuples)
  - `match_service_vulns()` / `match_protocol_vulns()` / `match_cipher_vulns()` / `match_certificate_vulns()` — per-category matchers
  - `match_tls_vulns()` / `match_ssl_vulns()` — consume `tls`/`ssl` command output dicts
  - `run_vuln()` — public entry point: normalizes host (URL/bare), runs live service detection unless pre-computed `services` data is passed, aggregates findings, applies `--severity` filter, computes per-severity counts and notes
  - `format_vuln_report_json()` / `format_vuln_report_markdown()` — output formatters (markdown includes summary, severity breakdown, and per-finding sections with pipe escaping)
- `tests/test_vuln.py` — 51 unit tests: defaults, host normalization, banner parsing (OpenSSH/ProFTPD/vsftpd/Pure-FTPd/Dovecot/unknown), version-range semantics, per-category matching (old/new versions, RC4/DES/NULL/EXP ciphers, weak keys, MD5/SHA-1/SHA-256 signatures), `run_vuln` live mode (monkeypatched `run_service`), pre-computed services/tls/ssl data, combined findings, severity filtering/counts, ports/timeout/workers pass-through, both formatters, markdown escaping.

### Modified Files
- `ethscan/cli.py` — registered `vuln` command with `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity` (low/medium/high/critical), `--timeout`, `--workers`, `--format`, `--out`.
- `tests/test_cli.py` — 12 CLI integration tests: `vuln` help, top-level help listing, offline json/markdown output (monkeypatched `run_vuln`), `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--ports`, `--workers`, `--out` (json and markdown).
- `README.md` — added vulnerability checks and service detection to the features list.

### Verification
- `python -m pytest -q` -> 280 passed (217 baseline + 63 new).
- `python -m ethscan --help` -> lists `vuln` among the 13 commands.
- `python -m ethscan vuln --help` -> shows all expected options.
- Live checks against local banner servers: an OpenSSH 7.2p2 banner yields CVE-2016-6210 + CVE-2018-15473 and a vsftpd 2.3.4 banner yields the VSFTPD-2.3.4-BACKDOOR critical finding; `--severity critical` filters to the backdoor only.
- Live check against the sandbox's own OpenSSH 9.6p1 (port 22): detected, zero findings (modern version not in DB).
- `openssl s_server -tls1` enumeration via `ethscan tls` (local OpenSSL 3.0 client policy blocks TLSv1 handshakes — probes correctly report NO_PROTOCOLS_AVAILABLE/protocol-version errors); a realistic tls report JSON fed through `--tls-file` yields CVE-2011-3389 (BEAST), CVE-2013-2566 (RC4), CVE-2016-2183 (Sweet32).

## Suggested next task

**Add a `dnsbrute` command (DNS zone-transfer/AXFR attempt + subdomain brute force)** — attempt AXFR against the target's authoritative nameservers (resolvable via `dns` command output or `--ns` option), and brute-force subdomains by resolving a wordlist (reusing `subdomains` wordlist loading), reporting resolvable hosts with their A/AAAA records.

Alternative: add a `--speed`/ports-range preset option for `scan` (e.g. `--profile fast|normal|full` mapping to port sets and worker/timeout presets), or a `urlcheck` command combining `web` + `fuzz` + `ssl` into a single consolidated report.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`brute.py`).

## Current state
- All 13 commands implemented.
- Tests: 280 passing.

(End of file - total 61 lines)

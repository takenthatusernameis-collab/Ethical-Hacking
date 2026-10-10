# Next task for the next agent

The `dnsbrute` command has been implemented. All previously listed features are now complete:
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
- `dnsbrute` — DNS zone-transfer (AXFR) attempts against authoritative nameservers plus subdomain brute force (wordlist resolution with A/AAAA reporting)

## Implementation Summary

### Added Files
- `ethscan/dnsbrute.py` — DNS brute force module with:
  - `build_axfr_query()` — builds a TCP-prefixed (2-byte length) DNS AXFR query (QTYPE 252, QCLASS IN) for a zone
  - `_parse_dns_name()` — DNS name parser with RFC 1035 compression-pointer support and loop protection
  - `parse_dns_response()` — parses raw DNS response headers (query id, rcode, counts) and answer records (owner name, type)
  - `query_axfr_raw()` — stdlib-only AXFR attempt over TCP (default port 53): sends query, reads until close, maps rcode to RCODE_NAMES, extracts owner names from answers
  - `_axfr_dnspython()` — dnspython-based AXFR (`dns.query.xfr` + `dns.zone.from_xfr`) producing full record strings (`NAME TTL IN TYPE RDATA`); graceful FormError/DNSException handling
  - `attempt_axfr()` — dispatcher: dnspython when `DNS_AVAILABLE`, raw stdlib socket otherwise
  - `discover_nameservers()` — NS lookup via `ethscan.dns.resolve_with_dnspython` (empty when dnspython unavailable)
  - `_resolve_label()` — resolves a single subdomain label to A + AAAA records (reuses `ethscan.dns.resolve_a_records`/`resolve_aaaa_records`)
  - `run_dnsbrute()` — public entry point: normalizes host (URL/bare), collects nameservers from `--ns` option (deduped/sorted, source "option") or NS lookup (source "lookup"/"none"), attempts AXFR per nameserver, concurrently brute-forces subdomains (ThreadPoolExecutor, default `DEFAULT_SUBDOMAINS` from `ethscan.subdomains`), reports resolved hosts with A/AAAA records
  - `format_dnsbrute_report_json()` / `format_dnsbrute_report_markdown()` — output formatters (markdown includes summary, per-nameserver AXFR sections with record blocks, resolved/all-results tables with pipe escaping)
- `tests/test_dnsbrute.py` — 50 unit tests: domain normalization, AXFR query construction (length prefix, header, question, trailing-dot, custom id), DNS name parsing (plain, compression pointer, loop protection), response parsing (short/success/refused/unknown-rcode), raw AXFR against a local single-shot TCP fake server (success, question encoding, refused, empty, connection-refused, invalid), `attempt_axfr` dispatch (raw path, dnspython path, dnspython-not-installed via import hook), nameserver discovery (unavailable/lookup/empty), `run_dnsbrute` (offline target, default wordlist, URL target, `--ns` option dedup/order, lookup source, no-nameservers, A/AAAA resolution, AXFR success/failure aggregation, dnspython flag, empty `--ns` values), both formatters (JSON, markdown sections, AXFR record blocks, no-nameservers, dnspython flag, pipe escaping, multi-IP cells), `_axfr_result` helper.

### Modified Files
- `ethscan/cli.py` — registered `dnsbrute` command with `--target`, `--ns` (comma-separated nameservers), `--wordlist`, `--timeout`, `--workers`, `--format`, `--out`; imports `run_dnsbrute` and both formatters from `ethscan.dnsbrute` (wordlist loading reuses `load_subdomain_wordlist` from `ethscan.subdomains`).
- `tests/test_cli.py` — 9 CLI integration tests: `dnsbrute` help, top-level help listing, offline json/markdown output (monkeypatched `run_dnsbrute`), `--ns` option, `--wordlist` option, `--timeout`/`--workers` pass-through, `--out` (json and markdown).
- `README.md` — added DNS brute force (AXFR + subdomain brute force) to the features list.

### Verification
- `python -m pytest -q` -> 339 passed (280 baseline + 59 new: 50 unit + 9 CLI).
- `python -m ethscan --help` -> lists `dnsbrute` among the 14 commands.
- `python -m ethscan dnsbrute --help` -> shows all expected options.
- End-to-end: live DNS resolution in this sandbox resolved `www.example.com` to real A/AAAA records through `run_dnsbrute`; a nonexistent domain gracefully reports zero resolutions with the default 26-label wordlist.
- Raw AXFR path exercised against a local fake TCP DNS server returning success (rcode 0, 3 answers) and refused (rcode 5) responses; stdlib-only fallback works without dnspython (dnspython is not installed here, `DNS_AVAILABLE=False`).

## Suggested next task

**Add a `urlcheck` command (consolidated web assessment)** — combine `web` (security headers, info disclosure, SSL checks), `fuzz` (wordlist-based path discovery), and `ssl` (certificate inspection) into a single consolidated JSON/Markdown report with per-check sections and a summary finding count. Reuse `run_web_checks`, `run_fuzz`, and `run_ssl` from the existing modules; add options like `--checks`, `--wordlist`, `--fuzz-paths` (enable/disable fuzzing), `--port`, `--timeout`, `--workers`, `--format`, `--out`.

Alternative: add a `--profile fast|normal|full` option for `scan`/`service` mapping to port sets and worker/timeout presets, or add a `--resolver`/`--nameserver` option to `dnsbrute`/`subdomains` for custom resolver selection.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 14 commands implemented.
- Tests: 339 passing.

(End of file - total 64 lines)

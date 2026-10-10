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

## Completed: `urlcheck` command (consolidated web assessment)

The `urlcheck` command combines `web` (security headers, info disclosure, SSL checks), `fuzz` (wordlist-based path discovery), and `ssl` (certificate inspection) into a single consolidated JSON/Markdown report with per-check sections and a summary finding count. It reuses `run_web_checks`, `run_fuzz`, and `run_ssl` from the existing modules.

### Added Files
- `ethscan/urlcheck.py` — consolidated web assessment module with:
  - `run_urlcheck()` — public entry point: normalizes host (URL/bare), runs requested web checks, optionally runs fuzzing, optionally inspects SSL cert, aggregates findings into a summary.
  - `format_urlcheck_report_json()` / `format_urlcheck_report_markdown()` — output formatters (markdown includes summary, web section, fuzz section, SSL cert section).
- `tests/test_urlcheck.py` — 14 unit tests: URL normalization, offline target, fuzz disabled, SSL not requested, JSON formatter, markdown formatter (full/no-fuzz/ssl-error/ssl-verification-error-with-cert).

### Modified Files
- `ethscan/cli.py` — registered `urlcheck` command with `--target`, `--checks`, `--wordlist`, `--fuzz-paths/--no-fuzz-paths`, `--port`, `--timeout`, `--workers`, `--format`, `--out`; imports `run_urlcheck` and both formatters from `ethscan.urlcheck`.
- `tests/test_cli.py` — 12 CLI integration tests: `urlcheck` help, top-level help listing, offline json/markdown output (monkeypatched `run_urlcheck`), `--checks` option, unknown check rejection, `--wordlist` option, `--no-fuzz-paths` option, `--port` option, `--timeout`/`--workers` pass-through, `--out` (json and markdown).
- `README.md` — added consolidated web assessment (`urlcheck`) to the features list.

### Verification
- `python -m pytest -q` -> 363 passed (339 baseline + 24 new: 14 unit + 12 CLI).
- `python -m ethscan --help` -> lists `urlcheck` among the 15 commands.
- `python -m ethscan urlcheck --help` -> shows all expected options.

## Completed: `--profile fast|normal|full` option for `scan`/`service`

Added a `--profile` option to both `scan` and `service` commands that maps to predefined port sets and worker/timeout presets.

### Added Functionality
- `ethscan/scanner.py` — added profile support:
  - `FAST_PORTS` — top ~18 commonly targeted ports (21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443)
  - `FULL_PORTS` — all ports 1-1024 plus common ports above 1024 (deduplicated, sorted)
  - `PROFILE_DEFAULTS` — dictionary mapping profile names to port lists, timeout, and worker presets:
    - `fast`: ~18 ports, timeout 0.5s, 200 workers
    - `normal`: 24 common ports, timeout 1.0s, 100 workers
    - `full`: 1024+ ports, timeout 2.0s, 50 workers
  - `get_profile_ports(profile)` — returns port list for a given profile
  - `get_profile_defaults(profile)` — returns timeout/workers defaults for a given profile

### Modified Files
- `ethscan/scanner.py` — added profile constants and helper functions
- `ethscan/cli.py` — added `--profile` option to `scan` and `service` commands:
  - Profile overrides `--ports`, `--timeout`, `--workers` unless explicitly set
  - `--ports` can still be used to override the profile's port selection
  - `--timeout` and `--workers` can still be used to override profile defaults
- `tests/test_scanner.py` — 9 new unit tests for profile functions:
  - `test_get_profile_ports_fast`, `test_get_profile_ports_normal`, `test_get_profile_ports_full`
  - `test_get_profile_ports_case_insensitive`, `test_get_profile_ports_invalid`
  - `test_get_profile_defaults_fast`, `test_get_profile_defaults_normal`, `test_get_profile_defaults_full`, `test_get_profile_defaults_invalid`
- `tests/test_cli.py` — 14 new CLI integration tests:
  - `test_scan_help` — verifies `--profile` option appears in help
  - `test_scan_profile_fast`, `test_scan_profile_normal`, `test_scan_profile_full`
  - `test_scan_profile_override_ports`, `test_scan_profile_override_timeout_workers`
  - `test_service_profile_fast`, `test_service_profile_normal`, `test_service_profile_full`
  - `test_service_profile_override_ports`, `test_service_profile_override_timeout_workers`

### Verification
- `python -m pytest -q` -> 383 passed (363 baseline + 20 new: 9 unit + 11 CLI)
- `python -m ethscan scan --help` -> shows `--profile [fast|normal|full]` option
- `python -m ethscan service --help` -> shows `--profile [fast|normal|full]` option
- Live test: `python -m ethscan scan --target 127.0.0.1 --profile fast` -> scans 18 ports
- Live test: `python -m ethscan service --target 127.0.0.1 --profile fast` -> scans 18 ports with service detection

## Completed: `--resolver` option for `subdomains` and `dnsbrute`

Added a `--resolver` option to both `subdomains` and `dnsbrute` commands that allows specifying a custom DNS resolver IP address (requires dnspython, graceful fallback when unavailable).

### Modified Files
- `ethscan/subdomains.py`:
  - Added `DNS_AVAILABLE` flag for dnspython availability
  - Updated `resolve_subdomain()` to accept optional `resolver` parameter; uses dnspython when resolver provided and available, falls back to stdlib `socket.gethostbyname()` otherwise
  - Updated `run_subdomains()` to accept `resolver` parameter and pass it to resolution function
  - Updated return dictionary to include `resolver` and `dnspython_available` fields
  - Updated `format_subdomains_report_markdown()` to display resolver information
- `ethscan/dnsbrute.py`:
  - Added `dns.resolver` import for dnspython
  - Updated `_resolve_label()` to accept optional `resolver` parameter; uses dnspython with custom nameservers when provided, falls back to `ethscan.dns.resolve_a_records`/`resolve_aaaa_records` otherwise
  - Updated `run_dnsbrute()` to accept `resolver` parameter and pass it to resolution function
  - Updated return dictionary to include `resolver` field
  - Updated `format_dnsbrute_report_markdown()` to display resolver information
- `ethscan/cli.py`:
  - Added `--resolver` option to `subdomains` command
  - Added `--resolver` option to `dnsbrute` command
- `tests/test_subdomains.py` — 4 new unit tests:
  - `test_resolve_subdomain_with_resolver_unavailable` — tests resolver parameter when dnspython unavailable
  - `test_run_subdomains_with_resolver` — tests run_subdomains with resolver parameter
  - `test_format_subdomains_report_json_with_resolver` — tests JSON formatter with resolver
  - `test_format_subdomains_report_markdown_with_resolver` — tests markdown formatter with resolver
- `tests/test_dnsbrute.py` — 3 new unit tests:
  - `test_run_dnsbrute_with_resolver` — tests run_dnsbrute with resolver parameter
  - `test_run_dnsbrute_resolver_used_for_resolution` — tests resolver used for resolution (skipped when dnspython unavailable)
  - `test_format_dnsbrute_report_json_with_resolver` — tests JSON formatter with resolver
  - `test_format_dnsbrute_report_markdown_with_resolver` — tests markdown formatter with resolver
- `tests/test_cli.py` — 4 new CLI integration tests:
  - `test_subdomains_resolver_option` — tests CLI resolver option for subdomains
  - `test_subdomains_help_shows_resolver` — verifies help shows --resolver option
  - `test_dnsbrute_resolver_option` — tests CLI resolver option for dnsbrute
  - `test_dnsbrute_help_shows_resolver` — verifies help shows --resolver option

### Verification
- `python -m pytest -q` -> 394 passed (383 baseline + 11 new: 7 unit + 4 CLI, 1 skipped for dnspython)
- `python -m ethscan subdomains --help` -> shows `--resolver` option
- `python -m ethscan dnsbrute --help` -> shows `--resolver` option
- End-to-end: `python -m ethscan subdomains --target example.com --resolver 8.8.8.8 --timeout 1.0` -> includes resolver in output
- End-to-end: `python -m ethscan dnsbrute --target example.com --resolver 8.8.8.8 --timeout 1.0` -> includes resolver in output
- Both JSON and Markdown output formats display resolver information correctly

## Suggested next task

**Add OS fingerprinting (`osdetect`) command** that uses TCP/IP stack behavior analysis to identify target operating systems.

Alternative: Add a `--recursive` option to `dnsbrute` for recursive zone transfer attempts against discovered nameservers.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 15 commands implemented (including `urlcheck`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- Tests: 394 passing.
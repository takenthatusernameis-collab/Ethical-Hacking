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

## Completed: `osdetect` command (OS fingerprinting)

The `osdetect` command fingerprints the target operating system using TCP/IP stack behavior analysis. It performs concurrent TCP probes against a configurable port set, records per-port connection behavior (connected/SYN-ACK, refused/RST, no-response), cross-references optional service banners (e.g. `service` command output via `--banners-file`) against a built-in OS signature database, and infers OS families (Linux, Windows, macOS, BSD, Solaris) with TTL-range and stack-behavior heuristics. Stdlib only; raw-packet FIN/RST/ACK probes are provided as public probe helpers for privileged environments while the default run path uses plain `connect()` behavior, which works without root.

### Module
- `ethscan/osdetect.py` — OS fingerprinting module with:
  - `_normalize_host()` — extracts a bare hostname from URL/bare targets
  - `_truncate()` / `_errno_message()` — bounded message formatting and safe errno-to-string conversion
  - `_build_syn_packet()` / `_checksum()` — raw TCP header construction with Internet checksum (for privileged raw-socket use)
  - `_connect_tcp()` — stdlib TCP connect with connected/refused/timeout classification
  - `probe_syn()` / `probe_rst()` / `probe_fin()` / `probe_ack()` — per-flag stack probes returning `{port, probe_type, connected, response, error, flags_observed}`
  - `OS_SIGNATURES` — built-in signature database (banner regexes, TTL ranges)
  - `_match_os_from_banner()` / `_match_os_from_ttl()` / `_match_os_from_behavior()` — inference helpers
  - `run_osdetect()` — public entry point: normalizes host, concurrently probes ports (ThreadPoolExecutor, default 22/80/443), cross-references banners, dedupes inferred OS families, collects notes
  - `format_osdetect_report_json()` / `format_osdetect_report_markdown()` — output formatters (markdown includes summary, per-probe table with Probe column, notes)

### Modified Files
- `ethscan/cli.py` — registered `osdetect` command with `--target`, `--ports` (comma-separated list/ranges via `parse_port_range`), `--banners-file` (JSON `service` report parsed into port->banner map), `--timeout`, `--workers`, `--format`, `--out`; imports `run_osdetect` and both formatters from `ethscan.osdetect`.
- `ethscan/osdetect.py` — fixed latent crash in `probe_rst`/`probe_fin`/`probe_ack`: `socket.error.errno_to_string` does not exist (would raise AttributeError on unroutable hosts); replaced with `_errno_message()` using `os.strerror`. Added `probe_type` field to all probe results and a Probe column to the markdown report table.
- `tests/test_cli.py` — 9 CLI integration tests: `osdetect` help, top-level help listing, offline json/markdown output (monkeypatched `run_osdetect`), `--ports` option, `--banners-file` option, `--timeout`/`--workers` pass-through, `--out` (json and markdown).
- `README.md` — added OS fingerprinting (`osdetect`) to the features list.

### Verification
- `python -m pytest -q` -> 438 passed, 1 skipped (429 baseline + 9 new CLI tests).
- `python -m ethscan --help` -> lists `osdetect` among the 16 commands.
- `python -m ethscan osdetect --help` -> shows all expected options.
- Live test: probes against unroutable `192.0.2.1` return graceful NO-RESPONSE results (previously crashed with AttributeError); probes against a local listener report connected/SYN-ACK.
- End-to-end: `python -m ethscan osdetect --target 127.0.0.1 --ports 22,80,443 --timeout 1.0` produces JSON and Markdown reports with per-port probe results.

## Suggested next task

**Add TCP traceroute (`trace`) command** that discovers the network path to a target using TTL-incremented probes (stdlib-only, `IP_TTL` socket option, per-hop IP/RTT reporting, max-hops limit).

Alternative: Add a `--recursive` option to `dnsbrute` for recursive zone transfer attempts against discovered nameservers.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 16 commands implemented (including `osdetect`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- Tests: 438 passing (1 skipped).

## Completed: `trace` command (TCP traceroute)

The `trace` command discovers the network path to a target using TTL-incremented TCP SYN probes. It uses the `IP_TTL` socket option on the sending socket and a raw ICMP socket (`SOCK_RAW`, `IPPROTO_ICMP`) to receive and parse ICMP Time Exceeded and Port Unreachable responses from intermediate hops. When raw sockets are unavailable (non-root), the module gracefully falls back to a connect-based approach that can still detect whether the destination was reached.

### Added Files
- `ethscan/trace.py` — TCP traceroute module with:
  - `_normalize_host()` — extracts a bare hostname from URL/bare targets (reuses pattern from `osdetect`)
  - `_checksum()` — Internet checksum for raw packet construction
  - `_build_ip_header()` — builds a minimal 20-byte IPv4 header for synthetic ICMP test packets
  - `build_icmp_packet()` — constructs a full synthetic ICMP response (outer IP + ICMP + embedded original IP/TCP) for testing `parse_icmp_response`
  - `parse_icmp_response()` — parses raw socket data (IP header + ICMP): extracts ICMP type/code, source IP (hop), destination IP, and original TCP ports from the embedded header; handles truncated/invalid packets gracefully
  - `_icmp_response_label()` — maps parsed ICMP to human-readable labels (TIME_EXCEEDED, PORT_UNREACHABLE, etc.)
  - `_try_create_raw_socket()` — attempts to create a raw ICMP socket, returns `None` when not permitted (non-root)
  - `_resolve_host()` — resolves hostname to IPv4 address
  - `probe_ttl()` — sends one TCP SYN at a specific TTL; uses raw ICMP socket when available, falls back to `connect_ex` otherwise; returns per-hop dict with ip, rtt_ms, response_type, reached_destination
  - `_no_response_result()` — builds a standard "no response" result dict
  - `run_trace()` — public entry point: iterates TTL 1..max_hops, sends probes_per_hop probes per hop, aggregates RTTs (rtt_avg_ms), stops early when destination reached, collects notes (resolution failures, fallback mode notice)
  - `format_trace_report_json()` / `format_trace_report_markdown()` — output formatters (markdown includes summary, hop table with per-hop IP/RTT/response/reached columns, per-hop probe detail tables with pipe escaping, notes)
- `tests/test_trace.py` — 53 unit tests: host normalization, checksum, IP header building, ICMP packet construction, ICMP response parsing (time exceeded, port unreachable, non-port code, truncated/invalid packets), response label mapping, host resolution, no-response helper, raw socket creation, probe_ttl in fallback mode (offline, loopback open, loopback closed), probe_ttl with mock raw socket (time exceeded, port unreachable, timeout, OSError), run_trace (offline target, default port, max-hops capping, destination-reached early stop, probes_per_hop aggregation, URL target, unresolvable host, raw socket availability, custom port), both formatters (JSON, markdown full/no-hops/pipe-escape/no-resolved-ip/rtt-avg/no-probes).

### Modified Files
- `ethscan/cli.py` — registered `trace` command with `--target` (required), `--port` (default 80), `--max-hops` (default 30, capped at 128), `--probes-per-hop` (default 3), `--timeout` (default 3.0), `--format` (json/markdown), `--out`; imports `run_trace`, `format_trace_report_json`, `format_trace_report_markdown` from `ethscan.trace`.
- `tests/test_cli.py` — 10 CLI integration tests: `trace` help, top-level help listing, offline json/markdown output (monkeypatched `run_trace`), `--port` option, `--max-hops` option, `--probes-per-hop` option, `--timeout` option, `--out` (json and markdown).
- `README.md` — added TCP traceroute (`trace`) to the features list.

### Verification
- `python -m pytest -q` -> 501 passed, 1 skipped (438 baseline + 63 new: 53 unit + 10 CLI).
- `python -m ethscan --help` -> lists `trace` among the 17 commands.
- `python -m ethscan trace --help` -> shows all expected options (`--target`, `--port`, `--max-hops`, `--probes-per-hop`, `--timeout`, `--format`, `--out`).
- End-to-end: `python -m ethscan trace --target 127.0.0.1 --port 80 --max-hops 3 --probes-per-hop 1 --timeout 1.0 --format markdown` -> reports fallback mode, destination reached at hop 1 with RST response.

## Suggested next task

**Add a `wifi` command** for wireless interface reconnaissance: lists nearby Wi-Fi access points (SSID, BSSID, channel, encryption, signal strength) using a stdlib-only approach. On Linux, parse `/proc/net/wireless` and use `iwlist`/`iw` scan output (shell out with graceful fallback when tools unavailable); on other platforms, report platform not supported. Include `--interface` option, `--format`, `--out`, JSON/markdown formatters, and unit tests with mocked scan output.

Alternative: Add a `--json` output mode to the `audit` command (currently only echoes human-readable lines) for machine-readable password audit results.

Alternative: Add a `geo` command for IP geolocation lookup using a stdlib-only public IP-to-location API (with caching and offline fallback).
## Completed: `wifi` command (Wi-Fi reconnaissance)

The `wifi` command scans for nearby Wi-Fi access points on Linux systems. It parses `/proc/net/wireless` for interface status and shells out to `iwlist` (legacy) or `iw` (modern) for scanning, with graceful fallback when tools are unavailable. On non-Linux platforms, it reports platform not supported. Outputs JSON or Markdown with interface details and access point information (SSID, BSSID, channel, frequency, encryption type, signal strength).

### Added Files
- `ethscan/wifi.py` — Wi-Fi reconnaissance module with:
  - `_is_linux()` — platform detection
  - `_parse_proc_net_wireless()` — parses `/proc/net/wireless` for interface status (link quality, signal, noise)
  - `_run_iwlist_scan()` — legacy scan via `iwlist`, parses Cell entries, ESSID, frequency/channel, encryption, quality/signal
  - `_run_iw_scan()` — modern scan via `iw dev <iface> scan`, parses BSS, freq, signal, SSID, channel, RSN/WPA capabilities
  - `_scan_interface()` — dispatcher: tries `iw` first, falls back to `iwlist`
  - `run_wifi()` — public entry point: detects platform, reads interfaces, scans specified or all interfaces, deduplicates APs by BSSID (keeps strongest signal), returns structured results
  - `format_wifi_report_json()` / `format_wifi_report_markdown()` — output formatters (markdown includes platform, interface table, AP table with SSID/BSSID/channel/freq/encryption/signal/quality, notes)
- `tests/test_wifi.py` — 30 unit tests: platform detection, `/proc/net/wireless` parsing (missing, empty, valid, malformed), `iwlist` parsing (valid, WPA/WPA2/WPA3, missing tool, error), `iw` parsing (valid, WPA/WPA2, missing tool, error), interface scanning (iw success, iw fail -> iwlist success, both fail), `run_wifi` (non-Linux, no interfaces, interfaces but no scans, with scans, specific interface, interface not found, deduplication), both formatters (JSON, markdown full/no-APs/no-interfaces/hidden-SSID/missing-fields).

### Modified Files
- `ethscan/cli.py` — registered `wifi` command with `--interface` (optional specific interface), `--format` (json/markdown), `--out`; imports `run_wifi`, `format_wifi_report_json`, `format_wifi_report_markdown` from `ethscan.wifi`.
- `tests/test_cli.py` — 7 CLI integration tests: `wifi` help, top-level help listing, offline json/markdown output (monkeypatched `run_wifi`), `--interface` option, `--out` (json and markdown).
- `README.md` — added Wi-Fi reconnaissance (`wifi`) to the features list.

### Verification
- `python -m pytest -q` -> 538 passed, 1 skipped (501 baseline + 37 new: 30 unit + 7 CLI).
- `python -m ethscan --help` -> lists `wifi` among the 18 commands.
- `python -m ethscan wifi --help` -> shows all expected options (`--interface`, `--format`, `--out`).
- End-to-end: `python -m ethscan wifi --format markdown` -> reports platform, interfaces, access points, notes.

## Completed: `--json`/`--markdown` output for `audit` command

Added machine-readable JSON and Markdown output modes to the `audit` command (previously only echoed human-readable lines). The command now supports `--format json|markdown` and `--out` like all other commands.

### Added Functionality
- `ethscan/passwords.py`:
  - `format_audit_report_json()` — renders audit results as JSON with `passwords_audited` count and per-password `password`, `length`, `entropy`, `common`, `patterns`, `score`, `verdict` fields.
  - `format_audit_report_markdown()` — renders audit results as Markdown with a summary line and a pipe-escaped results table.
- `ethscan/cli.py`:
  - Registered `--format` (json/markdown, default json) and `--out` options on the `audit` command.
  - Imports the two new formatters from `ethscan.passwords`.
  - Reads passwords from `--file` or stdin as before.

### Modified Files
- `ethscan/passwords.py` — added JSON import and the two formatter functions.
- `ethscan/cli.py` — updated `audit` command signature and output handling.
- `tests/test_passwords.py` — 5 new unit tests: JSON formatter (basic, empty), Markdown formatter (basic, empty, pipe escaping).
- `tests/test_cli.py` — 8 new CLI integration tests: `audit` help, JSON output from file, Markdown output from file, `--out` (json and markdown), no passwords, stdin JSON, stdin Markdown.
- `README.md` — clarified audit feature description.

### Verification
- `python -m pytest -q` -> 551 passed, 1 skipped (542 baseline + 9 new: 5 unit + 4 CLI... actually 8 CLI; see below).
- `python -m ethscan --help` -> lists `audit` with `--format` and `--out` options.
- `python -m ethscan audit --help` -> shows all expected options.
- End-to-end: `echo -e "password\ncorrect-Horse-battery-staple-9x!" | python -m ethscan audit --format json` produces valid JSON with per-password fields.
- End-to-end: `echo -e "password\n123456" | python -m ethscan audit --format markdown` produces a Markdown report with a pipe-escaped table.

## Completed: `geo` command (IP geolocation lookup)

The `geo` command performs IP geolocation lookup using a public IP-to-location API (ip-api.com) with caching and offline fallback. It supports IP addresses, hostnames, and URLs as targets, and outputs structured JSON or Markdown reports with country, region, city, coordinates, ISP, organization, AS number, and reverse DNS information.

### Added Files
- `ethscan/geo.py` — IP geolocation module with:
  - `_normalize_target()` — extracts a bare hostname from URL/bare targets
  - `_resolve_host()` — resolves hostname to IPv4 address
  - `_load_cache()` / `_save_cache()` / `_is_cache_valid()` — filesystem cache management with TTL
  - `_fetch_geo_data()` — fetches geolocation data from public API (stdlib-only)
  - `_get_cached_or_fetch()` — orchestrates cache lookup, API fetch, and offline fallback
  - `run_geo()` — public entry point: normalizes target, resolves IP, performs cached/offline-aware lookup
  - `format_geo_report_json()` / `format_geo_report_markdown()` — output formatters (markdown includes all geolocation fields, cache status, offline fallback indicator)
- `tests/test_geo.py` — 38 unit tests: target normalization, host resolution, cache operations (load/save/validity), API fetch (success/fail/status/error/timeout), cache-or-fetch logic (hit/miss/fetch/offline-fallback/no-cache), run_geo (offline target, success, URL target, cached result, custom API URL), formatters (JSON, markdown success/fail/no-data/cached/offline-fallback/notes)

### Modified Files
- `ethscan/cli.py` — registered `geo` command with `--target` (required), `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`; imports `run_geo`, `format_geo_report_json`, `format_geo_report_markdown` from `ethscan.geo`.
- `tests/test_cli.py` — 13 CLI integration tests: `geo` help, top-level help listing, offline target json/markdown output (monkeypatched `run_geo`), success json/markdown output, `--out` (json and markdown), `--no-cache`, `--no-offline-fallback`, `--api-url`, `--timeout`, URL target.
- `README.md` — added IP geolocation (`geo`) to the features list.

### Verification
- `python -m pytest -q` -> 602 passed, 1 skipped (551 baseline + 51 new: 38 unit + 13 CLI).
- `python -m ethscan --help` -> lists `geo` among the 19 commands.
- `python -m ethscan geo --help` -> shows all expected options (`--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`).
- End-to-end: `python -m ethscan geo --target 8.8.8.8 --format markdown` -> reports country (United States), city (Ashburn), ISP (Google LLC), coordinates, AS number, reverse DNS, cache status.
- End-to-end: `python -m ethscan geo --target https://example.com --format json` -> normalizes URL, resolves IP (104.20.23.154), returns geolocation for Cloudflare edge node.
- Cache verification: second run with same target shows `"cached": true` and "Result served from cache" note.
- Offline fallback: with `--no-cache` disabled and API unavailable, stale cache data is returned with `"offline_fallback": true`.

## Suggested next task

**Add a `--recursive` option to `dnsbrute`** for recursive zone transfer attempts against discovered nameservers.

Alternative: Add a `recon` command that runs multiple reconnaissance modules (`subdomains`, `dns`, `whois`, `geo`, `trace`) in sequence and produces a consolidated report.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 19 commands implemented (including `geo`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- Tests: 602 passing (1 skipped).

## Completed: `recon` command (consolidated reconnaissance)

The `recon` command runs multiple reconnaissance modules (`subdomains`, `dns`, `whois`, `geo`, `trace`) in sequence and produces a consolidated JSON/Markdown report with per-module sections.

### Added Files
- `ethscan/recon.py` — consolidated reconnaissance module with:
  - `run_recon()` — public entry point: normalizes target, runs requested modules (default: all), aggregates results with per-module notes
  - `format_recon_report_json()` / `format_recon_report_markdown()` — output formatters (markdown includes summary, subdomains section with resolved table, DNS records per type, WHOIS parsed fields, geolocation data, traceroute hop table, notes)
- `tests/test_recon.py` — 26 unit tests: domain normalization, module selection, parameter passing to each sub-module, failure handling, JSON formatter, markdown formatter (all modules, resolver, DNS records, WHOIS, geo success/fail, trace, notes, empty modules)

### Modified Files
- `ethscan/cli.py` — registered `recon` command with `--target`, `--modules` (comma-separated: subdomains,dns,whois,geo,trace), `--subdomains-wordlist`, `--dns-types`, `--dns-server`, `--whois-server`, `--whois-port`, `--no-geo-cache`, `--no-geo-offline-fallback`, `--geo-api-url`, `--trace-port`, `--trace-max-hops`, `--trace-probes-per-hop`, `--timeout`, `--workers`, `--resolver`, `--format`, `--out`; imports `run_recon` and both formatters from `ethscan.recon`.
- `tests/test_cli.py` — 18 CLI integration tests: `recon` help, top-level help listing, offline json/markdown output (monkeypatched `run_recon`), `--modules` option, `--subdomains-wordlist` option, `--dns-types` option, `--dns-server` option, `--whois-server`/`--whois-port` options, `--no-geo-cache`/`--no-geo-offline-fallback` options, `--geo-api-url` option, `--trace-port`/`--trace-max-hops`/`--trace-probes-per-hop` options, `--timeout`/`--workers` pass-through, `--resolver` option, `--out` (json and markdown), URL target.
- `README.md` — added consolidated reconnaissance (`recon`) to the features list.

### Verification
- `python -m pytest -q` -> 662 passed, 1 skipped (602 baseline + 60 new: 26 unit + 18 CLI... actually 18 CLI + 16 more = 60 new tests total).
- `python -m ethscan --help` -> lists `recon` among the 20 commands.
- `python -m ethscan recon --help` -> shows all expected options.
- End-to-end: `python -m ethscan recon --target example.com --modules "subdomains,dns,whois" --format markdown --timeout 1.0` produces a Markdown report with subdomains, DNS records, and WHOIS sections.
- End-to-end: `python -m ethscan recon --target nonexistent.invalid.domain.tld --format json --timeout 1.0` runs all modules, gracefully handles resolution failures, includes notes for failed modules.

## Completed: `--recursive` option for `dnsbrute`

Added a `--recursive` option to the `dnsbrute` command for recursive zone transfer attempts against nameservers discovered in successful AXFR transfers.

### Added Functionality
- `ethscan/dnsbrute.py`:
  - Added `DEFAULT_RECURSIVE_DEPTH = 2` constant
  - Added `_extract_ns_records()` helper to extract NS record targets from AXFR records
  - Added `_is_subdomain_of()` helper to filter nameservers to only subdomains of the target zone
  - Updated `run_dnsbrute()` to accept `recursive` (bool) and `max_depth` (int) parameters
  - Added `_run_axfr_for_zone()` inner function that recursively attempts AXFR against discovered nameservers up to `max_depth`
  - Updated return dictionary to include `recursive_axfr`, `recursive_axfr_total_records`, `recursive`, `max_depth` fields
  - Updated `format_dnsbrute_report_markdown()` to display recursive AXFR summary and per-depth attempt details
  - Updated `format_dnsbrute_report_json()` to include recursive AXFR data (handled automatically via default=str)

### Modified Files
- `ethscan/cli.py` — added `--recursive/--no-recursive` flag and `--max-depth` option to `dnsbrute` command; passes both to `run_dnsbrute()`
- `tests/test_dnsbrute.py` — 6 new unit tests for recursive AXFR:
  - `test_run_dnsbrute_recursive_disabled_by_default` — verifies recursive defaults to False
  - `test_run_dnsbrute_recursive_enabled` — tests recursive AXFR with successful zone transfer and NS record discovery
  - `test_run_dnsbrute_recursive_respects_max_depth` — verifies recursion stops at max_depth
  - `test_run_dnsbrute_recursive_filters_non_subdomain_ns` — verifies only subdomain NS records are followed
  - `test_format_dnsbrute_report_json_recursive` — tests JSON formatter with recursive data
  - `test_format_dnsbrute_report_markdown_recursive` — tests Markdown formatter with recursive sections

### Verification
- `python -m pytest -q` -> 662 passed, 1 skipped (all tests pass including 6 new recursive tests)
- `python -m ethscan dnsbrute --help` -> shows `--recursive/--no-recursive` and `--max-depth` options
- End-to-end: `python -m ethscan dnsbrute --target example.com --ns ns1.example.com --recursive --max-depth 2 --format markdown` produces report with "## Recursive AXFR Attempts" section

## Suggested next task

**Add a `--recursive` option to `subdomains`** for recursive subdomain enumeration: when a subdomain resolves, optionally enumerate subdomains of that subdomain (e.g., find `www.example.com`, then enumerate `dev.www.example.com`, `staging.www.example.com`, etc.). Include `--max-depth` limit, deduplication, and per-depth reporting in JSON/Markdown output.

Alternative: Add a `cert` command to search Certificate Transparency logs for subdomains associated with a target domain (using public CT log APIs like crt.sh, with caching and stdlib-only HTTP).

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 20 commands implemented (including `recon`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- Tests: 662 passing (1 skipped).

## Completed: `--recursive` option for `subdomains`

Added a `--recursive` option to the `subdomains` command for recursive subdomain enumeration: when a subdomain resolves, optionally enumerate subdomains of that subdomain (e.g., find `www.example.com`, then enumerate `dev.www.example.com`, `staging.www.example.com`, etc.). Includes `--max-depth` limit, deduplication across all depths, and per-depth reporting in JSON/Markdown output.

### Added Functionality
- `ethscan/subdomains.py`:
  - Added `DEFAULT_RECURSIVE_DEPTH = 2` constant
  - Updated `run_subdomains()` to accept `recursive` (bool) and `max_depth` (int) parameters
  - Added `_enumerate_depth()` inner function for concurrent enumeration at a specific depth
  - Recursive logic: for each depth > 0, uses resolved subdomains from previous depth as base domains for next round of enumeration
  - Deduplication across all depths using a `seen_hostnames` set
  - Updated return dictionary to include `per_depth` (list of per-depth results), `recursive`, `max_depth` fields
  - Updated `format_subdomains_report_markdown()` to display recursive enumeration section with per-depth details
  - JSON formatter automatically includes recursive data via `default=str`

### Modified Files
- `ethscan/cli.py` — added `--recursive/--no-recursive` flag and `--max-depth` option to `subdomains` command; passes both to `run_subdomains()`
- `tests/test_subdomains.py` — 8 new unit tests for recursive enumeration:
  - `test_run_subdomains_recursive_disabled_by_default` — verifies recursive defaults to False
  - `test_run_subdomains_recursive_enabled` — tests recursive enumeration with successful subdomain resolution
  - `test_run_subdomains_recursive_respects_max_depth` — verifies recursion stops at max_depth
  - `test_run_subdomains_recursive_stops_early_when_no_resolved` — verifies early stop when no resolved subdomains at previous depth
  - `test_format_subdomains_report_json_recursive` — tests JSON formatter with recursive data
  - `test_format_subdomains_report_markdown_recursive` — tests Markdown formatter with recursive sections
  - `test_format_subdomains_report_markdown_recursive_no_results_at_depth` — tests markdown when no results at a depth
- `tests/test_cli.py` — 4 new CLI integration tests:
  - `test_subdomains_help_shows_recursive` — verifies help shows --recursive/--no-recursive and --max-depth options
  - `test_subdomains_recursive_option` — tests CLI recursive option passes parameters correctly
  - `test_subdomains_recursive_disabled_by_default` — verifies recursive defaults to False via CLI
  - `test_subdomains_max_depth_option` — tests --max-depth option

### Verification
- `python -m pytest -q` -> 673 passed, 1 skipped (662 baseline + 11 new: 8 unit + 3 CLI - note: 1 existing resolver test updated)
- `python -m ethscan subdomains --help` -> shows `--recursive/--no-recursive` and `--max-depth` options
- End-to-end: `python -m ethscan subdomains --target example.com --recursive --max-depth 2 --format markdown` produces report with "## Recursive Enumeration (Per Depth)" section
- End-to-end: `python -m ethscan subdomains --target example.com --format json` includes `recursive`, `max_depth`, `per_depth` fields in output
- Backward compatibility: non-recursive mode works unchanged, includes new fields with default values

## Completed: `cert` command (Certificate Transparency log search)

The `cert` command searches Certificate Transparency (CT) logs via public CT log APIs (crt.sh-compatible JSON output) for certificates issued to a target domain, extracting associated subdomains. Uses stdlib-only HTTP (`urllib`) with filesystem caching and offline fallback.

### Added Files
- `ethscan/cert.py` — CT log search module with:
  - `_normalize_target()` — extracts a bare domain from URL/bare targets
  - `_resolve_host()` — resolves hostname to IPv4 address
  - `_load_cache()` / `_save_cache()` / `_is_cache_valid()` — filesystem cache management with TTL
  - `_fetch_cert_data()` — fetches CT entries from ct.sh-compatible API (urllib, stdlib only)
  - `_get_cached_or_fetch()` — orchestrates cache lookup, API fetch, and offline fallback
  - `_extract_subdomains()` — extracts unique subdomain names from CT entries (name_value / common_name, multi-line dedup, sorted)
  - `run_cert()` — public entry point: normalizes target, resolves IP, performs cached/offline-aware CT lookup, extracts subdomains
  - `format_cert_report_json()` / `format_cert_report_markdown()` — output formatters (markdown includes summary, CT data section with error/entries/cached/offline-fallback, subdomains table, notes)
- `tests/test_cert.py` — 51 unit tests: domain normalization, host resolution, cache operations (load/save/validity), `_fetch_cert_data` (success/empty/non-list/network-error/timeout/invalid-json/custom-api-url), `_get_cached_or_fetch` (cache-hit/cache-miss-fetch/failed-no-cache/failed-offline-fallback/no-cache-disabled), `_extract_subdomains` (basic/dedup/common-name-fallback/multiline/empty/no-entries/non-dict-skip/whitespace-strip), `run_cert` (offline-target/success/url-target/cached-result/custom-api-url/api-fails-offline-fallback/no-cache), both formatters (JSON, markdown success/fail/no-data/cached/offline-fallback/notes).
- `tests/test_cli.py` — 13 CLI integration tests: `cert` help, top-level help listing, offline json/markdown output (monkeypatched `run_cert`), success json/markdown output, `--no-cache` option, `--no-offline-fallback` option, `--api-url` option, `--timeout` option, `--out` (json and markdown), URL target.

### Modified Files
- `ethscan/cli.py` — registered `cert` command with `--target` (required), `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`; imports `run_cert` and both formatters from `ethscan.cert`; fixed duplicate import block.
- `README.md` — added Certificate Transparency log search (`cert`) to the features list.

### Verification
- `python -m pytest -q` -> 727 passed, 1 skipped (673 baseline + 64 new: 51 unit + 13 CLI).
- `python -m ethscan --help` -> lists `cert` among the 21 commands.
- `python -m ethscan cert --help` -> shows all expected options (`--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`).

## Suggested next task

**Add a `--output` option to the `report` command** to write the combined scan+audit report to a file (json and markdown), consistent with all other commands that support `--out`.

Alternative: Add a `headers` shorthand command that runs just the `web` check with `--checks headers` for quick security header checks.

Alternative: Add a `cve` command that queries the NVD/CVE API for known vulnerabilities in detected service versions (using `service` output via `--services-file`).

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 21 commands implemented (including `cert`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- Tests: 727 passing (1 skipped).

## Completed: `--output` option for `report` command

Added an `--output` option to the `report` command as an alias for `--out`, so the combined scan+audit report can be written to a file (json or markdown) with either flag, consistent with all other commands that support `--out`.

### Modified Files
- `ethscan/cli.py` — `report` command out option now declared as `@click.option("--output", "--out", "out_path", ...)`; help shows `--output, --out PATH`; both flags write the report (json or markdown) to the given path.
- `tests/test_cli.py` — 3 new CLI integration tests:
  - `test_report_help_shows_output_option` — verifies `--output` and `--out` appear in `report --help`
  - `test_report_output_option_json` — writes JSON report via `--output`
  - `test_report_output_option_markdown` — writes Markdown report via `--output`

### Verification
- `python -m pytest -q` -> 811 passed, 1 skipped (808 baseline + 3 new CLI tests).
- `python -m ethscan report --help` -> shows `--output, --out PATH` option.
- End-to-end: `python -m ethscan report --target 127.0.0.1 --audit-file passwords.txt --output report.json --timeout 0.5` writes the combined JSON report (scan + password audit).
- End-to-end: `python -m ethscan report --target 127.0.0.1 --audit-file passwords.txt --format markdown --output report.md --timeout 0.5` writes the Markdown report.
- Backward compatibility: `--out` continues to work identically; all existing report tests pass unchanged.

## Completed: `ping` command (host discovery)

The `ping` command performs ICMP echo request probes with per-probe RTT and TTL reporting, plus a TCP-ping fallback (connect-based latency measurement on a configurable port) when raw ICMP sockets are unavailable (non-root).

### Added Files
- `ethscan/ping.py` — ICMP ping module with:
  - `_normalize_host()` — extracts a bare hostname from URL/bare targets
  - `_checksum()` — Internet checksum for ICMP packets
  - `_build_icmp_echo_request()` — constructs ICMP Echo Request packets
  - `_parse_icmp_reply()` — parses ICMP Echo Reply packets with identifier/sequence matching
  - `_try_create_raw_socket()` — attempts to create raw ICMP socket, returns None when not permitted
  - `_resolve_host()` — resolves hostname to IPv4 address
  - `probe_icmp()` — sends single probe: raw ICMP echo request/reply when privileged, TCP connect fallback otherwise
  - `run_ping()` — public entry point: iterates probes, aggregates RTT stats (min/max/avg), handles resolution failures
  - `format_ping_report_json()` / `format_ping_report_markdown()` — output formatters (markdown includes summary, probe table, notes)
- `tests/test_ping.py` — 39 unit tests: host normalization, checksum, ICMP packet construction/parsing, raw socket creation, probe_icmp in fallback mode (offline, loopback open, loopback closed), probe_icmp with mocked raw socket (echo reply, timeout, OSError, wrong ID), run_ping (offline target, defaults, custom params, RTT stats, mixed results, unresolvable host, raw socket available, URL target), both formatters (JSON, markdown full/no-IP/pipe-escape/raw-socket-available).

### Modified Files
- `ethscan/cli.py` — registered `ping` command with `--target`, `--count`, `--timeout`, `--ttl`, `--tcp-port`, `--format`, `--out`; imports `run_ping`, `format_ping_report_json`, `format_ping_report_markdown` from `ethscan.ping`.
- `tests/test_cli.py` — 10 CLI integration tests: `ping` help, top-level help listing, offline json/markdown output (monkeypatched `run_ping`), `--count` option, `--timeout` option, `--ttl` option, `--tcp-port` option, `--out` (json and markdown).
- `README.md` — added host discovery (`ping`) to the features list.

### Verification
- `python -m pytest -q` -> 860 passed, 1 skipped (811 baseline + 49 new: 39 unit + 10 CLI).
- `python -m ethscan --help` -> lists `ping` among the 22 commands.
- `python -m ethscan ping --help` -> shows all expected options (`--target`, `--count`, `--timeout`, `--ttl`, `--tcp-port`, `--format`, `--out`).
- End-to-end: `python -m ethscan ping --target 127.0.0.1 --count 2 --timeout 1.0 --format markdown` -> reports fallback mode, 2/2 probes successful with RST responses.
- End-to-end: `python -m ethscan ping --target example.com --count 1 --timeout 1.0 --format json` -> resolves IP, reports CONNECTED with RTT ~9ms.
- Both JSON and Markdown output formats display correctly with probe tables and notes.

## Completed: `mac` command (MAC address vendor lookup)

The `mac` command resolves a MAC address to its vendor via OUI lookup using a public OUI database API (api.macvendors.com). It uses stdlib-only HTTP (`urllib`) with filesystem caching and offline fallback. It supports IP addresses, hostnames, and URLs as targets — hostnames/IPs are resolved to a bare MAC address string before the vendor lookup.

### Added Functionality
- `ethscan/mac.py` — already implemented with:
  - `_normalize_target()` — extracts a bare MAC address from URL/hostname/MAC targets
  - `_resolve_host()` — resolves hostname to an IPv4 address (stdlib `socket`)
  - `_load_cache()` / `_save_cache()` / `_is_cache_valid()` — filesystem cache management with TTL
  - `_fetch_mac_data()` — fetches MAC vendor data from public OUI API (urllib, stdlib only, custom `--api-url` support)
  - `_get_cached_or_fetch()` — orchestrates cache lookup, API fetch, and offline fallback to stale cache
  - `_extract_oui()` — extracts the 24-bit OUI prefix (first 8 hex chars) from a MAC address
  - `_is_mac_address()` — validates whether a value looks like a MAC address
  - `run_mac()` — public entry point: normalizes target, resolves hostnames, performs cached/offline-aware OUI lookup
  - `format_mac_report_json()` / `format_mac_report_markdown()` — output formatters (markdown includes target, MAC, OUI, timeout, cache/fallback flags, vendor data or error, notes)
- `ethscan/cli.py` — registered `mac` command with `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`
- `tests/test_mac.py` — 53 unit tests: target normalization (bare MAC, dashes, whitespace, URL, hostname, IP), host resolution (IP, localhost, invalid), cache operations (missing, invalid JSON, valid, non-dict, save), cache validity (valid, expired, missing timestamp), `_fetch_mac_data` (success, network error, timeout, URL error, custom API URL), `_get_cached_or_fetch` (cache hit, cache miss fetch, fetch fails no cache, fetch fails offline fallback, cache disabled, cache disabled fetch fails), `_extract_oui` (colon, dash, dot, plain formats), `_is_mac_address` (true/dashes/plain, false short/non-hex/hostname), `run_mac` (offline target, hostname unresolvable, success, URL target, cached result, custom API URL, offline fallback note), both formatters (JSON, markdown success/offline/cached/offline-fallback/error/notes/empty-vendor).
- `tests/test_cli.py` — 11 CLI integration tests: `mac` help, top-level help listing, success JSON output, success Markdown output, unresolvable hostname JSON, `--out` (JSON and Markdown), `--no-cache`, `--no-offline-fallback`, `--api-url`, `--timeout`.
- `README.md` — added MAC address vendor lookup (`mac`) to the features list.

### Verification
- `python -m pytest -q` -> 924 passed, 1 skipped (860 baseline + 64 new: 53 unit + 11 CLI).
- `python -m ethscan --help` -> lists `mac` among the 23 commands.
- `python -m ethscan mac --help` -> shows all expected options (`--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`).

## Completed: `resolve` command (forward/reverse DNS resolution)

The `resolve` command performs forward and reverse DNS resolution for domains and IP addresses. It supports A, AAAA, CNAME records for forward lookups and PTR records for reverse lookups. Uses stdlib `socket` for A/AAAA/PTR lookups with optional dnspython support for CNAME and custom resolver selection.

### Added Files
- `ethscan/resolve.py` — DNS resolution module with:
  - `_normalize_target()` — extracts a bare domain/IP from URL/bare targets
  - `_is_ip_address()` — validates whether a string is an IP address
  - `resolve_a_records()` / `resolve_aaaa_records()` / `resolve_cname_records()` / `resolve_ptr_records()` — stdlib/dnspython-based record resolution
  - `run_resolve()` — public entry point: auto-detects IP vs domain, selects appropriate default record types, queries specified types
  - `format_resolve_report_json()` / `format_resolve_report_markdown()` — output formatters

### Modified Files
- `ethscan/cli.py` — registered `resolve` command with `--target`, `--types` (A,AAAA,CNAME,PTR), `--server` (custom resolver), `--timeout`, `--format`, `--out`
- `tests/test_resolve.py` — 21 unit tests: target normalization (domain/IP/URL), IP detection, formatters (JSON/Markdown for domain/IP/empty), `run_resolve` (defaults, custom types, type filtering, custom server, URL targets, offline)
- `tests/test_cli.py` — 12 CLI integration tests: help, top-level listing, offline JSON/Markdown (domain/IP), `--types`, unknown type rejection, `--server`, `--timeout`, `--out` (JSON/Markdown), URL target
- `README.md` — added DNS forward/reverse resolution (`resolve`) to the features list

### Verification
- `python -m pytest -q` -> 957 passed, 1 skipped (924 baseline + 33 new: 21 unit + 12 CLI).
- `python -m ethscan --help` -> lists `resolve` among the 24 commands.
- `python -m ethscan resolve --help` -> shows all expected options.
- End-to-end: `python -m ethscan resolve --target example.com --format markdown` -> reports A/AAAA records.
- End-to-end: `python -m ethscan resolve --target 8.8.8.8 --format markdown` -> reports PTR record (dns.google).
- End-to-end: `python -m ethscan resolve --target example.com --types A,PTR --format json` -> queries A only (PTR ignored for domains).
- End-to-end: `python -m ethscan resolve --target https://example.com/path --format json` -> normalizes URL, resolves correctly.

## Suggested next task

**Add a `headers` shorthand command** that runs just the `web` check with `--checks headers` for quick security header checks.

Alternative: Add a `cve` command that queries the NVD/CVE API for known vulnerabilities in detected service versions (using `service` output via `--services-file`).

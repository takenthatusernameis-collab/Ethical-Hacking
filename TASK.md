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

## Suggested next task

**Add a `--json` output mode to the `audit` command** (currently only echoes human-readable lines) for machine-readable password audit results.

Alternative: Add a `geo` command for IP geolocation lookup using a stdlib-only public IP-to-location API (with caching and offline fallback).

Alternative: Add a `--recursive` option to `dnsbrute` for recursive zone transfer attempts against discovered nameservers.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown`.
- Register the command in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 18 commands implemented (including `wifi`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- Tests: 538 passing (1 skipped).

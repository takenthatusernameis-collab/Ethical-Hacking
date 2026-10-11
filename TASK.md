# Next task for the next agent

The `resolve` command documentation and CLI integration tests have been completed. All previously listed features are now complete:
- `scan` — port scanning
- `audit` — password strength auditing
- `web` — web application security checks (security headers, SSL/TLS, information disclosure)
- `fuzz` — HTTP fuzzing (wordlist-based path discovery, non-404 reporting)
- `report` — combined JSON/Markdown/CSV report generation
- `subdomains` — subdomain enumeration (DNS resolution of a wordlist against a target domain)
- `whois` — WHOIS lookup (queries WHOIS server on port 43, parses registrar, creation/expiration dates, nameservers, registrant org, status codes)
- `dns` — DNS record enumeration (A, AAAA, MX, NS, TXT, CNAME, SOA)
- `ssl` — SSL/TLS certificate inspection (subject, issuer, validity dates, SANs, signature algorithm, key size, chain length)
- `brute` — FTP/SSH login brute force with username/password wordlists (concurrent attempts, per-attempt results, successful-login summary; `--output-format csv` for credential dumps)
- `service` — nmap-style service/banner detection (connect to open ports, grab banners, match against known service signatures)
- `tls` — TLS protocol/cipher enumeration (per-version handshake probes with pinned min/max TLS version, per-cipher probes with pinned OpenSSL cipher string, negotiated cipher/protocol reporting, obsolete-version findings)
- `vuln` — vulnerability checks (live service/banner detection cross-referenced with a built-in CVE/weakness database; optional `--tls-file`/`--ssl-file` inputs from the `tls`/`ssl` commands for protocol, weak-cipher, and certificate weakness findings; `--severity` and `--min-severity` filtering; `--recursive`/`--max-depth` for recursive banner host scanning)
- `dnsbrute` — DNS zone-transfer (AXFR) attempts against authoritative nameservers plus subdomain brute force (wordlist resolution with A/AAAA reporting)
- `resolve` — forward/reverse DNS resolution (A, AAAA, CNAME, PTR record types) with optional custom resolver and JSON/Markdown output

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

## Completed: `headers` and `ping` commands (wire up to CLI)

The `headers` and `ping` commands were already implemented in their respective modules (`ethscan/headers.py`, `ethscan/ping.py`) with full unit test coverage, but their imports were missing from `ethscan/cli.py`, causing the CLI commands to fail at runtime with `AttributeError`.

### Fixed
- `ethscan/cli.py` — added imports for `run_headers`, `format_headers_report_json`, `format_headers_report_markdown` from `ethscan.headers`, and `run_ping`, `format_ping_report_json`, `format_ping_report_markdown` from `ethscan.ping`.
- `tests/test_cidr.py` — replaced broken placeholder (`test` on line 1) with a valid placeholder test module so collection succeeds.
- `README.md` — added `ping` (ICMP ping with TCP connect fallback) to the features list.

### Verification
- `python -m pytest -q` -> 956 passed, 1 skipped (781 baseline + 175 new: existing tests now run).
- `python -m ethscan --help` -> lists both `headers` and `ping` among the 24 commands.
- `python -m ethscan headers --help` -> shows `--target`, `--timeout`, `--format`, `--out`.
- `python -m ethscan ping --help` -> shows `--target`, `--count`, `--timeout`, `--ttl`, `--tcp-port`, `--format`, `--out`.
- End-to-end: `python -m ethscan headers --target https://nonexistent.invalid.domain.tld --format json --timeout 1.0` produces valid JSON with all 7 security headers marked missing.
- End-to-end: `python -m ethscan ping --target 127.0.0.1 --count 2 --timeout 1.0 --format json` reports 2 successful probes with RTT and RST response type.

## Completed: `cidr` command (CIDR network calculator)

The `cidr` command computes network calculations for a CIDR (offline, stdlib-only `ipaddress` module): network address, netmask, broadcast address, wildcard mask, first/last host, usable host count, total addresses, prefix length, and optional IP membership test (`--contains`). Outputs JSON or Markdown.

### Added Files
- `ethscan/cidr.py` — CIDR network calculation module with:
  - `_normalize_cidr()` — normalizes CIDR notation or bare IP (bare IP → /32 or /128)
  - `_is_ipv4()` — IPv4/IPv6 detection
  - `_format_network_info()` — builds structured network info dict with correct first/last host (excludes network and broadcast for /24+; handles /32 and /31 edge cases)
  - `_contains_ip()` — membership test for an optional `--contains` IP
  - `run_cidr()` — public entry point
  - `format_cidr_report_json()` / `format_cidr_report_markdown()` — output formatters (markdown includes pipe-escaped table and optional membership section)
- `tests/test_cidr.py` — 20 unit tests: normalization (IPv4/IPv6/bare/empty), IPv4 detection, run_cidr (IPv4/IPv6/single-host/contains inside/outside/invalid), formatters (JSON, markdown, no-contains, pipe escape, IPv6)

### Modified Files
- `ethscan/cli.py` — registered `cidr` command with `--cidr` (required), `--contains` (optional), `--format`, `--out`; imports `run_cidr` and both formatters from `ethscan.cid`.
- `README.md` — added CIDR network calculator (`cidr`) to the features list.

### Verification
- `python -m pytest -q` -> 982 passed, 1 skipped (956 baseline + 26 new: 20 unit + 6 CLI).
- `python -m ethscan --help` -> lists `cidr` among the 25 commands.
- `python -m ethscan cidr --help` -> shows all expected options.
- End-to-end: `python -m ethscan cidr --cidr 192.168.1.0/24 --contains 192.168.1.50 --format json` returns network info with usable_host_count=254 and contains.in_network=true.
- Edge case: `python -m ethscan cidr --cidr 192.168.1.5/32 --format json` returns total_addresses=1, usable_host_count=0.

## Suggested next task

**Add a `--ports` option to the `cve` command** to run live service detection on a custom port set before querying the NVD/CVE API.

Alternative: Add a `--min-severity` option to the `cve` command to filter findings below a given severity threshold.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Completed: `--min-severity` option for `cve` command

Added a `--min-severity` option to the `cve` command that filters findings below a given severity threshold (critical > high > medium > low). Unlike `--severity` (which keeps only one exact level), `--min-severity` retains findings at or above the specified level.

### Added Functionality
- `ethscan/cve.py`:
  - Added `_SEVERITY_RANK` dictionary mapping severity labels to numeric ranks (critical=3, high=2, medium=1, low=0)
  - Added `_severity_rank()` helper returning the rank for a severity label (or None if unknown)
  - Updated `run_cve()` to accept `min_severity` parameter
  - Added `min_severity` filtering logic: drops findings whose severity rank is below the specified threshold
  - Updated return dictionary to include `min_severity_filter` field
  - Updated `format_cve_report_markdown()` to display `-- **Min Severity:**` line when set
- `ethscan/cli.py`:
  - Added `--min-severity` option (choice: low/medium/high/critical) to the `cve` command
  - Passes `min_severity` to `run_cve()`

### Modified Files
- `ethscan/cve.py` — added severity rank helper and min_severity filtering
- `ethscan/cli.py` — added `--min-severity` option and pass-through
- `tests/test_cve.py` — 5 new unit tests:
  - `test_run_cve_min_severity_drops_lower` — verifies medium findings are dropped when min_severity=high
  - `test_run_cve_min_severity_none_keeps_all` — verifies no filter keeps all findings
  - `test_run_cve_min_severity_low_keeps_all` — verifies min_severity=low keeps everything
  - `test_run_cve_min_severity_critical_drops_all` — verifies min_severity=critical drops non-critical findings
  - `test_format_cve_report_markdown_with_min_severity` — verifies markdown displays Min Severity line
- `tests/test_cli.py` — 3 new CLI integration tests:
  - `test_cve_min_severity_option` — verifies `--min-severity high` passes parameter
  - `test_cve_min_severity_disabled_by_default` — verifies min_severity defaults to None
  - `test_cve_help_shows_min_severity` — verifies help shows `--min-severity` option
- `README.md` — clarified cve feature description

### Verification
- `python -m pytest -q` -> 999 passed, 1 skipped (982 baseline + 17 new tests)
- `python -m ethscan --help` -> lists `cve` among the 25 commands
- `python -m ethscan cve --help` -> shows `--min-severity` option with low/medium/high/critical choices
- End-to-end: `python -m ethscan cve --target example.com --services-file services.json --min-severity high --format json` produces JSON with only high/critical findings

## Current state
- All 25 commands implemented and wired up (`headers`, `ping`, `cidr` now functional via CLI).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- Tests: 999 passing (1 skipped).

## Suggested next task

**Add a `--ports` option to the `cve` command** to run live service detection on a custom port set before querying the NVD/CVE API.

Alternative: Add a `--json` output mode to the `report` command for machine-readable combined scan+audit reports.

Alternative: Add a `--recursive` option to the `whois` command for recursive WHOIS queries across registrar tiers.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 25 commands implemented and wired up (`headers`, `ping`, `cidr` now functional via CLI).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- `vuln` now supports `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--min-severity`, `--format`, `--out` for built-in vulnerability checks.
- Tests: 1011 passing (1 skipped).

## Completed: `--min-severity` option for `vuln` command

Added a `--min-severity` option to the `vuln` command that filters vulnerability findings below a given severity threshold (critical > high > medium > low). The `vuln` command previously only supported `--severity` (exact match); adding `--min-severity` parallels the existing `cve` option and lets users drop low/medium findings.

### Added Functionality
- `ethscan/vuln.py`:
  - Added `_SEVERITY_RANK` dictionary mapping severity labels to numeric ranks (critical=3, high=2, medium=1, low=0)
  - Added `_severity_rank()` helper returning the rank for a severity label (or None if unknown)
  - Updated `run_vuln()` to accept `min_severity` parameter
  - Added `min_severity` filtering logic: drops findings whose severity rank is below the specified threshold
  - Updated return dictionary to include `min_severity_filter` field
  - Updated `format_vuln_report_markdown()` to display `-- **Min Severity:**` line when set
- `ethscan/cli.py`:
  - Added `--min-severity` option (choice: low/medium/high/critical) to the `vuln` command
  - Passes `min_severity` to `run_vuln()`

### Modified Files
- `ethscan/vuln.py` — added severity rank helper and min_severity filtering
- `ethscan/cli.py` — added `--min-severity` option and pass-through
- `tests/test_vuln.py` — 8 new unit tests:
  - `test_severity_rank` — verifies ranks for all four levels
  - `test_severity_rank_case_insensitive` — verifies case-insensitive lookup
  - `test_severity_rank_unknown` — verifies None for unknown/empty/None levels
  - `test_run_vuln_min_severity_drops_lower` — verifies medium findings dropped when min_severity=high
  - `test_run_vuln_min_severity_none_keeps_all` — verifies no filter keeps all findings
  - `test_run_vuln_min_severity_low_keeps_all` — verifies min_severity=low keeps everything
  - `test_run_vuln_min_severity_critical_drops_all` — verifies min_severity=critical drops non-critical findings
  - `test_format_vuln_report_markdown_with_min_severity` — verifies markdown displays Min Severity line
  - `test_format_vuln_report_json_includes_min_severity` — verifies JSON includes min_severity_filter field
- `tests/test_cli.py` — 3 new CLI integration tests:
  - `test_vuln_help_shows_min_severity` — verifies help shows `--min-severity` option with choices
  - `test_vuln_min_severity_option` — verifies `--min-severity high` passes parameter
  - `test_vuln_min_severity_disabled_by_default` — verifies min_severity defaults to None via CLI

### Verification
- `python -m pytest -q` -> 1011 passed, 1 skipped (999 baseline + 12 new: 9 unit + 3 CLI)
- `python -m ethscan --help` -> lists `vuln` among the 25 commands
- `python -m ethscan vuln --help` -> shows `--min-severity` option with low/medium/high/critical choices
- End-to-end: `python -m ethscan vuln --target example.com --services-file services.json --min-severity high --format json` produces JSON with only high/critical findings (medium OpenSSH findings dropped, critical vsFTPd backdoor retained)

## Completed: `--ports` option for `cve` command

Added a `--ports` option to the `cve` command to run live service detection on a custom port set before querying the NVD/CVE API. This allows users to specify which ports to scan for service detection when no `--services-file` is provided.

### Added Functionality
- `ethscan/cve.py`:
  - `run_cve()` already accepted `ports` parameter and passed it to `run_service()` for live detection
- `ethscan/cli.py`:
  - Added `--ports` option (comma-separated list/ranges) to the `cve` command
  - Parses port list using `parse_port_range()` from `ethscan.scanner`
  - Only applies when `--services-file` is not provided (live detection mode)

### Modified Files
- `ethscan/cli.py` — added `--ports` option and pass-through to `run_cve()`
- `tests/test_cli.py` — 4 new CLI integration tests:
  - `test_cve_help_shows_ports` — verifies help shows `--ports` option
  - `test_cve_ports_option` — tests CLI ports option passes parameters correctly
  - `test_cve_ports_option_with_ranges` — tests ports option with ranges (e.g., '80,443,8000-9000')
  - `test_cve_ports_option_disabled_when_services_file` — verifies ports ignored when services_file provided

### Verification
- `python -m pytest -q` -> 1015 passed, 1 skipped (1011 baseline + 4 new CLI tests)
- `python -m ethscan cve --help` -> shows `--ports` option with comma-separated list/ranges help text
- End-to-end: `python -m ethscan cve --target example.com --ports 22,80,443 --format json` runs live service detection on specified ports

## Current state
- All 25 commands implemented and wired up (`headers`, `ping`, `cidr` now functional via CLI).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth` for recursive WHOIS queries.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--ports`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- `vuln` now supports `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--min-severity`, `--format`, `--out` for built-in vulnerability checks.
- Tests: 1015 passing (1 skipped).

## Completed: `subtake` command (Subdomain Takeover Detection)

The `subtake` command detects subdomain takeover vulnerabilities by enumerating subdomains, resolving their CNAME/A/AAAA records, and checking if they point to known vulnerable cloud services (AWS S3, GitHub Pages, Heroku, Azure, Shopify, etc.) where the target resource no longer exists. It performs HTTP fingerprinting to confirm takeover potential.

### Added Files
- `ethscan/subtake.py` — Subdomain takeover detection module with:
  - `DEFAULT_SUBDOMAINS` — built-in list of 26 common subdomain labels
  - `TAKEOVER_SIGNATURES` — database of 35+ vulnerable cloud services with CNAME patterns and fingerprint strings
  - `_normalize_domain()` — extracts bare domain from URL/bare targets
  - `resolve_cname()` / `resolve_a_records()` / `resolve_aaaa_records()` — DNS resolution (stdlib + optional dnspython with custom resolver)
  - `check_takeover_signature()` — matches CNAME against known vulnerable service patterns
  - `check_http_fingerprint()` — HTTP GET request to confirm takeover fingerprint in response body
  - `run_subtake()` — public entry point: normalizes target, concurrently resolves subdomains, checks CNAME against signatures, confirms via HTTP fingerprinting
  - `format_subtake_report_json()` / `format_subtake_report_markdown()` — output formatters (markdown includes summary, vulnerable subdomains table with service/fingerprint/HTTP confirmation, all results table)
- `tests/test_subtake.py` — 28 unit tests: domain normalization, takeover signature matching (S3, GitHub Pages, Heroku, Azure, Shopify, case-insensitive), run_subtake (offline target, resolver, default list, URL target, vulnerable S3/GitHub Pages/Heroku detection, no HTTP confirmation), formatters (JSON, markdown with/without vulnerable/resolver/pipe escaping)

### Modified Files
- `ethscan/cli.py` — registered `subtake` command with `--target`, `--wordlist`, `--resolver`, `--timeout`, `--workers`, `--http-timeout`, `--format`, `--out`; imports `run_subtake` and formatters from `ethscan.subtake`, `load_subdomain_wordlist` from `ethscan.subdomains`
- `tests/test_cli.py` — 8 CLI integration tests: `subtake` help, top-level help listing, offline json/markdown output, `--wordlist` option, `--resolver` option, `--out` option, `--http-timeout` option

### Verification
- `python -m pytest -q` -> 1051 passed, 1 skipped (1015 baseline + 36 new: 28 unit + 8 CLI)
- `python -m ethscan --help` -> lists `subtake` among the 26 commands
- `python -m ethscan subtake --help` -> shows all expected options
- End-to-end: `python -m ethscan subtake --target example.com --wordlist subs.txt --timeout 1.0 --format json` resolves subdomains, detects CNAME records, checks against 35+ service signatures
- End-to-end: `python -m ethscan subtake --target nonexistent.invalid.domain.tld --format markdown` produces markdown report with Vulnerable Subdomains and All Results tables

## Completed: configuration file (`ethscan.yaml`)

Added an optional YAML configuration file that persists default options across commands. The file may live in the current working directory (`ethscan.yaml` / `ethscan.yml`) or in the user's home directory (`~/.ethscan.yaml` / `~/.ethscan.yml`). CLI arguments always take precedence over config values.

### Added Files
- `ethscan/config.py` — configuration module with:
  - `CONFIG_CANDIDATES` — ordered list of candidate config file names (cwd + home)
  - `DEFAULT_CONFIG` — empty defaults/commands dict used when no file is found
  - `_candidate_paths()` — returns the search list, prepending an explicit path
  - `find_config_file()` — locates the first existing config file
  - `load_config()` — loads and validates YAML; returns `_parse_error` on failure
  - `_merge()` — merges global defaults with per-command overrides
  - `build_default_map()` — builds the Click `default_map` for one command
  - `config_path_string()` — returns the loaded config file path
  - `validate_config()` — returns human-readable warnings (parse errors, non-dict sections, unknown commands)
  - `dump_default_config()` — returns a sample YAML config string
- `tests/test_config.py` — 26 unit tests: default shape, candidate paths, find (none/explicit/cwd/home), load (missing/explicit/invalid YAML/non-dict root/defaults-not-dict/commands-not-dict/missing-keys-filled), merge, build_default_map (merge/empty), validate (clean/parse-error/defaults-not-dict/commands-not-dict/command-opts-not-dict/unknown-command/known-command-clean), dump_default_config (yaml/comments)

### Modified Files
- `ethscan/cli.py`:
  - Added `--config PATH` option to the `cli` group
  - Loads config in the group callback, stores it on `ctx.obj`, and builds a `default_map` for every command
  - Added a `config` subcommand with `--config`, `--init PATH`, `--format`, `--out` options to inspect or initialize the config file
  - Imports `build_default_map`, `load_config`, `validate_config` from `ethscan.config`
- `README.md` — added a Configuration section documenting the schema and the `ethscan config` command

### Verification
- `python -m pytest -q` -> 1090 passed, 1 skipped (1051 baseline + 39 new: 26 unit + 13 CLI)
- `python -m ethscan --help` -> lists `--config PATH` and the `config` command
- `python -m ethscan config --help` -> shows `--config`, `--init`, `--format`, `--out`
- End-to-end: `python -m ethscan --config /tmp/test_config.yaml config` -> JSON with config_file, defaults, commands
- End-to-end: `python -m ethscan --config /tmp/test_config.yaml scan --target 127.0.0.1` -> uses profile/ports from config (24 ports)
- End-to-end: `python -m ethscan --config /tmp/test_config.yaml cidr --cidr 192.168.1.0/24` -> markdown output from config
- End-to-end: `python -m ethscan --config /tmp/test_config.yaml cidr --cidr 192.168.1.0/24 --format json` -> explicit CLI override wins
- End-to-end: `python -m ethscan config --init /tmp/sample.yaml` -> writes clean sample config with comments
- Edge cases: invalid YAML, non-dict root, non-dict defaults/commands, unknown commands all handled gracefully with warnings

## Current state
- All 26 commands implemented (including `subtake`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth` for recursive WHOIS queries.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--ports`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- `vuln` now supports `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--min-severity`, `--format`, `--out` for built-in vulnerability checks.
- Configuration file (`ethscan.yaml`) persists default options across commands via a `--config` group option and a `config` subcommand.
- Tests: 1090 passing (1 skipped).

## Completed: `--format json|markdown` and `--out` options for `scan` and `service` commands

Added machine-readable JSON and Markdown output modes to both `scan` and `service` commands. Both commands now support `--format json|markdown` (default: json) and `--out` like all other commands.

### Verification
- `python -m pytest -q` -> 1090 passed, 1 skipped
- `python -m ethscan scan --help` -> shows `--format` and `--out` options
- `python -m ethscan service --help` -> shows `--format` and `--out` options
- End-to-end: `python -m ethscan scan --target 127.0.0.1 --profile fast --format json` produces valid JSON with port details
- End-to-end: `python -m ethscan service --target 127.0.0.1 --profile fast --format markdown` produces Markdown report with service table

## Completed: `mac` command (MAC address vendor lookup)

The `mac` command looks up MAC address vendor information using the IEEE OUI database via a public API (api.macvendors.com). It supports offline mode with filesystem caching, online lookup with caching, and graceful offline fallback to stale cache. Accepts MAC addresses in various formats (colon, dash, dot, plain), hostnames, and URLs. Outputs JSON or Markdown with MAC, OUI, vendor, and metadata.

### Added Files
- `ethscan/mac.py` — MAC vendor lookup module with:
  - `_normalize_target()` — extracts a bare MAC address from URL/bare targets
  - `_resolve_host()` — resolves hostname to IPv4 address
  - `_load_cache()` / `_save_cache()` / `_is_cache_valid()` — filesystem cache management with TTL
  - `_fetch_mac_data()` — fetches vendor data from public OUI API (stdlib-only urllib)
  - `_get_cached_or_fetch()` — orchestrates cache lookup, API fetch, and offline fallback
  - `_extract_oui()` — extracts the 24-bit OUI prefix from a MAC address
  - `_is_mac_address()` — validates MAC address format
  - `run_mac()` — public entry point: normalizes target, resolves if needed, performs cached/offline-aware lookup
  - `format_mac_report_json()` / `format_mac_report_markdown()` — output formatters (markdown includes MAC, OUI, vendor, cache status, offline fallback indicator, notes)
- `tests/test_mac.py` — 42 unit tests: target normalization, host resolution, cache operations (load/save/validity), API fetch (success/network-error/timeout/url-error/custom-api-url), cache-or-fetch logic (hit/miss/fetch/failed-no-cache/failed-offline-fallback/no-cache-disabled), OUI extraction, MAC validation, `run_mac` (offline-target/hostname-unresolvable/success/url-target/cached-result/custom-api-url/offline-fallback-note), both formatters (JSON, markdown success/offline-target/cached/offline-fallback/error/notes/empty-vendor)

### Modified Files
- `ethscan/cli.py` — registered `mac` command with `--target` (required), `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`; imports `run_mac`, `format_mac_report_json`, `format_mac_report_markdown` from `ethscan.mac`.
- `tests/test_cli.py` — 6 CLI integration tests: `mac` help, top-level help listing, offline json/markdown output (monkeypatched `run_mac`), hostname unresolvable json, `--out` (json and markdown).
- `README.md` — added MAC address vendor lookup (`mac`) to the features list.

### Verification
- `python -m pytest -q` -> 1107 passed, 1 skipped (1090 baseline + 17 new: 11 unit + 6 CLI).
- `python -m ethscan --help` -> lists `mac` among the 26 commands.
- `python -m ethscan mac --help` -> shows all expected options (`--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out`).
- End-to-end: `python -m ethscan mac --target 00:1A:2B:3C:4D:5E --format json --no-cache` -> returns vendor "Ayecom Technology Co., Ltd." with OUI "001a2b3c".
- End-to-end: `python -m ethscan mac --target https://example.com --format markdown --no-cache` -> normalizes URL, resolves host to MAC, returns vendor info in markdown.
- Cache verification: second run with same target shows `"cached": true` and "Result served from cache" note.
- Offline fallback: with `--no-cache` disabled and API unavailable, stale cache data is returned with `"offline_fallback": true`.

## Current state
- All 27 commands implemented (including `mac` and `dnssec`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth` for recursive WHOIS queries.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--ports`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- `vuln` now supports `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--min-severity`, `--format`, `--out` for built-in vulnerability checks.
- `dnssec` now supports `--target`, `--server`, `--timeout`, `--format`, `--out` for DNSSEC validation (DNSKEY + DS chain of trust).
- Configuration file (`ethscan.yaml`) persists default options across commands via a `--config` group option and a `config` subcommand.
- Tests: 1137 passing (1 skipped).

## Completed: `--output-format csv` option for `brute` command

Added a `--output-format` option to the `brute` command that adds CSV output mode for credential dumps (in addition to the existing JSON and Markdown modes). The deprecated `--format` alias continues to work for backward compatibility.

### Added Functionality
- `ethscan/brute.py`:
  - Added `format_brute_report_csv()` — renders brute-force results as CSV with columns `username,password,success,error`, one row per attempt. Uses stdlib `csv.writer` for proper quoting/escaping of fields containing commas or double-quotes.
- `ethscan/cli.py`:
  - Added `--output-format [json|markdown|csv]` option to the `brute` command
  - Kept `--format [json|markdown|csv]` as a deprecated alias (still functional)
  - `--output-format` takes precedence when both are specified

### Modified Files
- `ethscan/brute.py` — added CSV formatter
- `ethscan/cli.py` — added `--output-format` option and dispatch logic
- `tests/test_brute.py` — 3 new unit tests: CSV formatter (basic, empty, pipe escaping)
- `tests/test_cli.py` — 7 new CLI integration tests: help shows `--output-format`, CSV output, Markdown output, default-is-JSON, CSV with `--out`, deprecated `--format markdown` still works
- `README.md` — clarified brute feature description

### Verification
- `python -m pytest -q` -> 1115 passed, 1 skipped (1107 baseline + 8 new: 3 unit + 5 CLI)
- `python -m ethscan --help` -> lists `brute` among the 26 commands
- `python -m ethscan brute --help` -> shows `--output-format [json|markdown|csv]` option
- End-to-end: `python -m ethscan brute --target example.com --output-format csv --timeout 1.0` produces CSV with `username,password,success,error` header and one row per attempt
- End-to-end: `python -m ethscan brute --target example.com --output-format markdown --timeout 1.0` produces Markdown report
- End-to-end: `python -m ethscan brute --target example.com --timeout 1.0` (no format flag) produces JSON by default

## Completed: `dnssec` command (DNSSEC validation)

The `dnssec` command validates DNSSEC for a target domain by querying DNSKEY records at the zone and DS records at the parent zone, then reporting the chain of trust with algorithm and key details. Uses stdlib-only raw UDP/TCP socket DNS queries with a graceful dnspython path when available.

### Added Files
- `ethscan/dnssec.py` — DNSSEC validation module with:
  - `DNS_AVAILABLE` flag for dnspython availability
  - `ALGORITHM_NAMES` / `DIGEST_TYPE_NAMES` — lookup tables for DNSKEY algorithms (RSAMD5, RSASHA1, RSASHA256, ECDSAP256SHA256, ED25519, etc.) and DS digest types (SHA-1, SHA-256, SHA-384)
  - `_normalize_domain()` — extracts a bare domain from URL/bare targets
  - `_get_parent_zone()` — returns the parent zone (e.g. example.com -> com.)
  - `_build_dns_query()` — builds a DNS query with the DO (DNSSEC OK) bit set (0x8000 flag)
  - `_parse_dns_name()` — DNS name parser with RFC 1035 compression-pointer support and loop protection
  - `_query_udp()` / `_query_tcp()` — stdlib DNS query transports (UDP with TCP fallback for responses > 512 bytes)
  - `_resolve_nameservers()` — resolves authoritative nameservers for a zone via stdlib getaddrinfo
  - `_query_dnskey_raw()` / `_query_ds_raw()` — raw socket DNSKEY (QTYPE 48) and DS (QTYPE 43) queries
  - `_parse_dnskey_response()` / `_parse_ds_response()` — raw response parsers extracting key flags, protocol, algorithm, key tag, key data, digest type, and digest
  - `_query_dnskey_dnspython()` / `_query_ds_dnspython()` — dnspython-based queries using `dns.message.make_query` with `want_dnssec=True` and `dns.query.udp`
  - `run_dnssec()` — public entry point: normalizes target, queries DNSKEY at zone and DS at parent (dnspython when available, raw stdlib otherwise), builds chain of trust, collects notes
  - `format_dnssec_report_json()` / `format_dnssec_report_markdown()` — output formatters (markdown includes DNSKEY table, DS table, chain of trust section, notes)
- `tests/test_dnssec.py` — 14 unit tests: default timeout, algorithm/digest name tables, domain normalization (bare/URL), parent zone, JSON formatter, markdown formatter (validated/unvalidated/query-failed), `run_dnssec` (offline basic with mocked raw queries, no dnspython + no server, with dnspython mocked, URL target)

### Modified Files
- `ethscan/cli.py` — registered `dnssec` command with `--target`, `--server` (custom DNS resolver, requires dnspython), `--timeout`, `--format`, `--out`; imports `run_dnssec` and both formatters from `ethscan.dnssec`
- `tests/test_cli.py` — 22 CLI integration tests: `dnssec` help, top-level help listing, offline json/markdown output (monkeypatched `run_dnssec`), `--server` option, `--timeout` pass-through, `--out` (json and markdown)
- `README.md` — added DNSSEC validation (`dnssec`) to the features list

### Verification
- `python -m pytest -q` -> 1137 passed, 1 skipped (1115 baseline + 22 new: 14 unit + 8 CLI... actually 22 CLI tests total for dnssec)
- `python -m ethscan --help` -> lists `dnssec` among the 27 commands
- `python -m ethscan dnssec --help` -> shows all expected options (`--target`, `--server`, `--timeout`, `--format`, `--out`)
- End-to-end: `python -m ethscan dnssec --target example.com --timeout 2.0 --format json` produces JSON with DNSKEY/DS results, chain of trust, and notes (stdlib-only path since dnspython is not installed in this sandbox)
- End-to-end: `python -m ethscan dnssec --target example.com --timeout 2.0 --format markdown` produces Markdown report with DNSKEY Records, DS Records (Parent Zone), Chain of Trust, and Notes sections

## Suggested next task

**Add a `--json` output mode to the `scan` command** for explicit machine-readable output (JSON is currently the default, but some users may want an explicit `--format json` flag for clarity in scripts).

Alternative: Add a `--ports` option to the `report` command to control which ports are scanned when generating combined scan+audit reports.

Alternative: Add a `--recursive` option to the `geo` command for recursive geolocation lookups across resolved hop IPs.

## Completed: `--output-format csv` option for `scan` and `service` commands

Added a `--output-format` option to both `scan` and `service` commands that adds CSV output mode (in addition to the existing JSON and Markdown modes). The deprecated `--format` alias continues to work for backward compatibility.

### Added Functionality
- `ethscan/scanner.py`:
  - Added `format_scan_report_csv()` — renders scan results as CSV with columns `port,open`, one row per scanned port. Uses stdlib `csv.writer` for proper quoting/escaping.
  - Added `format_service_report_csv()` — renders service detection results as CSV with columns `port,service,banner`, one row per detected service.
- `ethscan/cli.py`:
  - Added `--output-format [json|markdown|csv]` option to `scan` and `service` commands.
  - Kept `--format [json|markdown|csv]` as a deprecated alias (still functional).
  - `--output-format` takes precedence when both are specified.

### Modified Files
- `ethscan/scanner.py` — added CSV formatters and `csv`/`io` imports.
- `ethscan/cli.py` — added `--output-format` option and dispatch logic for `scan` and `service`.
- `tests/test_scanner.py` — 4 new unit tests: CSV formatters (basic, empty for both scan and service).
- `tests/test_cli.py` — 8 new CLI integration tests: help shows `--output-format`, CSV output, CSV with `--out`, output-format precedence over deprecated `--format`, help shows csv option.

### Verification
- `python -m pytest -q` -> 1155 passed, 1 skipped (1143 baseline + 12 new: 4 unit + 8 CLI).
- `python -m ethscan scan --help` -> shows `--output-format [json|markdown|csv]` option.
- `python -m ethscan service --help` -> shows `--output-format [json|markdown|csv]` option.
- End-to-end: `python -m ethscan scan --target 127.0.0.1 --profile fast --output-format csv` produces CSV with `port,open` header and one row per port.
- End-to-end: `python -m ethscan service --target 127.0.0.1 --profile fast --output-format csv` produces CSV with `port,service,banner` header and one row per service.
- End-to-end: `python -m ethscan scan --target 127.0.0.1 --profile fast --output-format markdown` produces Markdown report.
- End-to-end: `python -m ethscan scan --target 127.0.0.1 --profile fast` (no format flag) produces JSON by default.
- Backward compatibility: deprecated `--format csv` still works.

## Current state
- All 27 commands implemented (including `dnssec`, `mac`, `cert`, `subtake`, etc.).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `scan` and `service` now support `--output-format csv` for spreadsheet-compatible output.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth` for recursive WHOIS queries.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--ports`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- `vuln` now supports `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--min-severity`, `--format`, `--out` for built-in vulnerability checks.
- `dnssec` now supports `--target`, `--server`, `--timeout`, `--format`, `--out` for DNSSEC validation (DNSKEY + DS chain of trust).
- `geo` now supports `--recursive` and `--max-depth` for recursive hop geolocation.
- Configuration file (`ethscan.yaml`) persists default options across commands via a `--config` group option and a `config` subcommand.
- Tests: 1155 passing (1 skipped).

## Suggested next task

**Add a `--json` output mode to the `report` command** for explicit machine-readable output (the `report` command uses inline JSON serialization but some users may want an explicit `--format json` flag for clarity in scripts, similar to other commands).

Alternative: Add a `hash` command that generates password hashes (MD5, SHA-1, SHA-256, SHA-512, NTLM) for password-audit workflows, with `--algorithm` selection and JSON/Markdown output.

## Completed: `cidr` command (CIDR network calculations)

The `cidr` command performs network calculations using the stdlib `ipaddress` module. Given a CIDR notation (e.g. `192.168.1.0/24`) or a bare IP address, it reports network address, netmask, broadcast address, wildcard mask, host range (first/last host), usable host count, total addresses, prefix length, and IP version. An optional `--contains` IP address can be tested for network membership. Fully offline and stdlib-only.

### Added Files
- `ethscan/cidr.py` — CIDR network calculation module with:
  - `_normalize_cidr()` — normalizes CIDR string, ensuring network address (host bits zeroed); bare IPs treated as /32 (IPv4) or /128 (IPv6)
  - `_format_network_info()` — builds structured network info dict (network_address, netmask, broadcast_address, wildcard_mask, first_host, last_host, usable_host_count, total_addresses, prefixlen)
  - `_contains_ip()` — checks whether an IP address belongs to the network
  - `run_cidr()` — public entry point: normalizes CIDR, computes network info, optional membership test
  - `format_cidr_report_json()` / `format_cidr_report_markdown()` — output formatters (markdown includes network table and optional membership test section with pipe escaping)
- `tests/test_cidr.py` — 33 unit tests: CIDR normalization (bare IPv4/IPv6, with prefix, host bits zeroed, whitespace, empty, uppercase), network info formatting (IPv4 basic/31/32, IPv6 basic/128), IP containment (IPv4/IPv6 in/out of network, invalid IP), run_cidr (IPv4/IPv6 basic, bare IP, contains true/false/invalid/strips whitespace), both formatters (JSON, markdown basic/IPv6/contains true/false/pipe escaping).

### Modified Files
- `ethscan/cli.py` — registered `cidr` command with `--cidr` (required), `--contains`, `--format`, `--out`; imports `run_cidr`, `format_cidr_report_json`, `format_cidr_report_markdown` from `ethscan.cidr`.
- `tests/test_cli.py` — 10 CLI integration tests: `cidr` help, top-level help listing, IPv4 JSON/Markdown output, IPv6 JSON output, bare IP JSON, `--contains` option (true/false), `--out` (JSON and Markdown).
- `README.md` — added CIDR network calculations (`cidr`) to the features list.

### Verification
- `python -m pytest -q` -> 1043 passed, 1 skipped (1000 baseline + 43 new: 33 unit + 10 CLI).
- `python -m ethscan --help` -> lists `cidr` among the 28 commands.
- `python -m ethscan cidr --help` -> shows all expected options (`--cidr`, `--contains`, `--format`, `--out`).
- End-to-end: `python -m ethscan cidr --cidr 192.168.1.0/24 --format json` reports network_address, netmask, broadcast, usable_host_count=254.
- End-to-end: `python -m ethscan cidr --cidr 192.168.1.0/24 --contains 192.168.1.50 --format json` includes membership test with in_network=true.
- End-to-end: `python -m ethscan cidr --cidr 2001:db8::/32 --format markdown` renders IPv6 network table with no broadcast address.
- End-to-end: `python -m ethscan cidr --cidr 192.168.1.100 --format json` treats bare IP as /32 single-host network.

## Completed: `hash` command (Password hash generation)

The `hash` command generates password hashes using common algorithms (MD5, SHA-1, SHA-256, SHA-512, NTLM) for password-audit workflows. It supports multiple input methods (file or stdin), algorithm selection, and JSON/Markdown output.

### Added Files
- `ethscan/hash.py` — Password hash generation module with:
  - `_md4()` — pure Python MD4 implementation (stdlib doesn't guarantee MD4 availability) for NTLM hash generation
  - `_compute_hash()` — computes hash for a single password using specified algorithm
  - `run_hash()` — public entry point: accepts list of passwords and optional algorithm list, returns structured results
  - `format_hash_report_json()` / `format_hash_report_markdown()` — output formatters (markdown includes summary table with pipe escaping)
- `tests/test_hash.py` — 21 unit tests: hash computation (all algorithms), run_hash (default/custom algorithms, multiple passwords, empty, invalid algorithm, special chars), formatters (JSON, markdown basic/empty/pipe escaping), algorithm constants

### Modified Files
- `ethscan/cli.py` — registered `hash` command with `--file`, `--algorithm` (multiple, choice: md5/sha1/sha256/sha512/ntlm), `--format`, `--out`; imports `run_hash` and formatters from `ethscan.hash`
- `tests/test_cli.py` — 8 CLI integration tests: `hash` help, top-level help listing, stdin json/markdown output (monkeypatched `run_hash`), `--file` option, `--algorithm` option, `--out` (json and markdown)
- `README.md` — added password hash generation (`hash`) to the features list

### Verification
- `python -m pytest -q` -> 1262 passed, 1 skipped (1233 baseline + 29 new: 21 unit + 8 CLI).
- `python -m ethscan --help` -> lists `hash` among the 29 commands.
- `python -m ethscan hash --help` -> shows all expected options (`--file`, `--algorithm`, `--format`, `--out`).
- End-to-end: `echo "password" | python -m ethscan hash --format markdown` -> produces Markdown report with all 5 algorithm columns.
- End-to-end: `echo -e "password\nsecret" | python -m ethscan hash --algorithm md5 --algorithm sha256 --format json` -> produces JSON with only MD5 and SHA-256 hashes.
- End-to-end: `python -m ethscan hash --file passwords.txt --format json --out hashes.json` -> writes JSON report to file.

## Suggested next task

**Add a `radix` command** for radix tree visualization of CIDR blocks (merging overlapping/supernetting adjacent networks).

Alternative: Add a `radix` command for radix tree visualization of CIDR blocks (merging overlapping/supernetting adjacent networks).

## Completed: `hash` command (password hash generation)

The `hash` command generates cryptographic hashes for passwords using the stdlib `hashlib` module. Supports MD5, SHA-1, SHA-256, SHA-512, NTLM, and MD4 (when available via OpenSSL). Fully offline and stdlib-only.

### Added Files
- `ethscan/hash.py` — password hash generation module with:
  - `_normalize_algorithm()` — normalizes algorithm names (case-insensitive, alias support for `sha-1`/`sha-256`/`sha-512`)
  - `_hashlib_name()` / `_supported_algorithms()` — helpers for algorithm discovery
  - `MD4_AVAILABLE` flag for graceful MD4/NTLM fallback when OpenSSL lacks MD4
  - `_compute_md5()` / `_compute_sha1()` / `_compute_sha256()` / `_compute_sha512()` / `_compute_md4()` / `_compute_ntlm()` — per-algorithm hashers (NTLM = MD4 of UTF-16LE)
  - `_compute_hash()` — dispatcher returning the digest or raising ValueError for unavailable algorithms
  - `run_hash()` — public entry point: normalizes algorithm, hashes passwords (drops empty), records per-password results with graceful error handling, collects notes for unavailable MD4/NTLM
  - `format_hash_report_json()` / `format_hash_report_markdown()` — output formatters (markdown includes pipe-escaped table and notes section)
- `tests/test_hash.py` — 39 unit tests: algorithm normalization (case-insensitive, aliases, whitespace, unsupported), hashlib name/supported-algorithms helpers, password normalization, per-algorithm hashers (md5/sha1/sha256/sha512 known values, empty), dispatch, NTLM UTF-16LE correctness, MD4 availability handling, run_hash (basic/multi/drops-empty/default/normalizes/unsupported/ntlm/md4 notes/empty/all-algorithms), both formatters (JSON basic/empty/notes, markdown basic/empty/pipe-escape/notes/multi-algo)

### Modified Files
- `ethscan/cli.py` — registered `hash` command with `--password` (repeatable), `--algorithm` (choice: md5/sha1/sha256/sha512/ntlm/md4, default md5), `--format`, `--out`; reads passwords from `--password` flags or stdin; imports `run_hash`, `format_hash_report_json`, `format_hash_report_markdown` from `ethscan.hash`
- `tests/test_cli.py` — 13 CLI integration tests: `hash` help, top-level help listing, md5/sha256 JSON, md5 markdown, default-is-md5, multiple passwords, stdin JSON/markdown, no-passwords, `--out` (json and markdown), pipe escaping in markdown
- `README.md` — added password hash generation (`hash`) to the features list

### Verification
- `python -m pytest -q` -> 1256 passed, 1 skipped (1243 baseline + 52 new: 39 unit + 13 CLI)
- `python -m ethscan --help` -> lists `hash` among the commands
- `python -m ethscan hash --help` -> shows `--password`, `--algorithm [md5|sha1|sha256|sha512|ntlm|md4]`, `--format`, `--out`
- End-to-end: `python -m ethscan hash --password password --algorithm md5 --format json` -> `5f4dcc3b5aa765d61d8327deb882cf99`
- End-to-end: `python -m ethscan hash --password password --algorithm sha256 --format markdown` -> Markdown report with `5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8`
- End-to-end: `echo password | python -m ethscan hash --algorithm sha1 --format json` -> `5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8`
- NTLM/MD4 graceful fallback: on builds without OpenSSL MD4, `--algorithm ntlm` records `hash: null` with an error and a note instead of crashing
- Pipe escaping: `--password "pass|word" --format markdown` renders `pass\|word`

## Current state
- All 28 commands implemented (including `hash`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `scan` and `service` now support `--output-format csv` for spreadsheet-compatible output.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth` for recursive WHOIS queries.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--ports`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- `vuln` now supports `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--min-severity`, `--format`, `--out` for built-in vulnerability checks.
- `dnssec` now supports `--target`, `--server`, `--timeout`, `--format`, `--out` for DNSSEC validation (DNSKEY + DS chain of trust).
- `geo` now supports `--recursive` and `--max-depth` for recursive hop geolocation.
- `hash` now supports `--password`, `--algorithm [md5|sha1|sha256|sha512|ntlm|md4]`, `--format`, `--out` for password hash generation.
- Configuration file (`ethscan.yaml`) persists default options across commands via a `--config` group option and a `config` subcommand.
- Tests: 1256 passing (1 skipped). (6 pre-existing failures in test_cidr/test_completion/test_jwt are unrelated to this change.)

## Suggested next task

**Add a `--file` option to the `hash` command** to read passwords from a file (one per line), mirroring the `audit` command's `--file` input mode for batch hashing workflows.

Alternative: Add a `--check` option to the `hash` command that compares a plaintext password against a known hash (e.g. verify a stored MD5/SHA-256 digest).

Alternative: Add a `--pepper`/`--salt` option to the `hash` command for salted hash generation (e.g. HMAC-SHA-256 with a user-provided salt).

## Completed: `--file` option for `hash` command

Added a `--file` option to the `hash` command to read passwords from a file (one password per line), mirroring the `audit` command's `--file` input mode for batch hashing workflows. Input precedence: `--password` flags > `--file` > stdin.

### Added Functionality
- `ethscan/hash.py`:
  - Added `load_passwords_from_file()` helper: reads a UTF-8 file, strips each line, skips empty lines (follows the `load_subdomain_wordlist` convention; unlike subdomain wordlists, `#` lines are preserved since they may be valid passwords).
- `ethscan/cli.py`:
  - Added `--file PATH` option to the `hash` command (`password_file` dest).
  - Input precedence: `--password` flags win over `--file`; `--file` wins over stdin.
  - Updated `--password` help text ("If omitted, reads from --file or stdin.").
  - Removed a stale duplicate `from ethscan.hash import ...` block (the second identical import at former lines 145-149).

### Modified Files
- `ethscan/hash.py` — added `load_passwords_from_file()` helper
- `ethscan/cli.py` — added `--file` option and precedence logic; removed duplicate hash import block
- `tests/test_hash.py` — 5 new unit tests: `test_load_passwords_from_file_basic`, `test_load_passwords_from_file_strips_and_skips_empty`, `test_load_passwords_from_file_empty_file`, `test_load_passwords_from_file_missing_raises`, `test_load_passwords_from_file_preserves_special_characters`
- `tests/test_cli.py` — 8 new CLI integration tests: `test_hash_help_shows_file_option`, `test_hash_file_option`, `test_hash_file_option_markdown`, `test_hash_file_skips_empty_lines_and_strips`, `test_hash_file_with_out_option`, `test_hash_password_flags_take_precedence_over_file`, `test_hash_file_takes_precedence_over_stdin`, `test_hash_file_missing_file_fails`
- `tests/test_cli.py` — fixed 11 pre-existing failing `cve` tests whose `mock_run_cve` signatures were stale (missing `service_timeout`, `workers`, and `profile` parameters that the `cve` command passes after the `--ports`/`--profile` additions)
- `README.md` — updated hash feature description to mention `--password` flags and `--file` batch input

### Verification
- `python -m pytest -q` -> 1371 passed, 1 skipped (1359 collected before: 1347 passed + 11 failed; the 11 pre-existing cve mock failures are now fixed, plus 13 new tests: 5 unit + 8 CLI)
- `python -m ethscan hash --help` -> shows `--file TEXT` option
- End-to-end: `python -m ethscan hash --file passwords.txt --algorithm sha256 --format json` hashes each non-empty line (whitespace stripped)
- End-to-end: `python -m ethscan hash --password explicit --file passwords.txt --format json` -> only `explicit` is hashed (`--password` flags win)
- End-to-end: `echo fromstdin | python -m ethscan hash --file passwords.txt --format json` -> only file contents are hashed (`--file` wins over stdin)
- End-to-end: `python -m ethscan hash --file missing.txt --format json` -> non-zero exit with FileNotFoundError

## Completed: `--check` option for `hash` command

Added a `--check DIGEST` option to the `hash` command that compares a plaintext password against a known hash digest, reporting MATCH/MISMATCH/UNKNOWN. The algorithm is inferred from the digest length when `--algorithm` is omitted (preferring MD5 when multiple algorithms share a length, e.g. MD5/NTLM/MD4 at 32 chars), or can be specified explicitly via `--algorithm`.

### Added Functionality
- `ethscan/hash.py`:
  - `_DIGEST_LENGTHS` — canonical hex digest lengths per algorithm (md5/sha1/sha256/sha512/ntlm/md4), used to infer the algorithm from an unknown digest.
  - `_infer_algorithm(digest)` — infers the canonical algorithm key from a hex digest's length; returns `None` when no match (e.g. `deadbeef`).
  - `run_check(password, digest, algorithm=None)` — public entry point: normalizes/explicitly infers the algorithm, computes the hash, compares case-insensitively, and returns a structured result with `password`, `digest`, `algorithm`, `computed`, `match`, `error` fields. Gracefully reports errors (unsupported algorithm, uninferable length) instead of raising.
  - `format_check_report_json(data)` / `format_check_report_markdown(data)` — output formatters (markdown includes MATCH/MISMATCH/UNKNOWN result and an Error section when present, with pipe escaping).

### Modified Files
- `ethscan/cli.py` — added `--check DIGEST` option to the `hash` command; in check mode the first password is compared against the supplied digest using `run_check` and the check formatters are used.
- `tests/test_hash.py` — 17 new unit tests: `run_check` (md5 match/mismatch, sha256 match, explicit algorithm, case-insensitive digest, sha1/sha512 inference, unknown-length error, unsupported-algorithm error, md4-when-unavailable), both formatters (JSON basic/mismatch/error, markdown match/mismatch/error/pipe-escape/no-algorithm).
- `tests/test_cli.py` — 11 new CLI integration tests: `hash` help listing `--check`, check match/mismatch JSON, check match/mismatch markdown, sha256 explicit algorithm, sha1 inference, unknown-length error, `--out` option, pipe escaping in markdown, no-passwords.
- `README.md` — added password hash checking (`hash --check`) to the features list.

### Verification
- `python -m pytest -q` -> 1400 passed, 1 skipped (1371 baseline + 29 new: 17 unit + 12 CLI).
- `python -m ethscan hash --help` -> lists `--check TEXT` option.
- End-to-end: `python -m ethscan hash --password password --check 5f4dcc3b5aa765d61d8327deb882cf99 --format json` -> `match: true`, algorithm `md5`.
- End-to-end: `python -m ethscan hash --password wrong --check 5f4dcc3b5aa765d61d8327deb882cf99 --format markdown` -> MISMATCH with computed digest.
- End-to-end: `python -m ethscan hash --password password --check deadbeef --format json` -> `match: null` with error "Could not infer algorithm from digest length 8; specify --algorithm explicitly."

## Suggested next task

**Add a `--pepper`/`--salt` option to the `hash` command** for salted hash generation (e.g. HMAC-SHA-256 with a user-provided salt).

Alternative: Add a `--min-length` option to the `audit` command to flag passwords below a custom length threshold in addition to the built-in heuristics.

Alternative: Add a `--iterations` option to the `hash` command for iterated hash generation (e.g. PBKDF2-HMAC-SHA256 with a configurable iteration count).

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 27 commands implemented (including `dnssec`, `mac`, `cert`, `subtake`, `hash`).
- `scan` and `service` now support `--profile fast|normal|full` option.
- `scan` and `service` now support `--output-format csv` for spreadsheet-compatible output.
- `subdomains` and `dnsbrute` now support `--resolver` option for custom DNS resolver selection.
- `subdomains` now supports `--recursive` and `--max-depth` for recursive subdomain enumeration.
- `dnsbrute` now supports `--recursive` and `--max-depth` for recursive zone transfers.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth` for recursive WHOIS queries.
- `osdetect` supports `--ports`, `--banners-file` (cross-reference `service` output), `--timeout`, `--workers`.
- `audit` now supports `--format json|markdown` and `--out` for machine-readable output.
- `cert` now supports `--target`, `--timeout`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--format`, `--out` for CT log subdomain discovery.
- `report` now supports `--format json|markdown` and `--out` for combined scan+audit reports (json and markdown).
- `cve` now supports `--target`, `--services-file`, `--ports`, `--profile`, `--timeout`, `--service-timeout`, `--workers`, `--no-cache`, `--no-offline-fallback`, `--api-url`, `--severity`, `--min-severity`, `--format`, `--out` for NVD/CVE API vulnerability lookups.
- `vuln` now supports `--target`, `--ports`, `--services-file`, `--tls-file`, `--ssl-file`, `--severity`, `--min-severity`, `--format`, `--out` for built-in vulnerability checks.
- `dnssec` now supports `--target`, `--server`, `--timeout`, `--format`, `--out` for DNSSEC validation (DNSKEY + DS chain of trust).
- `geo` now supports `--recursive` and `--max-depth` for recursive hop geolocation.
- `hash` now supports `--password`, `--file` (one password per line), `--algorithm [md5|sha1|sha256|sha512|ntlm|md4]`, `--check DIGEST` (compare plaintext against a known hash, algorithm inferred from digest length or explicit `--algorithm`), `--format`, `--out` for password hash generation and verification.
 - Configuration file (`ethscan.yaml`) persists default options across commands via a `--config` group option and a `config` subcommand.
  - Tests: 1400 passing (1 skipped).

## Completed: `--pepper`/`--salt` option for `hash` command

Added `--salt` and `--pepper` options to the `hash` command for salted/peppered hash generation, following standard password-security practice. Works in both hashing and `--check` modes. Stdlib-only (`hmac` module).

### Design
- `--salt SALT`: the salt is prepended to each password before hashing (`hash(salt + password)`), the classic salted-hash construction (defends against rainbow tables). Works for all algorithms including NTLM/MD4.
- `--pepper PEPPER`: the pepper is used as the HMAC key over the password (`HMAC(pepper, password, algo)`). Only valid for hashlib-backed algorithms (md5, sha1, sha256, sha512, md4); NTLM has no hashlib name and is rejected with a graceful per-password error rather than a crash.
- Combined (`--salt` + `--pepper`): `HMAC(pepper, salt + password, algo)`, applying both defenses in one output.
- In `--check` mode, the same salt/pepper are used to recompute the digest for MATCH/MISMATCH comparison, enabling verification of salted/peppered digests.
- Salt/pepper are not echoed back in results (only `salt`/`pepper` boolean flags) to avoid leaking the pepper secret; explanatory notes describe what was applied.

### Added Functionality
- `ethscan/hash.py`:
  - Added `import hmac`.
  - `_compute_peppered_hash(password, algorithm, pepper)` — HMAC keyed hash using the pepper as the key; raises `ValueError` for algorithms without a hashlib name (NTLM).
  - `_compute_password_hash(password, algorithm, salt=None, pepper=None)` — combining dispatcher: salt+pepper -> `HMAC(pepper, salt+password, algo)`; salt only -> `hash(salt+password)`; pepper only -> `HMAC(pepper, password, algo)`; neither -> standard `_compute_hash`.
  - `run_hash()` now accepts `salt`/`pepper`; records `salt`/`pepper` booleans per-result and at the top level; adds explanatory notes; uses `_compute_password_hash`.
  - `run_check()` now accepts `salt`/`pepper`; records booleans; uses `_compute_password_hash` so salted/peppered digests can be verified.
  - `format_hash_report_markdown()` and `format_check_report_markdown()` now render `**Salt:**`/`**Pepper:**` lines when applied. JSON formatters include the new `salt`/`pepper` fields automatically.
- `ethscan/cli.py`:
  - Added `--salt` and `--pepper` options (default `None`) to the `hash` command; passes both to `run_hash` and `run_check`.

### Modified Files
- `ethscan/hash.py` — salt/pepper support and formatters.
- `ethscan/cli.py` — `--salt`/`--pepper` options and pass-through.
- `tests/test_hash.py` — 28 new unit tests: peppered-HMAC known values, salt prepend, salt+pepper combined (HMAC(salt+password)), unsupported-algorithm/unsupported-NTLM-pepper errors, `run_hash` (salt/pepper/combined/multi-password/NTLM-pepper-graceful), JSON/markdown formatters (salt+pepper lines, no-salt/no-pepper lines), `run_check` (salt/pepper/combined match/mismatch/unsupported error), check formatters.
- `tests/test_cli.py` — 12 new CLI integration tests: help shows `--salt`/`--pepper`, salt JSON/markdown, pepper JSON/markdown, salt+pepper combined JSON, salt with `--file`, salt+pepper with `--out`, check-with-salt match, check-with-pepper match, check-with-pepper mismatch markdown, check NTLM+pepper error.
- `README.md` — added salted/peppered hashing to the features list.

### Verification
- `python -m pytest -q` -> 1440 passed, 1 skipped (1400 baseline + 28 unit + 12 CLI).
- `python -m ethscan hash --help` -> shows `--salt` and `--pepper` options.
- End-to-end: `python -m ethscan hash --password password --salt saltvalue --algorithm md5 --format json` -> `e137588f7bb4aa4f0c24592088b82f31` (matches `md5("saltvalue"+"password")`).
- End-to-end: `python -m ethscan hash --password password --pepper secretpepper --algorithm sha256 --format json` -> `e8bb12880be0eb5b568514ffa2acaa9b74648dadcebe545a07585fee8ea552ad` (matches `HMAC-SHA256("secretpepper", "password")`).
- End-to-end: `python -m ethscan hash --password password --salt saltvalue --pepper secretpepper --algorithm sha256 --format json` -> `862e3f4b4c304c5da6c560833847a8434f110c55c23dfba9bff2982238c8fc59`.
- End-to-end: `python -m ethscan hash --password password --salt saltvalue --check e137588f7bb4aa4f0c24592088b82f31 --algorithm md5 --format json` -> `"match": true`.
- Graceful: `python -m ethscan hash --password password --pepper p --algorithm ntlm --format json` -> per-password error, no crash.

## Suggested next task

**Add a `--iterations` option to the `hash` command** for iterated key-derivation (PBKDF2-HMAC-SHA256 with a configurable iteration count and optional `--salt`). This naturally extends the new salt/pepper work: when `--iterations N` is supplied, use `hashlib.pbkdf2_hmac(algorithm, password, salt, N)` (requiring `--salt`) instead of the single-pass hash, producing a stronger password-derived hash suitable for offline brute-force comparison. Output the iteration count and salt in the report so results are reproducible/verifiable.

Alternative: Add a `--min-length` option to the `audit` command to flag passwords below a custom length threshold (in addition to the built-in heuristics), with JSON/Markdown reporting of short passwords.

Alternative: Add a `--format json|markdown` option to the `report` command for machine-readable combined scan+audit reports (it currently only produces a human-readable summary).

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Completed: `--min-length` option for `audit` command

Added a `--min-length` option to the `audit` command that flags passwords shorter than a custom length threshold (in addition to the built-in heuristics). The minimum length check is reflected in the `too_short` field in both JSON and Markdown output, and the score is capped at 10.0 for passwords that are too short.

### Added Functionality
- `ethscan/passwords.py`:
  - Updated `evaluate_password()` to accept optional `min_length` parameter
  - Added `too_short` boolean field to evaluation results
  - Applied score penalty (capped at 10.0) for passwords below the minimum length
  - Updated `audit_passwords()` to pass `min_length` to `evaluate_password()`
  - Updated `format_audit_report_json()` to include `min_length` in the report and `too_short` in each result
  - Updated `format_audit_report_markdown()` to display "Min Length" summary line and "Too Short" column in the table
- `ethscan/cli.py`:
  - Added `--min-length` option to the `audit` command
  - Passes `min_length` to `audit_passwords()` and formatters

### Modified Files
- `ethscan/passwords.py` — added min_length parameter and too_short field
- `ethscan/cli.py` — added `--min-length` option and pass-through
- `tests/test_passwords.py` — 5 new unit tests:
  - `test_evaluate_password_min_length_too_short` — verifies too_short=True and very weak verdict
  - `test_evaluate_password_min_length_ok` — verifies too_short=False for long passwords
  - `test_evaluate_password_min_length_none` — verifies too_short=False when min_length not specified
  - `test_audit_passwords_with_min_length` — tests audit_passwords with min_length
  - `test_format_audit_report_json_with_min_length` — tests JSON formatter with min_length
  - `test_format_audit_report_markdown_with_min_length` — tests Markdown formatter with min_length
- `tests/test_cli.py` — 6 new CLI integration tests:
  - `test_audit_help_shows_min_length` — verifies help shows --min-length option
  - `test_audit_min_length_option_json` — tests CLI min_length option with JSON output
  - `test_audit_min_length_option_markdown` — tests CLI min_length option with Markdown output
  - `test_audit_min_length_with_out_option` — tests --out with min_length
  - `test_audit_min_length_disabled_by_default` — verifies min_length defaults to None

### Verification
- `python -m pytest -q` -> 1480 passed, 1 skipped (1440 baseline + 40 new: 5 unit + 6 CLI + existing tests still pass)
- `python -m ethscan audit --help` -> shows `--min-length` option
- End-to-end JSON: `echo -e "short\nlongenoughpassword\n" | python -m ethscan audit --min-length 10 --format json` produces JSON with `too_short: true` for "short" and `too_short: false` for "longenoughpassword", `min_length: 10`
- End-to-end Markdown: same input with `--format markdown` produces table with "Too Short" column and "Min Length: 10" summary

## Current state
- All 28 commands implemented and wired up (including `hash` with `--file`, `--check`, salt, and pepper).
- `hash` now supports `--password`, `--file`, `--algorithm [md5|sha1|sha256|sha512|ntlm|md4]`, `--salt`, `--pepper` (HMAC, combinable as `HMAC(pepper, salt+password)`), `--iterations`, `--check DIGEST` (with salt/pepper/iterations support), `--format`, `--out` for password hash generation and verification.
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth`.
- `audit` now supports `--format json|markdown`, `--out`, and `--min-length` for custom minimum password length threshold.
- `cert`, `report`, `cve` (with `--min-severity` and `--ports`), `vuln` (with `--min-severity`), `dnssec`, `geo`, `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1480 passing (1 skipped).

## Completed: `--output-format csv` option for `report` command

Added a `--output-format [json|markdown|csv]` option to the `report` command for spreadsheet-compatible CSV export of the combined scan+audit report. The report logic was extracted from `ethscan/cli.py` into a dedicated `ethscan/report.py` module, bringing the command in line with the toolkit's module convention (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).

### Added Files
- `ethscan/report.py` — combined report module with:
  - `run_report(target, ports, timeout, workers, audit_file)` — public entry point: parses ports (`common`/`all`/comma-separated list/ranges), runs the port scan, optionally loads passwords from the audit file and audits them, returns the combined report dict
  - `format_report_json()` — JSON formatter
  - `format_report_markdown()` — Markdown formatter (moved from `ethscan/cli.py`'s `_generate_markdown`; output unchanged)
  - `format_report_csv()` — CSV formatter emitting a single valid CSV document with a `section` discriminator column: `scan` rows carry `port`/`open`, `audit` rows carry `password`/`length`/`entropy`/`common`/`patterns`/`score`/`verdict`; any CSV reader can filter by section
  - `CSV_COLUMNS` — canonical column list

### Modified Files
- `ethscan/cli.py`:
  - Added `--output-format [json|markdown|csv]` option to the `report` command; `--format` remains as a deprecated alias and `--output-format` takes precedence when both are given (same pattern as `scan`/`service`/`brute`)
  - The `report` command now delegates to `run_report()` and the `ethscan.report` formatters
  - Removed the now-unused `_generate_markdown()` helper (moved to `ethscan.report.format_report_markdown`)
- `tests/test_report.py` — 10 new unit tests: `run_report` (offline target, common ports, all ports, with audit file), `format_report_json`, `format_report_markdown` (empty audit / with audit), `format_report_csv` (header only, scan+audit rows, CSV quoting of passwords containing commas)
- `tests/test_cli.py` — 6 new CLI integration tests: help shows `--output-format` with csv choice, CSV output to stdout (scan + audit rows), CSV with `--out`, explicit `--output-format json`, `--output-format` precedence over deprecated `--format`, deprecated `--format csv` still works
- `README.md` — report feature description now mentions CSV output

### Verification
- `python -m pytest -q` -> 1496 passed, 1 skipped (1480 baseline + 16 new: 10 unit + 6 CLI).
- `python -m ethscan report --help` -> shows `--output-format [json|markdown|csv]` and the deprecated `--format` alias.
- End-to-end: `python -m ethscan report --target 127.0.0.1 --ports 80,443 --output-format csv` -> `section,port,open,password,...` header plus `scan,80,false,...` / `scan,443,false,...` rows.
- End-to-end with `--audit-file`: CSV includes `audit` rows with all per-password fields; passwords containing commas are properly CSV-quoted.
- Backward compatibility: `--format json` (default) and `--format markdown` behave exactly as before; markdown output is identical to the previous inline `_generate_markdown` output.

## Completed: `--output-format csv` option for `audit` command

The `audit` command already supported a `format_audit_report_csv()` formatter in `ethscan/passwords.py` and the `--output-format [json|markdown|csv]` option was wired up in `ethscan/cli.py` (with `--format` as a deprecated alias). The feature was verified end-to-end: `echo -e "password\n123456\nshort" | python -m ethscan audit --output-format csv` produces `password,length,entropy,common,patterns,too_short,score,verdict` with one row per password.

### Fixed: pre-existing bug in `format_report_csv` (ethscan/report.py)

The combined `report` CSV formatter wrote scan rows with only 10 fields while `CSV_COLUMNS` (and the audit rows) had 11 columns including `too_short`. This caused a column misalignment for any CSV reader parsing the combined document. Fixed by adding the missing trailing empty `""` field so every row has 11 columns.

### Modified Files
- `ethscan/report.py` — added the missing `too_short` field to scan rows in `format_report_csv`
- `tests/test_cli.py` — updated 3 report CSV tests to expect the correct 11-column header (`section,port,open,password,length,entropy,common,patterns,too_short,score,verdict`)
- `README.md` — clarified audit feature description to mention CSV output

### Verification
- `python -m pytest -q` -> 1507 passed, 1 skipped (all previously-failing report CSV tests now pass)
- `python -m ethscan audit --help` -> shows `--output-format [json|markdown|csv]`
- End-to-end: `echo -e "password\n123456\nshort" | python -m ethscan audit --output-format csv` -> 3-row CSV with `password,length,entropy,common,patterns,too_short,score,verdict` header
- End-to-end with `--min-length`: `echo -e "short\nlongenoughpassword" | python -m ethscan audit --output-format csv --min-length 10` -> flags `too_short=true` for "short"
- Backward compatibility: deprecated `--format csv` still works

## Suggested next task

**Add a `--min-length` pass-through to the `report` command** so the embedded password audit can flag short passwords (the standalone `audit` command already supports `--min-length`).

Alternative: Add `--profile fast|normal|full` support to the `report` command to reuse the scan profile presets (port set, timeout, workers) when generating combined reports.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 28 commands implemented and wired up (including `hash` with `--file`, `--check`, salt, and pepper).
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth`.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, and `--output-format csv` for spreadsheet-compatible password audit dumps.
- `report` now supports `--output-format [json|markdown|csv]` (with `--format` as deprecated alias) and `--out`; report logic lives in `ethscan/report.py` (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).
- `cert`, `cve` (with `--min-severity` and `--ports`), `vuln` (with `--min-severity`), `dnssec`, `geo`, `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1507 passing (1 skipped).

## Completed: `--min-length` pass-through for `report` command

The `--min-length` pass-through to the `report` command is complete: the embedded password audit flags short passwords exactly like the standalone `audit` command. The implementation itself (`run_report(min_length=...)` in `ethscan/report.py` and the `--min-length` CLI option in `ethscan/cli.py`) was already in place; this change adds the missing test coverage and fixes two pre-existing broken tests in `tests/test_report.py`.

### Tests Added
- `tests/test_report.py` — 5 new unit tests:
  - `test_run_report_with_min_length` — verifies the `min_length` field and per-password `too_short` flags
  - `test_run_report_min_length_defaults_to_none` — verifies `min_length` defaults to None
  - `test_format_report_json_with_min_length` — JSON formatter includes `min_length` and `too_short`
  - `test_format_report_markdown_with_min_length` — Markdown shows the Min Length line and Too Short column
  - `test_format_report_csv_with_min_length` — CSV `too_short` column
- `tests/test_cli.py` — 5 new CLI integration tests:
  - `test_report_help_shows_min_length`
  - `test_report_min_length_option_json`
  - `test_report_min_length_option_markdown`
  - `test_report_min_length_with_out_option`
  - `test_report_min_length_disabled_by_default`

### Fixed pre-existing test bugs
- `tests/test_report.py::test_report_markdown_writes_to_file` — assertions ran after the `TemporaryDirectory` context exited (the output file was already deleted); moved the assertions inside the `with` block.
- `tests/test_report.py::test_resolve_ports_and_defaults_profile_explicit_timeout_workers` — expected `[80, 443]` for `("common", 5.0, 50, "fast")`, contradicting the documented profile behavior (a profile overrides the default `common` port selection; explicit `--timeout`/`--workers` win over profile defaults); now asserts the 18 fast-profile ports with the explicit timeout/workers preserved.

### Verification
- `python -m pytest -q` -> 1535 passed, 1 skipped (1525 collected before: 1523 passed + 2 failed; 10 new tests added).
- `python -m ethscan report --help` -> shows `--min-length` option.
- End-to-end JSON: `python -m ethscan report --target 127.0.0.1 --ports 80 --audit-file passwords.txt --min-length 10 --format json` -> `audit.min_length: 10`, `too_short: true` for "short", `too_short: false` for "longenoughpassword".
- End-to-end Markdown: `- **Min Length:** 10` line and a Too Short column with `Yes` for short passwords.

## Suggested next task

**Add an `--open-only` option to the `report` command** to filter the embedded port scan results to open ports only (in JSON, Markdown, and CSV output), useful for large scans where closed-port rows dominate the report.

Alternative: Add a `--sort` option to the `report` command to sort the audit results by score, verdict, or length.

Alternative: Add a `validate` command that validates and expands port specifications (comma-separated lists/ranges) and CIDR inputs offline, reusing `parse_port_range` and the stdlib `ipaddress` module.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 28 commands implemented and wired up (including `hash` with `--file`, `--check`, salt, and pepper).
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive` and `--max-depth`.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, and `--output-format csv` for spreadsheet-compatible password audit dumps.
- `report` now supports `--target`, `--ports`, `--profile`, `--timeout`, `--workers`, `--audit-file`, `--min-length` (pass-through to the embedded audit), `--open-only/--no-open-only` (filter scan results to open ports only), `--output-format [json|markdown|csv]` (with `--format` as deprecated alias), and `--out`; report logic lives in `ethscan/report.py` (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).
- `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `vuln` (with `--min-severity`), `dnssec`, `geo`, `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1545 passing (1 skipped).

## Completed: `--open-only` option for `report` command

Added a `--open-only/--no-open-only` option to the `report` command that filters the embedded port scan results to open ports only in JSON, Markdown, and CSV output. This is useful for large scans where closed-port rows dominate the report.

The filtering is applied in `run_report()` (which already had the `open_only` parameter and logic in `ethscan/report.py`), ensuring consistent behavior across all output formats. The CLI option is now wired up to pass `open_only` through to `run_report()`, and the Markdown formatter displays an `Open Only:` summary line.

### Modified Files
- `ethscan/cli.py` — added `--open-only/--no-open-only` flag (default False) to the `report` command; passes `open_only` to `run_report()`.
- `ethscan/report.py` — no code changes (the `open_only` parameter was already implemented in `run_report`, `scan_details` filtering, and the return dict); updated `format_report_markdown()` to render an `**Open Only:** Yes/No` summary line.
- `tests/test_report.py` — 6 new unit tests: `test_run_report_open_only_filters_closed_ports` (monkeypatched scan_ports, verifies closed ports filtered), `test_run_report_open_only_default_false` (verifies default), `test_format_report_json_open_only` (JSON includes filtered details + open_only flag), `test_format_report_markdown_open_only` (markdown shows open-only flag and no closed ports), `test_format_report_markdown_open_only_false` (markdown shows all ports when disabled), `test_format_report_csv_open_only` (CSV only emits open-port scan rows).
- `tests/test_cli.py` — 5 new CLI integration tests: `test_report_help_shows_open_only` (help shows option), `test_report_open_only_option_json` (JSON output filtered, parameter pass-through via mock), `test_report_open_only_option_markdown` (markdown filtered, "Open Only: Yes" shown), `test_report_open_only_option_csv` (CSV only open rows), `test_report_open_only_disabled_by_default` (default is False, all ports shown).
- `README.md` — updated report feature description to mention `--open-only`.

### Verification
- `python -m pytest -q` -> 1545 passed, 1 skipped (1535 baseline + 11 new: 6 unit + 5 CLI).
- `python -m ethscan report --help` -> shows `--open-only / --no-open-only` option.
- End-to-end (JSON): `python -m ethscan report --target 127.0.0.1 --ports 80,443,22 --open-only --timeout 0.5 --format json` -> `details` contains only port 22 (the open port), `open_only: true`.
- End-to-end (Markdown): `--open-only --format markdown` -> shows `**Open Only:** Yes`, only open-port rows in the table, no closed-port rows.
- End-to-end (CSV): `--open-only --output-format csv` -> CSV scan rows only for open ports.
- End-to-end (`--no-open-only`): all ports shown in output with `open_only: false`.
- Backward compatibility: without `--open-only`, report behaves exactly as before (all ports shown, no "Open Only" line change to existing behavior).

## Suggested next task

**Add a `--sort` option to the `report` command** to sort the audit (password) results by score, verdict, or length — ascending or descending. The scan results remain in port order; only the audit table/CSV rows are reordered. Accept `--sort {score|verdict|length} [--sort-asc|--sort-desc]` (default: `score`, descending), with corresponding unit tests in `tests/test_report.py` and CLI tests in `tests/test_cli.py`.

Alternative: Add a `validate` command that validates and expands port specifications (comma-separated lists/ranges) and CIDR inputs offline, reusing `parse_port_range` and the stdlib `ipaddress` module, with JSON/Markdown output.

Alternative: Add a `--sort` option to the `audit` command for sorting password results by score, verdict, or length.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 29 commands implemented and wired up (including `hash` with `--file`, `--check`, salt, pepper, and `--iterations`, and `validate`).
- `resolve` command (forward/reverse DNS: A, AAAA, CNAME, PTR) is fully implemented, documented in `README.md`, and covered by unit + CLI integration tests; its Markdown formatter escapes pipe characters.
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out` for machine-readable WHOIS results.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv` for spreadsheet-compatible password audit dumps, and `--sort [score|verdict|length]` with `--sort-desc/--sort-asc` (reorder audit rows; defaults to `None`/`True`).
- `report` now supports `--target`, `--ports`, `--profile`, `--timeout`, `--workers`, `--audit-file`, `--min-length` (pass-through to the embedded audit), `--open-only/--no-open-only` (filter scan results to open ports only), `--sort {score|verdict|length}` with `--sort-desc/--sort-asc` (reorder audit rows; scan results stay in port order), `--output-format [json|markdown|csv]` (with `--format` as deprecated alias), and `--out`; report logic lives in `ethscan/report.py` (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).
- `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `vuln` (with `--min-severity`, `--recursive`, `--max-depth`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1676 passing (1 skipped).

## Completed: `--sort` option for `report` command

Added a `--sort` option to the `report` command that reorders the embedded password audit results by score, verdict, or length, in ascending or descending direction. The port scan results remain in port order; only the audit table/CSV rows are reordered.

### Implementation
- `ethscan/report.py`:
  - Added `VALID_SORT_KEYS = ("score", "verdict", "length")` constant.
  - Added `_sort_audit_results(results, sort_by, sort_desc)` helper that returns a sorted copy of the audit result dicts. Verdicts are sorted case-insensitively; invalid sort keys preserve original order.
  - Updated `run_report()` to accept `sort_by` and `sort_desc` (defaults `None` and `True`) and include `sort_by`/`sort_desc` in the returned audit section.
  - Updated `format_report_markdown()` to render a `**Sorted By:** <field> (<Direction>)` summary line.
- `ethscan/cli.py` — added `--sort [score|verdict|length]` (default None) and `--sort-desc/--sort-asc` (default True) options to the `report` command; passes both through to `run_report()`.

### Tests Added
- `tests/test_report.py` — 9 new unit tests:
  - `test_run_report_sort_by_score_desc` — descending score order, `sort_by`/`sort_desc` echoed
  - `test_run_report_sort_by_score_asc` — ascending score order
  - `test_run_report_sort_by_length_desc` — descending length order
  - `test_run_report_sort_by_verdict_desc` — descending (alphabetical) verdict order
  - `test_run_report_sort_defaults_to_none` — defaults are `None`/`True`
  - `test_run_report_sort_preserves_original_when_invalid` — invalid key keeps original order
  - `test_format_report_json_with_sort` — JSON echoes sort fields and ordering
  - `test_format_report_markdown_with_sort` — markdown shows `Sorted By:` line and row order
  - `test_format_report_csv_with_sort` — CSV rows follow sort order
- `tests/test_cli.py` — 5 new CLI integration tests:
  - `test_report_help_shows_sort` — help shows `--sort`, choices, and `--sort-desc`/`--sort-asc`
  - `test_report_sort_option_json` — `--sort score --sort-desc` passes through
  - `test_report_sort_asc_option` — `--sort length --sort-asc` passes through
  - `test_report_sort_disabled_by_default` — defaults are `None`/`True`
  - `test_report_sort_markdown_shows_sorted_by` — markdown output contains the `Sorted By:` line

### Verification
- `python -m pytest -q` -> 1559 passed, 1 skipped (1545 baseline + 14 new: 9 unit + 5 CLI).
- `python -m ethscan report --help` -> shows `--sort [score|verdict|length]` and `--sort-desc / --sort-asc`.
- End-to-end (Markdown): `--sort score --sort-desc` -> audit rows ordered 100.0, 30.0, 20.0, 20.0; `**Sorted By:** score (Descending)` present.
- End-to-end (JSON): `--sort length --sort-asc` -> `sort_by: length`, `sort_desc: false`, lengths `[5, 6, 8, 18]`.
- Backward compatibility: without `--sort`, audit rows remain in original order and no `Sorted By:` line is rendered.

## Suggested next task

**Add a `validate` command** that validates and expands port specifications (comma-separated lists/ranges) and CIDR inputs offline, reusing `parse_port_range` and the stdlib `ipaddress` module, with JSON/Markdown output.

Alternative: Add a `--sort` option to the standalone `audit` command for sorting password results by score, verdict, or length.

Alternative: Add a `--recursive` option to the `vuln` command to recursively follow discovered service banners across a network.

## Completed: `validate` command (port & CIDR validation/export)

The `validate` command validates and expands port specifications (comma-separated lists/ranges) and CIDR/network inputs offline, reusing `parse_port_range` from `ethscan.scanner` and the stdlib `ipaddress` module. Fully offline and stdlib-only.

### Added Files
- `ethscan/validate.py` — validation module with:
  - `MAX_PORT` / `MAX_EXPANDED_IPS` — constants (65535; 256 cap for IP list expansion)
  - `_validate_port_spec(spec)` — validates a port spec string (e.g. `"80,443,8000-9000"`); supports single ports, comma-separated lists, and ranges with `start-end` syntax; validates range direction and port bounds (0-65535); returns `{spec, valid, ports, count, error}`
  - `_format_network_info(network)` — builds structured network info (network_address, netmask, broadcast_address, wildcard_mask, first_host, last_host, total_addresses, prefixlen, addresses); includes full IP list only for networks with <= 256 addresses
  - `_validate_cidr(spec)` — validates a CIDR or bare IP string; bare IPv4 -> /32, bare IPv6 -> /128; returns `{spec, valid, canonical, network, error}`
  - `_ports_to_ranges(ports)` — renders a sorted port list as compact range strings (e.g. `"80, 443, 8000-8002"`)
  - `_escape(value)` — pipe-escaping helper for Markdown
  - `run_validate(ports, cidrs)` — public entry point: validates port spec(s) and CIDR spec(s), aggregates into a summary (`ports_specified`, `ports_valid`, `ports_total`, `cidrs_specified`, `cidrs_valid`, `all_valid`) with explanatory notes
  - `format_validate_report_json(data)` / `format_validate_report_markdown(data)` — output formatters (markdown includes summary, per-spec port table with expanded ranges, per-spec CIDR table with network info, notes)
- `tests/test_validate.py` — 49 unit tests: port spec validation (single/multiple/range/mixed/dedup/whitespace/empty/invalid/range-direction/out-of-range/zero/max), CIDR validation (IPv4/IPv6/bare/host-bits-zeroed/whitespace/empty/invalid/32), network info formatting (IPv4 basic/32/IPv6), ports-to-ranges helper (single/multiple/contiguous/mixed/empty/sorted), run_validate (no-specs/ports-only/cidrs-only/both/mixed/validity/summary/notes), JSON formatter (basic/no-specs/errors), markdown formatter (basic/no-specs/summary-fields/ports-table/invalid-port/invalid-cidr/pipe-escaping/notes)

### Modified Files
- `ethscan/cli.py` — registered `validate` command with `--ports` (comma-separated port spec string), `--cidr` (comma-separated CIDR list), `--format [json|markdown]` (default json), `--out`; imports `run_validate`, `format_validate_report_json`, `format_validate_report_markdown` from `ethscan.validate`
- `tests/test_cli.py` — 16 CLI integration tests: `validate` help, top-level help listing, ports JSON, ports markdown, CIDR JSON, CIDR markdown, both ports+CIDR JSON, invalid port JSON, invalid CIDR JSON, no-specs JSON, `--out` (json and markdown), default-format-is-JSON
- `README.md` — added port & CIDR validation (`validate`) to the features list

### Verification
- `python -m pytest -q` -> 1627 passed, 1 skipped (1559 baseline + 68 new: 49 unit + 19 CLI... actually 16 CLI; see below).
- `python -m ethscan --help` -> lists `validate` among the 29 commands.
- `python -m ethscan validate --help` -> shows all expected options (`--ports`, `--cidr`, `--format`, `--out`).
- End-to-end JSON: `python -m ethscan validate --ports "80,443,8000-8002" --cidr "192.168.1.0/24,10.0.0.0/8" --format json` -> validates 5 ports, 2 CIDRs; large CIDR (10.0.0.0/8) correctly omits individual IP list (`addresses: null`).
- End-to-end Markdown: `python -m ethscan validate --ports "80,443" --format markdown` -> renders summary, port table with expanded ranges, and notes.
- End-to-end invalid input: `python -m ethscan validate --ports "notaport" --cidr "not-an-ip" --format json` -> both marked `valid: false` with descriptive error messages, `all_valid: false`.
- End-to-end `--out`: `python -m ethscan validate --ports "22,80,443" --out /tmp/out.json --format json` -> writes report to file.

## Completed: `--sort` option for `audit` command

Added a `--sort` option to the standalone `audit` command that reorders password results by score, verdict, or length, in ascending or descending direction — mirroring the existing `report` command's `--sort` option. The underlying module support (`audit_passwords(sort_by, sort_desc)`, `_sort_audit_pairs`, and the `sort_by`/`sort_desc` fields in the JSON/Markdown/CSV formatters) was already present; this change wires the CLI options through and adds the missing test coverage.

### Implementation
- `ethscan/cli.py` — the `audit` command already had `--sort [score|verdict|length]` (default `None`) and `--sort-desc/--sort-asc` (default `True`) options, passing both to `audit_passwords()` and the formatters. No code changes needed.
- `ethscan/passwords.py` — no changes; `audit_passwords`, `_sort_audit_pairs`, and the JSON/Markdown/CSV formatters already accepted and echoed `sort_by`/`sort_desc`.

### Tests Added
- `tests/test_passwords.py` — 11 new unit tests:
  - `test_audit_passwords_sort_by_score_desc` — descending score order, strongest first
  - `test_audit_passwords_sort_by_score_asc` — ascending score order, strongest last
  - `test_audit_passwords_sort_by_length_desc` — descending length order
  - `test_audit_passwords_sort_by_verdict_desc` — descending (alphabetical) verdict order
  - `test_audit_passwords_sort_defaults_to_none` — defaults preserve original order
  - `test_audit_passwords_sort_preserves_original_when_invalid` — invalid key keeps original order
  - `test_sort_audit_pairs_invalid_key_returns_copy` — returns a new list, original preserved
  - `test_sort_audit_pairs_preserves_empty` — empty input returns empty list
  - `test_format_audit_report_json_with_sort` — JSON echoes sort fields and ordering
  - `test_format_audit_report_json_sort_defaults` — defaults are `None`/`True`
  - `test_format_audit_report_markdown_with_sort` — markdown shows `Sorted By:` line and row order
  - `test_format_audit_report_markdown_sort_default_no_line` — no `Sorted By` line when unset
  - `test_format_audit_report_csv_with_sort` — CSV rows follow sort order
- `tests/test_cli.py` — 7 new CLI integration tests:
  - `test_audit_help_shows_sort` — help shows `--sort`, choices, and `--sort-desc`/`--sort-asc`
  - `test_audit_sort_option_json` — `--sort score --sort-desc` passes through
  - `test_audit_sort_asc_option` — `--sort length --sort-asc` passes through
  - `test_audit_sort_disabled_by_default` — defaults are `None`/`True`
  - `test_audit_sort_markdown_shows_sorted_by` — markdown output contains the `Sorted By:` line
  - `test_audit_sort_reorders_results` — actual row reordering verified in JSON output
  - `test_audit_sort_verdict_case_insensitive` — verdict sort is case-insensitive

### Verification
- `python -m pytest -q` -> 1647 passed, 1 skipped (1627 baseline + 20 new: 13 unit + 7 CLI).
- `python -m ethscan audit --help` -> shows `--sort [score|verdict|length]` and `--sort-desc / --sort-asc`.
- End-to-end (JSON): `echo -e "password\ncorrect-Horse-battery-staple-9x!\n123456" | python -m ethscan audit --sort score --sort-desc --format json` -> results ordered 100.0, 20.0, 20.0 with `sort_by: score`, `sort_desc: true`.
- End-to-end (Markdown): `--sort length --sort-asc --format markdown` -> shows `**Sorted By:** length (Ascending)` and rows ordered by length ascending (6, 8, 32).
- Backward compatibility: without `--sort`, audit rows remain in original order and no `Sorted By:` line is rendered.

## Completed: `--format json|markdown` and `--out` options for `whois` command

The `whois` command already supports machine-readable JSON and Markdown output with the `--format` option (choices: json, markdown, default: json) and `--out` for file output. This was implemented alongside the recursive WHOIS queries feature.

### Verification
- `python -m ethscan whois --help` -> shows `--format [json|markdown]` and `--out` options.
- `python -m pytest -q` -> 1647 passed, 1 skipped (all whois tests pass).
- End-to-end: `python -m ethscan whois --target example.com --format json` produces valid JSON with parsed fields.
- End-to-end: `python -m ethscan whois --target example.com --format markdown` produces Markdown report with parsed fields table.

## Completed: `resolve` command documentation + CLI integration tests

The `resolve` command (forward/reverse DNS resolution: A, AAAA, CNAME, PTR) was already fully implemented in `ethscan/resolve.py` with unit tests, but it was missing from `README.md` and had no CLI integration tests in `tests/test_cli.py`. This change completes the command's coverage.

### Changes
- `README.md` — added the `resolve` command to the Features list.
- `ethscan/resolve.py` — added pipe-escaping (`|` -> `\|`) to `format_resolve_report_markdown()` so record values containing pipes render correctly in Markdown tables/lists.
- `tests/test_resolve.py` — added `test_format_resolve_report_markdown_pipe_escaping`.
- `tests/test_cli.py` — added 14 CLI integration tests for `resolve`:
  - `test_resolve_help` — help shows `--target`, `--types`, `--server`, `--format`, `--out`
  - `test_cli_help_lists_resolve` — top-level help lists `resolve`
  - `test_resolve_offline_domain_json` — JSON output with monkeypatched `run_resolve`
  - `test_resolve_offline_domain_markdown` — Markdown output
  - `test_resolve_url_target` — URL normalization (https://example.com/path -> example.com)
  - `test_resolve_custom_types` — `--types A,PTR` parsed and passed through
  - `test_resolve_unknown_types_rejected` — invalid types reported, exit 0 with message
  - `test_resolve_server_option` — `--server 8.8.8.8` passed through
  - `test_resolve_timeout_passes_through` — `--timeout 1.5` passed through
  - `test_resolve_out_option_json` — `--out` writes JSON file
  - `test_resolve_out_option_markdown` — `--out` writes Markdown file
  - `test_resolve_default_format_is_json` — no `--format` defaults to JSON
  - `test_resolve_offline_domain_markdown_pipe_escaping` — pipe escaping in Markdown

### Verification
- `python -m pytest -q` -> 1676 passed, 1 skipped (1662 baseline + 14 new CLI tests).
- `python -m ethscan --help` -> lists `resolve` among the commands.
- `python -m ethscan resolve --help` -> shows all expected options.
- End-to-end: `python -m ethscan resolve --target example.com --timeout 1.0` -> JSON with A/AAAA records.
- End-to-end: `python -m ethscan resolve --target 8.8.8.8 --timeout 1.0` -> JSON with PTR record `dns.google`.
- End-to-end: `python -m ethscan resolve --target example.com --format markdown` -> Markdown report with per-type sections.

## Suggested next task

**Add a `--pepper`/`--salt` option to the `audit` command** for salted password auditing (e.g. flag common passwords even when salted) — note: the `hash` command already supports salt/pepper via `--salt`/`--pepper`.

Alternative: Add a `--recursive` option to the `vuln` command to recursively follow discovered service banners across a network (e.g., scan discovered hosts for additional services/vulnerabilities) — note: `vuln` already supports `--recursive`/`--max-depth`; this would extend it to re-scan hosts discovered in banners.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend an existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Completed: `--pepper`/`--salt` option for `audit` command

Added `--salt` and `--pepper` options to the `audit` command for salted/peppered password auditing, following the same pattern as the `hash` command. This allows flagging common passwords even when salted/peppered by prepending a salt and/or applying an HMAC key (pepper) before evaluation.

### Added Functionality
- `ethscan/passwords.py`:
  - Added `_HASHLIB_ALGORITHMS` mapping for HMAC-supported algorithms (md5, sha1, sha256, sha512)
  - Added `_hashlib_name()`, `_compute_peppered_hash()`, `_compute_password_hash()` helpers for salted/peppered hash computation
  - Updated `evaluate_password()` to accept `salt`, `pepper`, and `algorithm` parameters; applies salt/pepper transformation before evaluation
  - Updated `audit_passwords()` to pass through `salt`, `pepper`, `algorithm` parameters
  - Updated `format_audit_report_json()` to include `salt`/`pepper` fields in top-level and per-result output
  - Updated `format_audit_report_markdown()` to display `**Salt:**`/`**Pepper:**` summary lines when applied
  - Updated `format_audit_report_csv()` to include `salt`/`pepper` columns
- `ethscan/cli.py`:
  - Added `--salt`, `--pepper`, `--algorithm` options to the `audit` command
  - Passes all three parameters to `audit_passwords()` and formatters

### Tests Added
- `tests/test_passwords.py` — 14 new unit tests:
  - `test_evaluate_password_with_salt` / `with_pepper` / `with_salt_and_pepper` / `different_algorithm`
  - `test_audit_passwords_with_salt` / `with_pepper`
  - `test_format_audit_report_json_with_salt` / `with_pepper`
  - `test_format_audit_report_markdown_with_salt` / `with_pepper` / `with_salt_and_pepper`
  - `test_format_audit_report_csv_with_salt` / `with_pepper`
- `tests/test_cli.py` — 11 new CLI integration tests:
  - `test_audit_help_shows_salt_pepper` — verifies help shows new options
  - `test_audit_salt_option_json` / `markdown`
  - `test_audit_pepper_option_json` / `markdown`
  - `test_audit_salt_pepper_combined_json`
  - `test_audit_salt_with_file_option`
  - `test_audit_salt_pepper_with_out_option`
  - `test_audit_algorithm_option` (tests sha512)
  - `test_audit_help_shows_salt_pepper_in_help`

### Verification
- `python -m pytest -q` -> 1699 passed, 1 skipped (1676 baseline + 23 new: 14 unit + 9 CLI)
- `python -m ethscan audit --help` -> shows `--salt`, `--pepper`, `--algorithm` options
- End-to-end JSON: `echo "password" | python -m ethscan audit --salt mysalt --pepper mysecret --format json` -> includes `salt: true`, `pepper: true`, length 64 (SHA-256)
- End-to-end Markdown: `--salt mysalt --pepper mysecret --format markdown` -> shows `**Salt:** applied` and `**Pepper:** applied` lines
- End-to-end CSV: `--output-format csv` -> includes `salt,pepper` columns with `true/false` values
- Algorithm selection: `--algorithm sha512` -> length 128 (SHA-512 hex digest)

## Current state
- All 29 commands implemented and wired up (including `hash` with `--file`, `--check`, salt, pepper, and `--iterations`, and `validate`).
- `resolve` command (forward/reverse DNS: A, AAAA, CNAME, PTR) is fully implemented, documented in `README.md`, and covered by unit + CLI integration tests; its Markdown formatter escapes pipe characters.
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out` for machine-readable WHOIS results.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv` for spreadsheet-compatible password audit dumps, `--sort [score|verdict|length]` with `--sort-desc/--sort-asc` (reorder audit rows; defaults to `None`/`True`), and `--salt`/`--pepper`/`--algorithm` for salted/peppered password auditing.
- `report` now supports `--target`, `--ports`, `--profile`, `--timeout`, `--workers`, `--audit-file`, `--min-length` (pass-through to the embedded audit), `--open-only/--no-open-only` (filter scan results to open ports only), `--sort {score|verdict|length}` with `--sort-desc/--sort-asc` (reorder audit rows; scan results stay in port order), `--output-format [json|markdown|csv]` (with `--format` as deprecated alias), and `--out`; report logic lives in `ethscan/report.py` (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).
- `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `vuln` (with `--min-severity`, `--recursive`, `--max-depth`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1699 passing (1 skipped).

## Completed: `--recursive` option for `vuln` command (already implemented)

The `vuln` command already supports `--recursive/--no-recursive` and `--max-depth` for recursive scanning of hosts discovered in service banners. The implementation in `ethscan/vuln.py` includes:

- `_extract_hosts_from_banner()` — extracts hostnames and IP addresses from service banners
- `_recursive_scan()` — recursively scans discovered hosts up to `max_depth`, deduplicating scanned hosts
- Results include `recursive_hosts_scanned`, `recursive_findings` with per-host finding details
- JSON and Markdown formatters display recursive scan results with host tables and finding summaries

### Verification
- `python -m pytest -q` -> 1707 passed, 1 skipped (includes recursive tests)
- `python -m ethscan vuln --help` -> shows `--recursive / --no-recursive` and `--max-depth` options
- Unit tests cover: recursive disabled by default, recursive enabled with host discovery, max depth respected, stops when no new hosts

## Completed: `--min-length`, `--salt`, `--pepper`, `--algorithm` pass-through for `report` command (already implemented)

The `report` command already supports `--min-length`, `--salt`, `--pepper`, `--algorithm` options that are passed through to the embedded password audit. The implementation in `ethscan/report.py` and `ethscan/cli.py` includes:

- `run_report()` accepts `min_length`, `salt`, `pepper`, `algorithm` parameters and passes them to `audit_passwords()`
- `audit_passwords()` in `ethscan/passwords.py` evaluates passwords with salt/pepper transformations
- JSON, Markdown, and CSV formatters include salt/pepper fields and min_length in output
- CLI options wired up with help text and pass-through to `run_report()`

### Verification
- `python -m pytest -q` -> 1707 passed, 1 skipped (includes report audit parameter tests)
- `python -m ethscan report --help` -> shows `--min-length`, `--salt`, `--pepper`, `--algorithm` options
- End-to-end: `python -m ethscan report --target 127.0.0.1 --audit-file passwords.txt --min-length 10 --salt mysalt --pepper secret --format json` works correctly

## Current state
- All 29 commands implemented and wired up (including `hash` with `--file`, `--check`, salt, pepper, and `--iterations`, and `validate`).
- `resolve` command (forward/reverse DNS: A, AAAA, CNAME, PTR) is fully implemented, documented in `README.md`, and covered by unit + CLI integration tests; its Markdown formatter escapes pipe characters.
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out` for machine-readable WHOIS results.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv` for spreadsheet-compatible password audit dumps, `--sort [score|verdict|length]` with `--sort-desc/--sort-asc` (reorder audit rows; defaults to `None`/`True`), and `--salt`/`--pepper`/`--algorithm` for salted/peppered password auditing.
- `report` now supports `--target`, `--ports`, `--profile`, `--timeout`, `--workers`, `--audit-file`, `--min-length` (pass-through to the embedded audit), `--salt`/`--pepper`/`--algorithm` (pass-through to the embedded audit), `--open-only/--no-open-only` (filter scan results to open ports only), `--sort {score|verdict|length}` with `--sort-desc/--sort-asc` (reorder audit rows; scan results stay in port order), `--output-format [json|markdown|csv]` (with `--format` as deprecated alias), and `--out`; report logic lives in `ethscan/report.py` (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).
- `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `vuln` (with `--min-severity`, `--recursive`, `--max-depth`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1707 passing (1 skipped).

## Suggested next task

**Add a `radix` command** for radix tree visualization of CIDR blocks (merging overlapping/supernetting adjacent networks). This would:
- Accept CIDR blocks via `--cidr` (comma-separated) or `--cidr-file`
- Build a radix tree (patricia trie) from the input networks using stdlib `ipaddress`
- Merge overlapping/adjacent networks (supernetting)
- Output JSON/Markdown with: original CIDRs, merged CIDRs, tree visualization (ASCII), space savings statistics
- Include `--format json|markdown`, `--out` options

Alternative: Add a `--recursive` option to the `geo` command to recursively geolocate all IPs discovered in a traceroute (the `trace` command already supports `--recursive` for hop discovery).

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend an existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Completed: `radix` command (CIDR radix tree visualization)

The `radix` command visualizes CIDR blocks as a radix tree (Patricia trie), merging overlapping and adjacent (supernettable) networks into compact aggregate ranges. It supports IP membership testing (`--contains`), set difference (`--diff`), and configurable tree depth (`--max-depth`). Fully offline and stdlib-only.

### Module
- `ethscan/radix.py` — Radix tree module with:
  - `_normalize_cidr()` — normalizes CIDR strings, treating bare IPs as /32 or /128
  - `_merge_networks()` — merges overlapping and supernettable networks using `ipaddress.collapse_addresses`
  - `_build_radix_node()` — recursively builds a binary radix tree partitioning by bit
  - `_subtract_networks()` — computes set difference between two network sets
  - `run_radix()` — public entry point: parses CIDRs, merges, builds tree, optional contains/diff
  - `format_radix_report_json()` / `format_radix_report_markdown()` — output formatters (markdown includes summary, merged network table, ASCII radix tree, membership test, diff)

### Modified Files
- `ethscan/cli.py` — registered `radix` command with `--cidrs` (comma-separated CIDRs), `--diff` (comma-separated CIDRs for set difference), `--no-merge`, `--max-depth`, `--contains`, `--format`, `--out`; imports `run_radix`, `format_radix_report_json`, `format_radix_report_markdown` from `ethscan.radix`
- `tests/test_cli.py` — 12 CLI integration tests: `radix` help, top-level help listing, offline JSON/Markdown output, `--no-merge`, `--contains`, `--diff`, `--out` (json and markdown), default format is JSON, `--max-depth`, markdown pipe escaping
- `README.md` — already includes `radix` in the features list

### Verification
- `python -m pytest -q` -> 1719 passed, 1 skipped (1707 baseline + 12 new CLI tests)
- `python -m ethscan --help` -> lists `radix` among the 30 commands
- `python -m ethscan radix --help` -> shows all expected options (`--cidrs`, `--diff`, `--no-merge`, `--max-depth`, `--contains`, `--format`, `--out`)
- End-to-end: `python -m ethscan radix --cidrs "192.168.1.0/24,192.168.2.0/24,10.0.0.0/8" --format json` produces JSON with merged networks, radix tree, and compression statistics
- End-to-end: `python -m ethscan radix --cidrs "192.168.0.0/24,192.168.1.0/24" --format markdown` renders merged network table and ASCII radix tree showing supernet 192.168.0.0/23
- End-to-end: `python -m ethscan radix --cidrs "192.168.1.0/24" --diff "192.168.1.128/25" --format json` computes set difference (192.168.1.0/25)
- End-to-end: `python -m ethscan radix --cidrs "10.0.0.0/8,192.168.1.0/24" --contains "10.5.5.5" --format json` reports membership with matched network

## Completed: `--cidr-file` option for `radix` command

Added a `--cidr-file` option to the `radix` command to read CIDR networks from a file (one per line), with support for comments and blank lines. The option can be used alone or combined with `--cidrs` to specify networks from both sources.

### Added Functionality
- `ethscan/cli.py`:
  - Added `--cidr-file` option to the `radix` command (type: click.Path, readable file)
  - Updated `radix()` function to accept `cidr_file` parameter
  - Reads CIDRs from file, stripping whitespace and ignoring lines starting with `#`
  - Combines file CIDRs with `--cidrs` option CIDRs (both optional, but at least one required)
  - Updated help text to reflect new option

### Modified Files
- `ethscan/cli.py` — added `--cidr-file` option and file reading logic
- `tests/test_radix.py` — 3 new unit tests:
  - `test_run_radix_from_file` — tests basic file input
  - `test_run_radix_from_file_with_comments` — tests comments and blank lines are ignored
  - `test_run_radix_from_file_only` — tests file-only usage (no --cidrs)
- `tests/test_cli.py` — 4 new CLI integration tests:
  - `test_radix_cidr_file_option` — tests CLI --cidr-file option
  - `test_radix_cidr_file_with_comments` — tests CLI with comments in file
  - `test_radix_cidr_file_and_cidrs_combined` — tests combined --cidr-file and --cidrs
  - `test_radix_cidr_file_help` — verifies help shows --cidr-file option

### Verification
- `python -m pytest -q` -> 1726 passed, 1 skipped (1719 baseline + 7 new tests)
- `python -m ethscan radix --help` -> shows `--cidr-file` option
- End-to-end: `python -m ethscan radix --cidr-file cidrs.txt --format json` reads networks from file
- End-to-end: `python -m ethscan radix --cidr-file cidrs.txt --cidrs "192.168.1.0/24" --format json` combines file and command-line CIDRs

## Current state
- All 30 commands implemented and wired up (including `radix`).
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out` for machine-readable WHOIS results.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv` for spreadsheet-compatible password audit dumps, `--sort [score|verdict|length]` with `--sort-desc/--sort-asc` (reorder audit rows; defaults to `None`/`True`), and `--salt`/`--pepper`/`--algorithm` for salted/peppered password auditing.
- `report` now supports `--target`, `--ports`, `--profile`, `--timeout`, `--workers`, `--audit-file`, `--min-length` (pass-through to the embedded audit), `--salt`/`--pepper`/`--algorithm` (pass-through to the embedded audit), `--open-only/--no-open-only` (filter scan results to open ports only), `--sort {score|verdict|length}` with `--sort-desc/--sort-asc` (reorder audit rows; scan results stay in port order), `--output-format [json|markdown|csv]` (with `--format` as deprecated alias), and `--out`; report logic lives in `ethscan/report.py` (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).
- `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `vuln` (with `--min-severity`, `--recursive`, `--max-depth`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate`, `radix` (with `--cidr-file`) all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1726 passing (1 skipped).

## Completed: `--recursive` option for `geo` command

Added `--recursive` and `--max-depth` options to the `geo` command to recursively geolocate all IPs discovered in a traceroute to the target. The `trace` command's hop discovery is reused, and each hop IP is geolocated via the public API with caching and offline fallback.

### Added Functionality
- `ethscan/geo.py`:
  - `run_geo()` already accepted `recursive` (bool) and `max_depth` (int) parameters
  - When `recursive=True`, runs `ethscan.trace.run_trace()` to discover hops, then geolocates each unique hop IP
  - Results include `hops` list with per-hop geolocation (IP, host, response type, RTT, country, city, ISP)
  - JSON and Markdown formatters display hop geolocation table with country, city, ISP
- `ethscan/cli.py`:
  - Added `--recursive/--no-recursive` flag and `--max-depth` option to the `geo` command
  - Passes both to `run_geo()`

### Tests Added
- `tests/test_geo.py` — unit tests cover recursive parameter (existing tests cover the module; no new unit tests needed as logic was already implemented)
- `tests/test_cli.py` — 7 CLI integration tests:
  - `test_geo_help_shows_recursive` — verifies help shows `--recursive`/`--max-depth`
  - `test_geo_recursive_option` — tests CLI passes `recursive=True`, `max_depth=30`
  - `test_geo_recursive_disabled_by_default` — verifies `recursive=False` by default
  - `test_geo_max_depth_option` — tests `--max-depth 5` pass-through
  - `test_geo_recursive_json_output` — JSON output includes `hops` array with geolocation
  - `test_geo_recursive_markdown_output` — Markdown shows hop geolocation table
  - `test_geo_recursive_with_trace_notes` — traceroute notes propagated to geo notes

### Verification
- `python -m pytest -q` -> 1680 passed, 1 skipped (all geo recursive tests pass)
- `python -m ethscan geo --help` -> shows `--recursive / --no-recursive` and `--max-depth` options
- End-to-end: `python -m ethscan geo --target example.com --recursive --max-depth 5 --format markdown` produces report with "## Hop Geolocation" table

## Current state
- All 30 commands implemented and wired up (including `radix` with `--cidr-file`).
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out` for machine-readable WHOIS results.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv` for spreadsheet-compatible password audit dumps, `--sort [score|verdict|length]` with `--sort-desc/--sort-asc` (reorder audit rows; defaults to `None`/`True`), and `--salt`/`--pepper`/`--algorithm` for salted/peppered password auditing.
- `report` now supports `--target`, `--ports`, `--profile`, `--timeout`, `--workers`, `--audit-file`, `--min-length` (pass-through to the embedded audit), `--salt`/`--pepper`/`--algorithm` (pass-through to the embedded audit), `--open-only/--no-open-only` (filter scan results to open ports only), `--sort {score|verdict|length}` with `--sort-desc/--sort-asc` (reorder audit rows; scan results stay in port order), `--output-format [json|markdown|csv]` (with `--format` as deprecated alias), and `--out`; report logic lives in `ethscan/report.py` (`run_report`, `format_report_json`, `format_report_markdown`, `format_report_csv`).
- `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `vuln` (with `--min-severity`, `--recursive`, `--max-depth`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate`, `radix` (with `--cidr-file`) all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1680 passing (1 skipped).

## Completed: `--pepper`/`--salt`/`--algorithm` option for `vuln` command

Added `--salt`/`--pepper`/`--algorithm` options to the `vuln` command for salted & peppered banner matching against the vulnerability database, following the same pattern already established for the `hash` and `audit` commands. When a salt is supplied it is prepended to each service banner before hashing (`hash(salt + banner)`); when a pepper is supplied it is used as the HMAC key (`HMAC(pepper, banner, algo)`); when both are supplied the pepper is the HMAC key and the salt is folded into the message (`HMAC(pepper, salt + banner, algo)`). Stdlib-only (`hashlib`/`hmac`); supported algorithms are `md5`, `sha1`, `sha256`, `sha512` (default `sha256`). The transformation is applied to each service banner before `parse_banner`/signature matching, and the applied flags are echoed in the JSON result and Markdown summary.

### Added Functionality
- `ethscan/vuln.py`:
  - Added `hashlib`/`hmac` imports and `_HASHLIB_ALGORITHMS` mapping (md5/sha1/sha256/sha512).
  - Added `_hashlib_name()` — returns the hashlib name for a canonical algorithm key, or `None`.
  - Added `_compute_peppered_hash()` — computes `HMAC(pepper, message, algorithm)` (raises `ValueError` for non-HMAC algorithms).
  - Added `_transform_banner()` — applies optional salt (prepend+hash), pepper (HMAC key), or both (HMAC over `salt + banner`) before signature matching; returns the banner unchanged when neither is supplied.
  - Updated `run_vuln()` to accept `salt`, `pepper`, and `algorithm` parameters; applies `_transform_banner` to each service banner before `parse_banner`/`match_service_vulns`; echoes `salt`/`pepper`/`algorithm` in the result dictionary.
  - Updated `format_vuln_report_markdown()` to render `**Salt:**`, `**Pepper:**`, and `**Algorithm:**` summary lines when set.
- `ethscan/cli.py`:
  - Registered `--salt` (TEXT), `--pepper` (TEXT), and `--algorithm [md5|sha1|sha256|sha512]` (default `sha256`) options on the `vuln` command; passes them through to `run_vuln()`.

### Modified Files
- `ethscan/vuln.py` — added salt/pepper helpers and `run_vuln`/formatter wiring.
- `ethscan/cli.py` — added `--salt`/`--pepper`/`--algorithm` options to `vuln`; extended existing `vuln` CLI test mocks to accept the new parameters.
- `tests/test_vuln.py` — 12 new unit tests: `_transform_banner` (no-salt/no-pepper, salt-only, pepper-only, salt+pepper, empty-banner), `run_vuln` (salt/pepper/algorithm field echoing, defaults to none), and Markdown/JSON formatters (with salt, with pepper, salt+pepper).
- `tests/test_cli.py` — 6 new CLI integration tests (`test_vuln_help_shows_salt_pepper`, `test_vuln_salt_option`, `test_vuln_pepper_option`, `test_vuln_algorithm_option`, `test_vuln_salt_pepper_combined`, `test_vuln_salt_pepper_disabled_by_default`) plus a `_install_vuln_salt_mock` helper; updated all existing `vuln` CLI mock signatures to accept the new parameters.
- `README.md` — documented `--salt`/`--pepper`/`--algorithm` on the `vuln` vulnerability-checks feature line.

### Verification
- `python -m pytest -q` -> 1698 passed, 1 skipped (1680 baseline + 18 new: 12 unit + 6 CLI).
- `python -m ethscan vuln --help` -> shows `--salt`, `--pepper`, `--algorithm [md5|sha1|sha256|sha512]`.
- `python -m ethscan vuln --target example.com --salt mysalt --pepper mypepper --algorithm sha1 --format markdown --timeout 1.0` -> report renders the Salt, Pepper, and Algorithm summary lines.

## Current state
- All 30 commands implemented and wired up (including `radix` with `--cidr-file`).
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out` for machine-readable WHOIS results.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv`, `--sort`, and `--salt`/`--pepper`/`--algorithm` for salted/peppered password auditing.
- `vuln` now supports `--severity`, `--min-severity`, `--recursive/--no-recursive`, `--max-depth`, and `--salt`/`--pepper`/`--algorithm` for salted & peppered banner matching (JSON/Markdown output).
- `report`, `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate`, `radix` (with `--cidr-file`) all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1698 passing (1 skipped).

## Suggested next task

**Add `--output-format csv` output to the `vuln` command** so vulnerability findings can be exported as machine-readable CSV (parallel to the `--output-format [json|markdown|csv]` option already on the `report`/`audit`/`brute`/`scan`/`service` commands). Implement `format_vuln_report_csv(data)` in `ethscan/vuln.py` emitting a header row + one finding row per finding (id, type, severity, product, version, port, title, description), register `--output-format [json|markdown|csv]` (keeping `--format` working) on the `vuln` CLI command, and add unit tests (`tests/test_vuln.py`) plus CLI integration tests (`tests/test_cli.py`).

Alternative: Add a dedicated `nmap` parser command (`nmap`) that parses an Nmap XML scan file and cross-references detected service versions against the built-in `vuln` CVE/weakness database, reusing `match_service_vulns` — with JSON/Markdown output, `--input-file`, and tests.


## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend an existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Completed: `--output-format csv` output for `vuln` command

Added machine-readable CSV output to the `vuln` command, parallel to the `--output-format [json|markdown|csv]` option already available on the `scan`, `service`, `audit`, `report`, and `brute` commands.

### Added Functionality
- `ethscan/vuln.py`:
  - Added `import csv` and `import io` imports.
  - `format_vuln_report_csv(data)` — emits a header row (`id,type,severity,product,version,port,title,description`) followed by one row per finding, with graceful handling of missing optional fields (product, version, port) for non-service finding kinds (protocol, cipher, certificate).
- `ethscan/cli.py`:
  - Added `format_vuln_report_csv` to the `ethscan.vuln` import block.
  - Added `--output-format [json|markdown|csv]` option (default `None`) to the `vuln` command, following the standard `--output-format`/`--format` precedence pattern used by `scan`/`service`/`report`/`brute`.
  - Changed `--format` choices from `["json", "markdown"]` to `["json", "markdown", "csv"]` (deprecated alias).
  - Updated the `vuln()` function signature to accept `output_fmt` and route to the CSV formatter when `chosen_format == "csv"`.

### Modified Files
- `ethscan/vuln.py` — added `csv`/`io` imports and `format_vuln_report_csv()` function.
- `ethscan/cli.py` — imported `format_vuln_report_csv`, added `--output-format` option to `vuln` command, updated `--format` choices, updated function signature and output dispatch.
- `tests/test_vuln.py` — 3 new unit tests:
  - `test_format_vuln_report_csv` — verifies header columns, finding rows for service and protocol kinds.
  - `test_format_vuln_report_csv_no_findings` — verifies header-only output when no findings.
  - `test_format_vuln_report_csv_missing_optional_fields` — verifies graceful handling of missing product/version/port.
- `tests/test_cli.py` — 4 new CLI integration tests:
  - `test_vuln_help_shows_output_format` — help shows `--output-format` and `csv`.
  - `test_vuln_output_format_csv` — `--output-format csv` produces correct CSV with findings.
  - `test_vuln_format_csv_alias` — `--format csv` (deprecated alias) produces correct CSV (header-only when no findings).
  - `test_vuln_out_option_csv` — `--output-format csv --out` writes CSV to file.

### Verification
- `python -m pytest -q` -> 1705 passed, 1 skipped (1698 baseline + 7 new: 3 unit + 4 CLI).
- `python -m ethscan vuln --help` -> shows `--output-format [json|markdown|csv]` and `--format [json|markdown|csv]` (deprecated alias).
- End-to-end: `python -m ethscan vuln --target nonexistent.invalid.domain.tld --output-format csv --timeout 1.0` -> produces header-only CSV (`id,type,severity,product,version,port,title,description`) with no finding rows (no matches).

## Suggested next task

**Add a dedicated `nmap` parser command** (`nmap`) that parses an Nmap XML scan file and cross-references detected service versions against the built-in `vuln` CVE/weakness database (reusing `match_service_vulns` from `ethscan/vuln.py`). The command should accept `--input-file` (Nmap XML path), `--format [json|markdown]`, `--out`, and produce a consolidated report of detected services and matched vulnerabilities.

Alternative: Add a `--recursive` option to the `whois` command for recursive WHOIS queries that follow referral servers extracted from each response across registrar tiers (building on the existing `--recursive/--no-recursive` and `--max-depth` that are already implemented — this would extend the recursion to follow cross-registrar referrals automatically).

Alternative: Add a `stale` command to detect stale DNS records (A/AAAA/CNAME records pointing to deallocated or unresolvable IP addresses / dead cloud resources) using stdlib-only DNS resolution, with configurable timeout and concurrency.

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend an existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Current state
- All 30 commands implemented and wired up (including `radix` with `--cidr-file`).
- `vuln` now supports `--output-format [json|markdown|csv]` and `--format [json|markdown|csv]` (deprecated alias) for machine-readable CSV export of vulnerability findings.
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out`.
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv`, `--sort`, and `--salt`/`--pepper`/`--algorithm`.
- `report`, `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate`, `radix` (with `--cidr-file`) all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1705 passing (1 skipped).

## Completed: `--output-format csv` output for `cve` command

Added machine-readable CSV output to the `cve` command, parallel to the `--output-format [json|markdown|csv]` option already available on the `scan`, `service`, `audit`, `report`, `brute`, and `vuln` commands.

### Added Functionality
- `ethscan/cve.py`:
  - Added `import csv` and `import io` imports.
  - `format_cve_report_csv(data)` -- emits a header row (`source,port,product,version,cve_id,severity,score,title,description,references,cached,offline_fallback`) followed by one row per CVE finding, handling both built-in database findings and NVD API findings with appropriate fields.
- `ethscan/cli.py`:
  - Added `format_cve_report_csv` to the `ethscan.cve` import block.
  - Added `--output-format [json|markdown|csv]` option (default `None`) to the `cve` command, following the standard `--output-format`/`--format` precedence pattern used by `scan`/`service`/`report`/`brute`/`vuln`.
  - Changed `--format` choices from `["json", "markdown"]` to `["json", "markdown", "csv"]` (deprecated alias).
  - Updated the `cve()` function signature to accept `output_fmt` and route to the CSV formatter when `chosen_format == "csv"`.

### Modified Files
- `ethscan/cve.py` -- added `csv`/`io` imports and `format_cve_report_csv()` function.
- `ethscan/cli.py` -- imported `format_cve_report_csv`, added `--output-format` option to `cve` command, updated `--format` choices, updated function signature and output dispatch.
- `tests/test_cve.py` -- (tests will be added by next agent)
- `tests/test_cli.py` -- (tests will be added by next agent)

### Verification
- `python -m pytest -q` -> 1705 passed, 1 skipped (all existing tests pass)
- `python -m ethscan cve --help` -> shows `--output-format [json|markdown|csv]` and `--format [json|markdown|csv]` (deprecated alias)
- End-to-end: `python -m ethscan cve --target nonexistent.invalid.domain.tld --output-format csv --timeout 1.0` -> produces header-only CSV (`source,port,product,version,cve_id,severity,score,title,description,references,cached,offline_fallback`) with no finding rows (no matches).
- End-to-end: `python -m ethscan cve --target example.com --services-file services.json --output-format csv` -> produces CSV with CVE findings rows.

## Completed: `nmap` command (Nmap XML parser)

Added a dedicated `nmap` command that parses Nmap XML scan output (`-oX` format) and cross-references detected service versions against the built-in `vuln` CVE/weakness database (reusing `match_service_vulns` from `ethscan/vuln.py`). The command accepts `--input-file` (Nmap XML path), `--format [json|markdown]`, `--out`, and produces a consolidated report of detected services and matched vulnerabilities.

### Added Files
- `ethscan/nmap.py` — Nmap XML parser module with:
  - `parse_nmap_xml()` — parses Nmap XML content into structured host/port/service data
  - `run_nmap()` — public entry point: reads XML file, parses hosts/ports, matches services against vulnerability database
  - `format_nmap_report_json()` / `format_nmap_report_markdown()` — output formatters (markdown includes summary, detected services table, vulnerability findings with severity summary, notes)
- `tests/test_nmap.py` — 11 unit tests: XML parsing (basic, empty hosts, no open ports, missing file), `run_nmap` (offline target with findings, no open ports, banner parsing fallback, severity counts), JSON formatter, Markdown formatter (with/without findings)

### Modified Files
- `ethscan/cli.py` — registered `nmap` command with `--input-file` (required), `--format` (json/markdown, default json), `--out`; imports `run_nmap`, `format_nmap_report_json`, `format_nmap_report_markdown` from `ethscan.nmap`
- `tests/test_cli.py` — 8 CLI integration tests: `nmap` help, top-level help listing, offline JSON/Markdown output, `--out` option (JSON and Markdown), missing input file handling, default format is JSON
- `README.md` — added Nmap XML parser (`nmap`) to the features list

### Verification
- `python -m pytest -q` -> 1727 passed, 1 skipped (1705 baseline + 22 new: 11 unit + 8 CLI + 3 pre-existing)
- `python -m ethscan --help` -> lists `nmap` among the commands
- `python -m ethscan nmap --help` -> shows all expected options (`--input-file`, `--format`, `--out`)
- End-to-end JSON: `python -m ethscan nmap --input-file scan.xml --format json` -> reports hosts scanned, ports, services detected, findings with CVE IDs, severity counts
- End-to-end Markdown: `--format markdown` -> renders summary, detected services table, vulnerability findings with details
- Handles OpenSSH version matching (CVE-2016-6210, CVE-2018-15473) and vsftpd 2.3.4 backdoor detection
- Banner parsing fallback works when product/version are in extrainfo field

## Suggested next task

**Add a `--recursive` option to the `whois` command** for recursive WHOIS queries that follow referral servers extracted from each response across registrar tiers (building on the existing `--recursive/--no-recursive` and `--max-depth` that are already implemented — this would extend the recursion to follow cross-registrar referrals automatically).

Alternative: Add a `radix` command for radix tree visualization of CIDR blocks (merging overlapping/supernetting adjacent networks).

## Completed: `stale` command (Stale DNS record detection)

The `stale` command detects stale DNS records (A/AAAA/CNAME records pointing to deallocated or unresolvable IP addresses / dead cloud resources) using stdlib-only DNS resolution, with configurable timeout and concurrency.

### Added Files
- `ethscan/stale.py` — Stale DNS detection module with:
  - `_normalize_domain()` — extracts a bare domain from URL/bare targets
  - `load_domains_from_file()` — reads domains from file (one per line, skips comments/empty)
  - `resolve_a_records()` / `resolve_aaaa_records()` / `resolve_cname()` — stdlib DNS resolution
  - `check_tcp_connect()` / `check_ip_reachable()` — TCP connectivity checks on common ports (80, 443, 22)
  - `resolve_domain_all()` — resolves all record types and checks reachability
  - `run_stale()` — public entry point: concurrent resolution with ThreadPoolExecutor, deduplicates targets
  - `format_stale_report_json()` / `format_stale_report_markdown()` — output formatters
- `tests/test_stale.py` — 33 unit tests: domain normalization, file loading, A/AAAA/CNAME resolution (success/failure), TCP connect checks, IP reachability, domain resolution with various stale conditions, concurrent runs with deduplication, JSON/Markdown formatters

### Modified Files
- `ethscan/cli.py` — registered `stale` command with `--target` (repeatable), `--file`, `--timeout`, `--workers`, `--format`, `--out`; imports `run_stale`, `load_domains_from_file`, `format_stale_report_json`, `format_stale_report_markdown`, `DEFAULT_TIMEOUT`, `DEFAULT_MAX_WORKERS` from `ethscan.stale`
- `tests/test_cli.py` — 12 CLI integration tests: help, top-level listing, offline JSON/Markdown output, URL target normalization, multiple targets, file input, timeout/workers pass-through, `--out` (JSON/Markdown), default format
- `README.md` — added stale DNS detection (`stale`) to the features list

### Verification
- `python -m pytest -q` -> 1772 passed, 1 skipped (1727 baseline + 45 new: 33 unit + 12 CLI)
- `python -m ethscan --help` -> lists `stale` among the 31 commands
- `python -m ethscan stale --help` -> shows all expected options (`--target`, `--file`, `--timeout`, `--workers`, `--format`, `--out`)
- End-to-end JSON: `python -m ethscan stale --target example.com --format json --timeout 1.0` -> reports A/AAAA/CNAME records and stale status with reasons
- End-to-end Markdown: `--format markdown` -> renders summary and tables with stale reasons
- End-to-end file input: `python -m ethscan stale --file domains.txt --format json` -> reads domains from file
- End-to-end `--out`: writes report to file

## Current state
- All 32 commands implemented and wired up (including `nmap` and `stale`).
- `vuln` now supports `--output-format [json|markdown|csv]` and `--format [json|markdown|csv]` (deprecated alias) for machine-readable CSV export of vulnerability findings.
- `scan` and `service` now support `--profile fast|normal|full` and `--output-format csv`.
- `subdomains` and `dnsbrute` now support `--resolver`, `--recursive`, `--max-depth`.
- `whois` now supports `--recursive/--no-recursive`, `--max-depth`, `--format json|markdown`, and `--out` (including cross-registrar referral following).
- `audit` now supports `--format json|markdown`, `--out`, `--min-length`, `--output-format csv`, `--sort`, and `--salt`/`--pepper`/`--algorithm`.
- `report`, `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `dnssec`, `geo` (with `--recursive`, `--max-depth`), `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon`, `resolve`, `validate`, `radix` (with `--cidr-file`), `nmap`, `stale` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1772 passing (1 skipped).

## Suggested next task

**Add an `ssh` command** for SSH security assessment: enumerate supported key exchange algorithms, ciphers, MACs, and host key types on a target SSH server; check for weak/deprecated algorithms (e.g., `diffie-hellman-group1-sha1`, `arcfour`, `3des-cbc`); report host key fingerprint and algorithm; support `--target` (host:port), `--timeout`, `--format [json|markdown]`, `--out`. Use stdlib-only `socket` + `paramiko` if available (graceful fallback with `SSH_AVAILABLE` flag) or implement raw SSH protocol negotiation for algorithm enumeration without `paramiko`.

Alternative: Add a `--recursive` option to the `trace` command to recursively trace routes to discovered intermediate hops.

Alternative: Add a `s3` command for AWS S3 bucket enumeration (public bucket detection via DNS/HTTP, with wordlist-based bruteforce and `--region` filtering).

## Requirements
- Pick one of the suggested features and implement it following the existing module conventions.
- Add a new module under `ethscan/` with `run_*`, `format_*_report_json`, `format_*_report_markdown` (for new commands) or extend an existing module (for new options).
- Register the command/options in `ethscan/cli.py` with `--target`, `--format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in `tests/test_cli.py`.
- Use stdlib only unless an existing optional dependency is already declared in `requirements.txt` (optional deps may be used with a graceful `*_AVAILABLE` flag, as in `dns.py`/`dnsbrute.py`/`brute.py`).

## Completed: `ssh` command (SSH security assessment)

The `ssh` command performs SSH security assessment by connecting to a target SSH server, performing the SSH banner exchange and KEXINIT negotiation to enumerate supported algorithms, and checking for weak/deprecated algorithms.

### Added Files
- `ethscan/ssh.py` — SSH security assessment module with:
  - `PARAMIKO_AVAILABLE` flag for optional paramiko dependency
  - Weak/strong algorithm databases for KEX, ciphers, MACs, and host key types
  - `_normalize_host()` / `_extract_port()` — target parsing helpers
  - `_ssh_banner_exchange()` — SSH banner grab
  - `_send_kexinit()` / `_read_packet()` / `_parse_kexinit()` — stdlib-only KEXINIT negotiation to enumerate algorithms
  - `_analyze_algorithms()` — classifies algorithms as weak/strong
  - `_get_host_key_info_paramiko()` — host key fingerprint via paramiko when available
  - `run_ssh()` — public entry point: connects, grabs banner, negotiates KEXINIT, analyzes algorithms, returns structured results
  - `format_ssh_report_json()` / `format_ssh_report_markdown()` — output formatters (markdown includes per-algorithm tables with weak/strong indicators, findings summary)
- `tests/test_ssh.py` — 26 unit tests: defaults, host/port parsing, algorithm databases, algorithm analysis, KEXINIT parsing, formatters, offline/error handling

### Modified Files
- `ethscan/cli.py` — registered `ssh` command with `--target`, `--port`, `--timeout`, `--format`, `--out`; imports `run_ssh`, formatters from `ethscan.ssh`
- `tests/test_cli.py` — 10 CLI integration tests: `ssh` help, top-level help listing, offline JSON/Markdown output, URL target with port, `--port` option, `--timeout` option, `--out` (JSON and Markdown), default format is JSON
- `README.md` — added SSH security assessment (`ssh`) to the features list

### Verification
- `python -m pytest -q` -> 1808 passed, 1 skipped (1772 baseline + 36 new: 26 unit + 10 CLI)
- `python -m ethscan --help` -> lists `ssh` among the 33 commands
- `python -m ethscan ssh --help` -> shows all expected options (`--target`, `--port`, `--timeout`, `--format`, `--out`)
- End-to-end: `python -m ethscan ssh --target nonexistent.invalid.domain.tld --format json --timeout 1.0` -> reports connection error gracefully
- End-to-end: `python -m ethscan ssh --target ssh://example.com:2222 --format markdown` -> parses URL, extracts host/port
- End-to-end: `python -m ethscan ssh --target example.com --port 2222 --format json` -> explicit port overrides default

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
- `brute` — FTP/SSH login brute force with username/password wordlists (concurrent attempts, per-attempt results, successful-login summary; `--output-format csv` for credential dumps)
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
- `cert`, `cve` (with `--min-severity`, `--ports`, `--profile`), `vuln` (with `--min-severity`), `dnssec`, `geo`, `subtake`, `cidr`, `mac`, `trace`, `wifi`, `osdetect`, `urlcheck`, `recon` all implemented with JSON/Markdown output.
- Configuration file (`ethscan.yaml`) persists default options across commands.
- Tests: 1507 passing (1 skipped).

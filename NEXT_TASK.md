# Next Task for Next Agent

## What the previous (assigned) task was

The prior agent completed the `snmp` command (stdlib-only SNMP recon via
hand-rolled BER) and suggested implementing a `netbios` command next.
This session **executed and verified** the `netbios` command end-to-end.

## `netbios` command — COMPLETED & VERIFIED

Implemented a stdlib-only (`socket` + raw RFC 1001/1002 NBNS packet
encoding) NetBIOS Name Service reconnaissance command, the LAN-adjacent
companion to `smtp`/`ftp`/`ntp`/`snmp`, filling the final lightweight
network-service recon gap.

### Added
- `ethscan/netbios.py` (new module):
  - `_normalize_target()` — parse `host`, `host:port`, and
    `netbios://host:port` targets (defaults to port 137) — same shape as
    `snmp`/`ntp`/`ftp`.
  - `_encode_name_chars()` / `_decode_name_chars()` — RFC 1001 §14.1
    first-level NetBIOS name encoding (16-byte name+suffix → 32 ASCII chars
    `A`-`P`).
  - `_encode_qname()` — DNS-style first-level question name
    (`length=0x20 + 32 chars + 0x00` root terminator).
  - `_build_nbns_query(name, suffix, transaction_id)` — NBNS NODE STATUS
    request (QTYPE `0x0021`/NBSTAT, QCLASS IN) packet builder for a target
    NetBIOS name (default `"*"`).
  - `_parse_dns_name()` — DNS-style name parser with RFC 1035
    compression-pointer support and loop protection (max 16 jumps).
  - `_parse_name_flags()` — decodes the 16-bit NODE_NAME_FLAGS field into
    group/unique, owner node type (B/P/M-node), permanent/active, conflict,
    and deregister booleans (matches dpkt `NS_NAME_*` bit positions).
  - `_parse_nbtstat_rdata()` — parses NBSTAT RDATA: `NUM_NAMES(1)` +
    18-byte name entries (15-byte raw name + 1 suffix + 2 NAME_FLAGS) +
    6-byte `Unit ID` MAC, with suffix→service mapping and truncation checks.
  - `_parse_nbns_response()` — parses a full NBNS message (header, flags,
    RCODE, QDCOUNT, answers); locates the NBSTAT answer, extracts MAC and
    the name table; raises `ValueError` on malformed/truncated packets.
  - `_send_recv()` — send/receive UDP with injectable `connector` (same
    pattern as `ntp`/`snmp`).
  - `SUFFIX_SERVICE_TYPES` / `RCODE_NAMES` / `NAME_FLAGS_*` constants.
  - `_derive_assessment()` — heuristics: `is_server` (a `<20>` File server
    service name is present), `hostname` (unique `<00>` Workstation name),
    `is_domain_member` (group `<00>` name present).
  - `run_netbios(target, port, timeout, name, suffix, connector)` — sends a
    NODE STATUS query, parses the response, reports `mac`, `names`,
    `num_names`, `is_server`, `hostname`, `is_domain_member`,
    `transaction_id`, and `error`; graceful timeout/parse-error/rcode/error
    handling.
  - `format_netbios_report_json` / `format_netbios_report_markdown`
    (target/host/port/MAC/queried-name header, per-name table with pipe
    escaping, server/hostname/domain assessment, error) /
    `format_netbios_report_csv` (header:
    `target,host,port,mac,names,num_names,is_server,is_domain_member,
    hostname,error`).
- `ethscan/cli.py` — registered the `netbios` command with `--target`,
  `--port`, `--name`, `--suffix`, `--timeout`, `--output-format
  [json|markdown|csv]`, deprecated `--format` alias, and `--out`.
- `tests/test_netbios.py` — **58 unit tests** covering target normalization,
  name encoding/decoding (round-trip, wildcard, padding, invalid chars),
  query construction (header fields, QTYPE/QCLASS, default name), DNS name
  parsing (first-level labels, compression pointer, loop protection,
  truncation), name-flags decoding (group/unique, permanent/transient,
  conflict/deregister, owner node types for B/P/M-node), NBSTAT RDATA
  parsing (names+MAC, group names, truncated entries, unknown suffix,
  missing MAC), full response parsing (full, rcode error, not-a-response,
  truncated header/answer), `_send_recv` (connector pass-through/error/
  argument capture), `run_netbios` (full interaction, timeout, connection
  refused, parse failure, rcode error, not-a-response, no-server heuristic,
  custom name/suffix, port override, URL target, name-table return), and all
  three formatters (JSON/Markdown including no-names/escaping/error cases,
  CSV with comma escaping and error aggregation).
- `tests/test_cli.py` — **11 CLI integration tests** for `netbios`: help
  text/options, top-level listing, `--output-format csv`, csv-with-`--out`,
  deprecated `--format csv` alias, default=JSON, markdown, `--name`
  pass-through, `--suffix` pass-through, `--port`, and offline timeout
  graceful handling.
- `README.md` — added the `netbios` command to the features list.

### Verification
- `python -m pytest -q` → **2398 passed, 1 skipped** (2329 baseline →
  +69 netbios tests: 58 unit + 11 CLI; the 1 skip is the pre-existing
  dnspython-dependent test).
- End-to-end CLI smoke test against a local `socket` fake UDP NBNS server
  (real `socket` wire path) confirmed: 3 names decoded (MYHOST `<00>`
  unique workstation, MYHOST `<20>` file server, WORKGROUP `<00>` group
  domain), MAC `a0:b1:c2:d3:e4:f5`, `is_server=True`, `hostname=MYHOST`,
  `is_domain_member=True`, exit 0.
- `python -m ethscan netbios --help` lists all options; `python -m ethscan
  --help` lists `netbios` alongside `ftp`, `smtp`, `ntp`, and `snmp`.
- Offline timeout (`127.0.0.1:1`, `--timeout 0.2`) returns exit 0 with a
  JSON/markdown/csv error (`node status request failed: timeout`), no crash;
  `--output-format csv`/`json`/`markdown` and `--format csv` alias and
  `--out` all route correctly.

### Packet-format references used
- RFC 1002 §4.2.17/4.2.18 (NODE STATUS REQUEST/RESPONSE layout) and §4.2.18
  NODE_NAME entry (NETBIOS FORMAT NAME 16 bytes + NAME_FLAGS 2 bytes) and
  STATISTICS (UNIT_ID MAC first).
- RFC 1001 §14.1 first-level name encoding.
- Cross-checked the NBSTAT RDATA layout (NUM_NAMES + 18-byte name entries +
  Unit-ID MAC) and NAME_FLAGS bit positions against scapy
  `NBNSNodeStatusResponseService`/`NBNSNodeStatusResponse` and impacket
  `NBNodeStatusResponse`/`NODE_NAME_ENTRY` from the live RFC text and library
  source.

## Suggested next task

Implement a **`redis` command** (Redis reconnaissance) — inline RESP protocol
over TCP 6379: send `PING`/`INFO server`/`CONFIG GET *` probes (configurable)
to detect unauthenticated Redis instances; report server info (redis_version,
os, arch, process_id), role, connected clients, and dangerous-config findings
(bind to 0.0.0.0, no `requirepass`, writable `dir`). This is the last
recon gap alongside `smtp`/`ftp`/`ntp`/`snmp`/`netbios`.

Alternative: an **`smb` command** (SMB/CIFS banner + dialect negotiation +
anon-share enumeration) — heavier (SMB dialect negotiation is fiddly with
hand-rolled NTLM/Negotiate), so prefer `redis` unless SMB is specifically
requested.

Requirements (mirror the smtp/ftp/ntp/snmp/netbios patterns above):
- Add `ethscan/<module>.py` using stdlib `socket`/`struct` only (no new
  deps). `run_*(target, port=..., timeout, connector)` with
  `_normalize_target()`, request builders, response parsers, injectable
  `connector`, graceful timeout/error handling.
- Add `format_*_report_json`, `format_*_report_markdown`,
  `format_*_report_csv`.
- Register the command in `ethscan/cli.py` with `--target`, `--port`,
  feature-specific options, `--timeout`, `--output-format
  [json|markdown|csv]`, deprecated `--format` alias, and `--out`.
- Add `tests/test_<module>.py` (unit tests incl. packet/RESP builders, fake
  connector/TCP cases, formatter JSON/Markdown/CSV cases) and CLI
  integration tests in `tests/test_cli.py` (help, csv/markdown/json, `--out`,
  alias, default-format, offline timeout).
- Update `README.md` features list.

## Session handoff notes
- What changed: `ethscan/netbios.py` (new — NBNS codec + recon + formatters),
  `tests/test_netbios.py` (new — 58 tests), additions to
  `ethscan/cli.py` (import + `netbios` command, +11 lines), additions to
  `tests/test_cli.py` (11 netbios CLI tests), `README.md` (1 netbios feature
  line). No commits made.
- What was verified: full suite green (2398 passed, 1 skipped); real-socket
  CLI smoke test against a local fake UDP NBNS server round-trips names,
  suffixes, service types, MAC, and heuristics; offline timeout and all
  output formats + `--format` alias + `--out` verified via CLI.
- What remains unresolved: nothing blocking for `netbios`. The `redis`/`smb`
  commands remain as proposed next tasks (no prior attempt).
- Approaches that failed: none for netbios. Two test-fixture gaps were
  corrected during the first test run — (1) `_build_nbstat_response` defaulted
  to empty RDATA which made the "not-a-response" path raise a parse error
  instead of the intended "not a response" message (fixed by defaulting the
  fixture to a valid NBSTAT RDATA so the response-parsing path succeeds and
  the `is_response` check is reached); (2) a one-line module bug reading
  `message["is_response"]` instead of `message["flags"]["is_response"]`,
  fixed by using the correct nested key. All corrections were targeted,
  minimal diffs preserving the existing architecture.

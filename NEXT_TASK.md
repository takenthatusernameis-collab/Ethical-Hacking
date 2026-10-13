# Next Task for Next Agent

## What the previous (assigned) task was

The prior agent completed the `ntp` command and left a
suggested next task of implementing an `snmp` command. This
session **executed and verified** the `snmp` command
end-to-end.

## `snmp` command — COMPLETED & VERIFIED

Implemented a stdlib-only (`socket` + hand-rolled BER
encoding/decoding) SNMP reconnaissance command, the natural
companion to `smtp`/`ftp`/`ntp`, filling the remaining
lightweight network-service recon gap.

### Added
- `ethscan/snmp.py` (new module):
  - `_normalize_target()` — parse `host`, `host:port`, and
    `snmp://host:port` targets (defaults to port 161).
  - BER encoders: `_encode_length()` (short/long form),
    `_encode_tlv()`, `_encode_integer()` (minimal two's
    complement), `_encode_octet_string()`, `_encode_base128()`,
    `_encode_oid_value()`, `_encode_oid()`, `_encode_null()`.
  - `_build_get_request(version, community, oids)` — SNMP GET
    request (v1 = version 0, v2c = version 1) for a list of
    OIDs with request-id/error-status/error-index of 0.
  - `_parse_tlv()` — BER TLV parser (rejects indefinite
    lengths, truncated tags/lengths/values).
  - `_parse_oid()` — OID value payload → dotted notation
    (with base-128 multi-byte components).
  - `_decode_varbind_value()` — decodes OCTET STRING, OID,
    INTEGER, Counter32/Gauge32/TimeTicks/Counter64, IpAddress,
    NULL, and SNMPv2 exception values (endOfMibView/noSuchObject/
    noSuchInstance).
  - `_parse_snmp_message()` — parses a full SNMP message
    (request or response): version, community, pdu_type,
    request_id, error_status, error_index, and varbinds
    (`{oid, value, value_type}`); raises `ValueError` on
    malformed/truncated packets.
  - `_send_recv()` — send/receive UDP packets with injectable
    connector (same pattern as `ntp.py`).
  - `_probe_community()` — probes one community string with
    v2c first, then v1 fallback; records validity, version,
    decoded system values, and the last error.
  - `run_snmp(target, port=None, timeout, communities, connector)`
    — probes every requested community (defaults: `public`,
    `private`, `default`, empty string), reports
    `valid_communities`, `snmp_version`, `sysDescr`,
    `sysObjectID`, `sysUpTime` (TimeTicks → ms), `sysName`;
    graceful timeout/error handling.
  - `format_snmp_report_json()` / `format_snmp_report_markdown()`
    (community-probe table, system info, assessment with
    misconfiguration warning for default communities, pipe
    escaping) / `format_snmp_report_csv()` (header:
    `target,host,port,snmp_version,sys_descr,sys_object_id,
    sys_up_time_ms,sys_name,valid_communities,error`).
- `ethscan/cli.py` — registered the `snmp` command with
  `--target`, `--port`, `--communities` (comma-separated,
  whitespace-stripped, empty string preserved), `--timeout`,
  `--output-format [json|markdown|csv]`, deprecated `--format`
  alias, and `--out`.
- `tests/test_snmp.py` — **79 unit tests** covering target
  normalization, all BER encoders, GET-request construction,
  TLV/OID parsing, varbind value decoding (incl. exception
  values), full message parsing (success, error-status,
  truncated, wrong tag, trailing data, noSuchObject varbind),
  `_send_recv` (fake connector), `_probe_community` (valid v2c,
  v2c-timeout→v1-success, all-timeout, connection-refused,
  error-status, parse-failure, unexpected-PDU), `run_snmp`
  (full interaction, multiple valid communities, custom
  communities, empty community, all-timeout error, port
  override, URL target, error-not-masking-success, mismatched
  response community), and all three formatters (JSON/Markdown/
  CSV incl. escaping, no-valid-communities, error aggregation).
- `tests/test_cli.py` — **10 CLI integration tests** for
  `snmp`: help text/options, top-level listing,
  `--output-format csv`, csv-with-`--out`, deprecated
  `--format csv` alias, default=JSON, markdown, `--communities`
  pass-through (with whitespace stripping), `--port`, and
  offline timeout graceful handling.
- `README.md` — added the `snmp` command to the features list.

### Verification
- `python -m pytest -q` → **2329 passed, 1 skipped** (2240
  baseline → +89 snmp tests; the 1 skip is the pre-existing
  dnspython-dependent test).
- End-to-end CLI smoke test against a local `socketserver`
  fake UDP SNMP server (real `socket` wire path) confirmed:
  v2c detection, `valid_communities == ["public"]` (server
  returns noSuchName for other communities), sysDescr
  ("Linux router 5.4.0"), sysUpTime 123456780 ms (12345678
  TimeTicks × 10), exit 0; `--output-format csv`/`json`/
  `markdown` all route correctly; `--out` writes the report;
  `--communities "public"` restricts probing; deprecated
  `--format csv` alias works; an unreachable target
  (`127.0.0.1:1`, `--timeout 0.2`) returns exit 0 with a JSON
  error (`"v1 request failed: timeout"`), no crash.
- `python -m ethscan snmp --help` lists all options;
  `python -m ethscan --help` lists `snmp` among the commands
  alongside `ftp`, `smtp`, and `ntp`.

## Suggested next task

Implement a **`netbios` command** (NetBIOS Name Service
reconnaissance) using stdlib `socket` + raw packet encoding —
send an NBNS name query (UDP 137) for the target host name to
discover NetBIOS names (unique/group, workstation/server
service types) and MAC address; report name flags and
registered-name heuristics. This fills the LAN-adjacent
service-recon gap alongside `smtp`/`ftp`/`ntp`/`snmp`.

Alternative: a **`redis` command** (Redis reconnaissance) —
inline-command protocol over TCP 6379 (`INFO server`, `CLIENT
LIST`, `CONFIG GET *` probes with a configurable command list)
to detect unauthenticated Redis instances; report server info,
role, connected clients, and dangerous-config findings.

Requirements (mirror the smtp/ftp/ntp/snmp patterns above):
- Add `ethscan/<module>.py` using stdlib `socket`/`struct` only
  (no new deps). `run_*(target, port=…, timeout, connector)`
  with `_normalize_target()`, request builders, response
  parsers, injectable `connector`, graceful timeout/error
  handling.
- Add `format_*_report_json`, `format_*_report_markdown`,
  `format_*_report_csv`.
- Register the command in `ethscan/cli.py` with `--target`,
  `--port`, feature-specific options, `--timeout`,
  `--output-format [json|markdown|csv]`, deprecated `--format`
  alias, and `--out`.
- Add `tests/test_<module>.py` (unit tests incl. BER/packet
  builders, fake connector/UDP cases, formatter
  JSON/Markdown/CSV cases) and CLI integration tests in
  `tests/test_cli.py` (help, csv/markdown/json, `--out`,
  alias, default-format, offline timeout).
- Update `README.md` features list.

## Session handoff notes
- What changed: `ethscan/snmp.py` (new — 600+ lines),
  `tests/test_snmp.py` (new — 79 tests), additions to
  `ethscan/cli.py` (import + `snmp` command), additions to
  `tests/test_cli.py` (10 snmp CLI tests), `README.md`
  (1 snmp feature line). No commits made.
- What was verified: full suite green (2329 passed, 1 skipped);
  CLI smoke tests for all three output formats + `--out` +
  `--communities` + `--format` alias + offline timeout against
  a real local UDP SNMP server; the real `socket` wire path
  confirmed correct BER encoding/decoding and TimeTicks→ms
  conversion.
- What remains unresolved: nothing blocking for the `snmp`
  work; the `netbios`/`redis` commands remain as proposed next
  tasks (no prior attempt).
- Approaches that failed: none for snmp. Four initial test
  expectations were corrected after the first run (base-128
  encoding of 16512, per-community error reporting semantics
  — the last version's error is kept, and a mismatched
  response community string still counts as valid); one real
  module gap was fixed (SNMPv2 exception varbind tags
  0x80/0x81/0x82 now surface as `endOfMibView`/`noSuchObject`/
  `noSuchInstance` value types instead of `unknown (0x81)`).
  All fixes were targeted, minimal diffs that preserve the
  existing architecture and patterns.

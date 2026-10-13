# Next Task for Next Agent

## What the previous (assigned) task was

Implement an **`smb` command** (SMB/CIFS banner/dialect reconnaissance) using
stdlib only, following the `netbios`/`redis` command patterns. This was the
suggested next task after `redis` completion (see prior `NEXT_TASK.md`).

## `smb` command — COMPLETED & VERIFIED

Implemented a stdlib-only (`socket`/`struct`) SMB1 `SMB_COM_NEGOTIATE` recon
probe that returns the negotiated dialect, SMB1 SecurityMode, message-signing
policy, and the NTLM server challenge.

### Added
- `ethscan/smb.py` (new module):
  - `DEFAULT_PORT = 445`, `DEFAULT_TIMEOUT`, `DEFAULT_DIALECTS = ("NT LM 0.12", "Samba", "Core", "CorePlus")`.
  - `_normalize_target()` — parse `host`, `host:port`, `smb://host:port` forms; bracketed IPv6; default port 445.
  - `_build_smb1_negotiate_request(dialects)` — raw 32-byte little-endian SMB1 header (`\\xffSMB`, command `0x72`, WordCount=0) + dialect blob (`\\x02` + ASCII name + `\\x00` per dialect).
  - `_parse_smb_response(data)` — parse SMB1 negotiate response: DialectIndex (LE `<H` @ offset 33), SecurityMode byte (@ offset 35), data section ByteCount + server challenge (first 8 bytes). Defensive against short/truncated/non-SMB/SMB2-magic responses via an `error` field (no exceptions).
  - `_send_recv(host, port, request, timeout, connector)` — injectable TCP send/recv mirroring `redis`/`netbios`.
  - `run_smb(target, port=None, timeout, dialects=None, connector=None)` — builds request, sends once, parses, returns a structured result dict (`accessible`, `protocol`, `dialect`, `dialect_index`, `security_mode`, `security_flags`, `user_security`, `challenge_response`, `signing_enabled`, `signing_required`, `challenge`, `banner`, `raw_preview`, `error`).
  - `format_smb_report_json`, `format_smb_report_markdown`, `format_smb_report_csv` — consistent formatters matching the redis/markdown bullet style and CSV conventions.
- `ethscan/cli.py` — imported `run_smb` + formatters and registered the `smb` command with `--target`, `--port`, `--timeout`, `--output-format [json|markdown|csv]`, deprecated `--format` alias (lower precedence), `--out`.
- `tests/test_smb.py` (new, 41 unit tests) — target normalization, request builder structure/dialects, response parsing (full flags, all-signing-flags combo, dialect mapping, 0xFFFF no-dialect, unknown index, challenge extraction incl. NTLMSSP-after-challenge layout, SMB2-magic tolerance, non-SMB/empty/short/truncated), connector send/recv, `run_smb` (reachable, no-common-dialect, timeout, refused, no-response, non-SMB, port override, timeout passthrough, default/custom dialects), and JSON/Markdown/CSV formatters (accessible + inaccessible).
- `tests/test_cli.py` — added 8 CLI integration tests for `smb` (help, top-level listing, CSV output, CSV with `--out`, deprecated `--format csv` alias, default JSON, `--output-format` precedence over `--format`, `--port` passthrough).
- `README.md` — added SMB/CIFS reconnaissance feature description under Features.

### SecurityMode bit decode (verified against nmap `smb-security-mode.nse` + impacket `smb.SMB` constants + MS-SMB 2.2.4.2)
The SMB1 negotiate-response SecurityMode is a single byte (@ offset 35, LE header):
- `0x01` user-level authentication supported (else share-level)
- `0x02` challenge/response (NTLM) authentication supported
- `0x04` message signing enabled (supported)
- `0x08` message signing required
- `DialectIndex == 0xFFFF` → no common dialect agreed.

### Verification
- `python -m pytest -q` → **2470 passed, 1 skipped** (pre-existing TLS skip), no regressions vs. the 2469-baseline+redis run. New: 41 unit tests + 8 CLI tests, all passing.
- CLI smoke tests against a closed local port: graceful `accessible: false` with a structured error in JSON/Markdown/CSV; `--out` writes files; `--output-format`/`--format` precedence and `--port` work.
- Stdlib-only (`socket`/`struct`); injectable connector; follows existing module/formatter conventions; minimal and reversible.

### Packet/Protocol references used
- SMB1 `SMB_COM_NEGOTIATE` (command `0x72`): 32-byte little-endian header (`\xffSMB` + command + status + flags + PIDHigh/PID/UID/MID/TID), WordCount, ByteCount, then dialect descriptors (`\x02` + name + `\x00`). Verified against impacket `smb.py` `NewSMBPacket`/`SMBExtended_Security_Parameters` (header field order/LE, DialectIndex `<H` @33, SecurityMode `<B` @35, WordCount 0x11) and MS-SMB 2.2.4.2.
- SMB1 SecurityMode bit decode confirmed against nmap `scripts/smb-security-mode.nse` (`&1` user vs share, `&2` challenge/response, `&4`/`&8` signing enabled/required).
- SMB2 magic `\xfeSMB` tolerated defensively (not produced by an SMB1 request).

### Notes / known limitations
- Scope is intentionally minimal: a single SMB1 negotiate probe. This reports SMB1 dialect + signing policy, but does **not** perform SMB2/3 negotiation, session setup, or share enumeration. Modern hosts with SMB1 disabled will report `accessible=false` with a connection error. A natural future enhancement is an SMB2/3 `SMB2_NEGOTIATE` request/response parser (dialect revision + version) for modern-server coverage.

## Suggested next task

Implement an **`ldap` command** (LDAP reconnaissance) — a useful, bounded gap that
pairs with the existing directory/protocol recon set (`dns`, `smtp`, `snmp`,
`netbios`). LDAP banner/dialect grabbing + anonymous bind support detection is
straightforward and consistent with the lightweight recon style.

Requirements (mirror existing recon command patterns):
- Add `ethscan/ldap.py` using stdlib `socket`/`struct`/LDAP BER or plain text where possible (no new deps). Implement a minimal LDAP `BIND` probe / banner grab to detect anonymous bind support and the LDAP server identity, with `run_ldap(target, port=389/636, timeout)` + injectable `connector`, `_normalize_target()`, request builders/parsers, and graceful timeout/error handling.
- Add `format_ldap_report_json`, `format_ldap_report_markdown`, `format_ldap_report_csv`.
- Register command in `ethscan/cli.py` with `--target`, `--port`, `--timeout`, `--output-format [json|markdown|csv]`, deprecated `--format` alias, `--out`.
- Add `tests/test_ldap.py` (fake connector, BER/reader unit tests) and CLI integration tests in `tests/test_cli.py` following the `netbios`/`redis`/`smb` style.
- Update `README.md` with a feature description.
- Keep changes minimal and reversible; preserve existing architecture and the working `smb`/`redis`/`netbios` baseline.

Evidence: `smb` is complete and verified (2470 passed, 1 skipped). LDAP is a
common adjacent recon target and fills the remaining directory-protocol gap.

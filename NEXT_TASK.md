# Next Task for Next Agent

## What the previous (assigned) task was

Implement an **`ldap` command** (LDAP reconnaissance) using stdlib
only, following the `netbios`/`redis`/`smb` command patterns. This
was the suggested next task after `smb` completion (see prior
`NEXT_TASK.md`).

## `ldap` command — COMPLETED & VERIFIED

Implemented an RFC 4511 anonymous-bind probe plus a RootDSE search,
both using hand-built BER (ASN.1) encodings with the stdlib only
(`socket`, `ssl` for LDAPS).

### Added
- `ethscan/ldap.py` (new module):
  - `DEFAULT_PORT = 389`, `DEFAULT_LDAPS_PORT = 636`, `DEFAULT_TIMEOUT = 3.0`, `DEFAULT_LDAP_VERSION = 3`.
  - `_normalize_target()` — parses `host`, `host:port`, `ldap://host:port` and `ldaps://host:port` forms; bracketed IPv6; `ldaps://` defaults to port 636.
  - `_int_bytes()` / `_ber_length()` / `_ber_tlv()` — minimal BER encoding helpers (definite-form lengths, sign-bit-safe INTEGERs).
  - `_build_bind_request(version, message_id)` — anonymous BindRequest: LDAPMessage SEQUENCE { messageID INTEGER, BindRequest [APPLICATION 0] SEQUENCE { version INTEGER } }; name/authentication omitted per RFC 4511 anonymous bind.
  - `_build_root_dse_search(message_id)` — SearchRequest [APPLICATION 3] with empty base DN (RootDSE), scope=baseObject, neverDerefAliases, zero limits, typesOnly=FALSE, present filter (`0x87` + "objectClass"), empty attribute list.
  - `_read_length()` / `_read_tlv()` — defensive BER readers (raise ValueError on truncation; never escape to the caller).
  - `_parse_result_content()` — shared BindResponse/SearchResultDone body: optional version INTEGER, resultCode ENUMERATED, matchedDN, diagnosticMessage, referral [3]; unknown elements ignored.
  - `_parse_attribute()` / `_parse_search_entry()` — RootDSE attribute parsing (SEQUENCE { type OCTET STRING, SET OF OCTET STRING }).
  - `_parse_ldap_message()` / `_parse_ldap_response()` — LDAPMessage envelope parser handling multiple messages per buffer (entry + done); malformed/non-LDAP input reported via the `error` field, never raises.
  - `LDAP_RESULT_CODES` — common RFC 4511 result-code names (0 success … 80 other).
  - `_send_recv(host, port, request, timeout, connector=None, use_tls=False)` — injectable TCP transport; `use_tls` wraps the socket with `ssl` (check_hostname/verify disabled, mirroring nmap's LDAP recon scripts).
  - `run_ldap(target, port=None, timeout, ldap_version=3, connector=None)` — two probes, each on its own connection: (1) anonymous bind → `anonymous_bind` (resultCode 0), bind result code/name, matched DN, diagnostic message; (2) RootDSE search → `root_dse` attribute map (vendorName, vendorVersion, namingContexts, supportedLDAPVersion, supportedSASLMechanisms, …). Notes for invalidCredentials (49) and LDAPv3 protocolError (suggests `--ldap-version 2`). LDAPS implied by `ldaps://` scheme or port 636 (`protocol` field reports "LDAPS").
  - `format_ldap_report_json`, `format_ldap_report_markdown`, `format_ldap_report_csv` — consistent with the smb/redis formatters (markdown has Anonymous Bind + Server Identity (RootDSE) sections incl. "Other RootDSE Attributes", notes, raw preview; CSV has 18 columns).
- `ethscan/cli.py` — imported `run_ldap` + formatters; registered the `ldap` command with `--target`, `--port`, `--ldap-version [2|3]` (default 3), `--timeout`, `--output-format [json|markdown|csv]`, deprecated `--format` alias (lower precedence), `--out`.
- `tests/test_ldap.py` (new, 84 unit tests) — target normalization (incl. ldaps:// → 636), BER helpers, bind-request/root-DSE-search builders (structure, version, message id, length consistency), BER reader (short/long form, truncation), response parsing (bind success/49/1/10/unknown-code, version, matchedDN, diagnostic, referral, search entry attributes, entry+done multi-message, empty/truncated/non-LDAP/unknown-op/malformed), `_send_recv` (connector passthrough/error, real refused socket, TLS-against-plain-listener), `run_ldap` (success+RootDSE, bind denied, protocol-error note, v2 no-note, timeout, refused, no-response, port override, version passthrough, send-then-search ordering, malformed bind, RootDSE error/no-response/access-denied/malformed, unresolvable host, ldaps/636 TLS detection), and all three formatters.
- `tests/test_cli.py` — 12 CLI integration tests for `ldap` (help, top-level listing, CSV output, CSV with `--out`, deprecated `--format csv` alias, default JSON, `--output-format` precedence over `--format`, `--port`/`--ldap-version`/`--timeout` pass-through, markdown output).
- `README.md` — added LDAP reconnaissance feature description under Features.

### LDAP probe design (verified against RFC 4511)
- Anonymous BindRequest: `30 08 02 01 01 60 03 02 01 03` (messageID 1, version 3). resultCode 0 → anonymous bind allowed; 49 invalidCredentials / 1 operationsError are the common "anonymous disabled" responses.
- RootDSE search: base object "" (empty DN), scope baseObject, filter `(objectClass=*)` as a present filter (`0x87`), empty attribute list. The entry carries vendorName/vendorVersion/namingContexts/supportedLDAPVersion/supportedSASLMechanisms.
- Each probe opens its own TCP connection (mirrors the redis per-request socket model), so servers that close the connection after a failed bind still get a clean RootDSE attempt.

### Verification
- `python -m pytest -q` → **2566 passed, 1 skipped** (pre-existing TLS skip), up from the 2470-passed baseline. New: 84 unit tests + 12 CLI tests, all passing.
- CLI smoke test against a closed local port: graceful `accessible: false` with `"bind request failed: [Errno 111] Connection refused"` in JSON/Markdown/CSV; `--out` writes files; `--output-format`/`--format` precedence and `--port`/`--ldap-version`/`--timeout` work.
- End-to-end over real sockets (local fake LDAP server answering the bind with a successful BindResponse and the RootDSE search with an entry + SearchResultDone): anonymous bind detected, RootDSE attributes parsed (vendorName/namingContexts/supportedSASLMechanisms), banner built, JSON/Markdown/CSV and `--out` all verified.
- Stdlib-only (`socket`/`ssl`/BER helpers); injectable connector; follows existing module/formatter conventions; minimal and reversible.

### Notes / known limitations
- Scope is intentionally minimal: anonymous bind + RootDSE. It does not perform authenticated binds, paged searches, or attribute-specific queries. LDAPS wraps with certificate verification disabled (recon probe, not PKI validation — same as nmap).
- Each probe uses a fresh connection; servers that require a successful bind before serving searches will report the RootDSE error while still reporting bind status.

## Suggested next task

**Extend `smb` with an SMB2/SMB3 `SMB2_NEGOTIATE` probe** — the prior
`smb` handoff explicitly flagged this as the natural next enhancement:
"Modern hosts with SMB1 disabled will report `accessible=false`… A
natural future enhancement is an SMB2/3 `SMB2_NEGOTIATE`
request/response parser (dialect revision + version) for
modern-server coverage."

Concretely: add an SMB2 negotiate request (protocol id `\xfeSMB`,
StructureSize 25, DialectCount, dialects 0x0202/0x0210/0x0300/0x0302/
0x0311, NegotiateContextCount for SMB 3.1.1) and parse the response
(StructureSize 65, SecurityMode, DialectRevision `<H`, ServerGUID,
Capabilities) to report the negotiated SMB dialect/version on modern
servers. Wire it into `run_smb` as a follow-up probe when the SMB1
negotiate fails or via a `--smb2` flag, with formatters and tests
following the existing `tests/test_smb.py` conventions.

Alternative: add a `memcached` command (text-protocol `version`/`stats`
probe over TCP 11211) or a `mysql` command (server handshake banner
grab + version parse over TCP 3306), both following the
`redis`/`smb`/`ldap` module conventions.

## Requirements
- Follow the existing module conventions: `run_*`, `format_*_report_json`,
  `format_*_report_markdown` (+ `_csv` for protocol probes), injectable
  `connector`, `_normalize_target()`, graceful timeout/error handling.
- Register any new command/options in `ethscan/cli.py` with `--target`,
  `--format`/`--output-format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in
  `tests/test_cli.py` (see `test_ldap.py` / the `test_*_ldap_*` CLI
  tests for the current style).
- Use stdlib only unless an existing optional dependency is already
  declared in `requirements.txt`.
- Keep changes minimal and reversible; preserve the working
  `smb`/`ldap`/`redis` baseline (2566 passed, 1 skipped).

## Current state
- 26 commands implemented (including `ldap`).
- Tests: 2566 passing, 1 skipped (pre-existing TLS skip).
- Verified end-to-end over real sockets with a local fake LDAP server.

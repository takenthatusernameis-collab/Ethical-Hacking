# Next Task for Next Agent

## What the previous (assigned) task was

Extend `smb` with an **SMB2/SMB3 `SMB2_NEGOTIATE` probe** — the
prior `smb` handoff explicitly flagged this as the natural next
enhancement: "Modern hosts with SMB1 disabled will report
`accessible=false`… A natural future enhancement is an SMB2/3
`SMB2_NEGOTIATE` request/response parser (dialect revision +
version) for modern-server coverage."

## `smb --smb2` — COMPLETED & VERIFIED

The previous session had already implemented the SMB2 core in
`ethscan/smb.py` (request builder, response parser, negotiate-context
parsers, `run_smb2`, formatter support) but had NOT wired it into the
CLI, added tests, or updated docs. This session completed the wiring,
tests, and documentation, and fixed two defects in the committed code.

### Completed this session
- `ethscan/smb.py` (`run_smb`):
  - Removed an unreachable duplicated block after `return results`
    (dead code left over from the previous edit).
  - Reordered probes: the SMB1 `SMB_COM_NEGOTIATE` probe runs first
    (primary), then the SMB2/SMB3 `SMB2_NEGOTIATE` probe runs as the
    follow-up when `smb2=True` (previously SMB2 ran before SMB1).
  - SMB1 transport/parse errors no longer early-return before the
    follow-up probe, so a modern host with SMB1 disabled still gets
    its SMB2 dialect reported under the `smb2` key.
- `ethscan/cli.py`:
  - Registered `--smb2/--no-smb2` (default off) on the `smb` command;
    passed through to `run_smb(smb2=...)`. Docstring updated to
    "SMB1 and optional SMB2/SMB3".
- `tests/test_smb.py` — 52 new unit tests (93 total in file):
  - `_build_smb2_negotiate_request`: header/body structure, default and
    custom dialect lists, security-mode/capabilities/ClientGuid
    passthrough, preauth-integrity context required when 0x0311 is
    offered (8-byte alignment, offset, hash algorithm, salt) and
    absent otherwise, explicit salt.
  - `_build_smb2_preauth_integrity_context`: full layout.
  - `_parse_preauth_integrity_context` / `_parse_encryption_capabilities`:
    algorithms/ciphers, multiple entries, short input.
  - `_parse_smb2_negotiate_contexts`: preauth + encryption chaining,
    unknown context types preserved, empty input.
  - `_decode_smb2_capabilities`: none/all flags.
  - `_parse_smb2_response`: full response (StructureSize 65, SecurityMode,
    DialectRevision, ServerGUID, Capabilities, max sizes), all six
    dialect-name mappings, unknown revision, signing flags, negotiate
    contexts from an appended list, wrong structure size, too short,
    SMB1 magic, non-SMB, empty.
  - `_build_smb2_banner`: full banner and non-SMB2 guard.
  - `run_smb2`: accessible via connector (notes for signing
    required/enabled and SMB 2.0.2), timeout, connection refused, no
    response, malformed response, port override, timeout passthrough,
    custom dialects.
  - `run_smb` with `smb2=True`: both probes run in order (SMB1 first,
    then SMB2), `smb2` key absent by default, SMB2 failure does not
    mask SMB1 success, modern-dialect reporting when SMB1 is refused,
    `smb2_dialects` passthrough.
  - Formatters: markdown "SMB2 Negotiation" section (accessible,
    inaccessible, negotiate-context details), JSON nested `smb2` data,
    CSV schema unchanged.
- `tests/test_cli.py` — 4 new CLI tests (12 smb tests total):
  `--smb2`/`--no-smb2` in help, default `smb2=False`, flag passthrough
  both ways; the 7 pre-existing `mock_run_smb` signatures gained the
  `smb2=False` parameter.
- `README.md` — SMB feature description now documents the `--smb2`
  flag, the SMB2/SMB3 dialect list, and the reported fields.

### Verification
- `python -m pytest -q` -> **2622 passed, 1 skipped** (pre-existing
  TLS skip), up from the 2566-passed baseline. New: 52 unit tests +
  4 CLI tests, all passing.
- `python -m ethscan smb --help` -> shows `--smb2 / --no-smb2`.
- End-to-end over a real local TCP socket (fake server answering only
  `\xfeSMB` negotiate requests with a StructureSize-65 SMB 3.1.1
  response, signing required, encryption capability):
  - JSON: SMB1 probe reports `accessible: false` ("negotiate request
    failed: no response") while `smb2.accessible: true`,
    `smb2.dialect: "SMB 3.1.1"`, `smb2.capability_flags:
    ["encryption"]`, ServerGUID parsed.
  - Markdown: `## SMB2 Negotiation` section with dialect, revision
    (785), security mode 0x03, signing required/enabled, Server GUID,
    capabilities, banner, and the signing-required note.

### Design notes
- `--smb2` is opt-in (default off) so the plain `smb` command's
  behavior and output schema are unchanged (smallest reversible change;
  CSV columns unchanged — the SMB2 detail stays in JSON/Markdown).
- Each probe opens its own TCP connection via the injectable
  `_send_recv` connector, so servers that reset the connection after an
  SMB1 negotiate still get a clean SMB2 attempt.
- SMB2 request includes the required `SMB2_PREAUTH_INTEGRITY` negotiate
  context (SHA-512 + random 32-byte salt) whenever dialect 0x0311 is
  offered, per [MS-SMB2]; responses parse preauth-integrity and
  encryption-capability contexts and preserve unknown context types.

## Suggested next task

**Add a `memcached` command** (text-protocol `version`/`stats` probe
over TCP 11211) following the `redis`/`smb`/`ldap` module conventions:
send `version\r\n` and `stats\r\n`, parse the `STAT` lines into a
structured map (uptime, version, bytes, curr_connections, cmd_get/
cmd_set, get_hits/misses, evictions), report accessible/version/stats,
with `--target` (host, host:port, or `memcached://` URL), `--port`
(default 11211), `--probes`, `--timeout`, and
`--output-format [json|markdown|csv]` / `--format` / `--out`, plus
unit tests with an injectable connector and CLI integration tests in
`tests/test_cli.py`.

Alternative: add a `mysql` command (server handshake banner grab +
version parse over TCP 3306), same conventions.

## Requirements
- Follow the existing module conventions: `run_*`, `format_*_report_json`,
  `format_*_report_markdown` (+ `_csv` for protocol probes), injectable
  `connector`, `_normalize_target()`, graceful timeout/error handling.
- Register any new command/options in `ethscan/cli.py` with `--target`,
  `--format`/`--output-format`, `--out`, and feature-specific options.
- Add unit tests in `tests/` and CLI integration tests in
  `tests/test_cli.py` (see `tests/test_smb.py` / the `test_*_smb_*`
  CLI tests for the current style).
- Use stdlib only unless an existing optional dependency is already
  declared in `requirements.txt`.
- Keep changes minimal and reversible; preserve the working
  `smb`/`ldap`/`redis` baseline (2622 passed, 1 skipped).

## Current state
- 26 commands implemented (including `ldap` and the extended `smb`).
- Tests: 2622 passing, 1 skipped (pre-existing TLS skip).
- Verified end-to-end over real sockets with a local fake SMB2 server.

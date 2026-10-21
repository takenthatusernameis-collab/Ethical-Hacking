# NEXT TASK

## Status: COMPLETE (CLI verification of the ten commands, turned permanent)

The task of the previous handoff is done: the CLI was run against an
unreachable target for each of the ten commands (`netbios`, `ftp`, `smtp`,
`scan`, `dnsbrute`, `mysql`, `mongodb`, `postgresql`, `mssql`, `oracle`),
every one printed its own error field and exited 0, and the check is now a
permanent sweep instead of a manual step.

1. **The ten commands were verified through the CLI.** With the transport
   seam patched to raise a `RuntimeError("hostile transport")`:
   - `scan` -> `open_ports=[]`, every `details[].open` is `false`;
   - `dnsbrute` -> `axfr_success=false`, `axfr[0].error="hostile transport"`,
     `resolved=[]` (the raw socket path is the one exercised, so dnspython
     is disabled for the check);
   - `mysql`/`mongodb`/`postgresql`/`mssql`/`oracle` -> `accessible=false`,
     `error="hostile transport"`;
   - `netbios` -> `error="node status request failed: hostile transport"`;
   - `ftp` -> `connected=false`, `error="connection failed: hostile transport"`;
   - `smtp` -> `connected=false`, `error="connection failed: hostile transport"`.
   All exit 0.

2. **The result is a permanent sweep.** `tests/test_cli_unreachable_sweep.py`
   grew from 6 to 16 checks. The ten new checks patch the transport seam the
   module really uses (`ethscan.scanner.socket.create_connection`,
   `ethscan.dnsbrute.socket.create_connection` + `ethscan.dnsbrute.DNS_AVAILABLE`
   + `ethscan.dns.socket.getaddrinfo`, the five `ethscan.<db>.socket.create_connection`
   seams, `ethscan.netbios.socket.socket`, `ethscan.ftp._connect`,
   `ethscan.smtp._connect`), run the command through `CliRunner` and assert
   exit 0, no traceback and the command's own failure signal. It is hermetic:
   no network is needed and the result does not depend on what the machine
   can reach.

3. **The checks are meaningful.** Four of them were proved by reverting a
   guard and watching the check fail: removing `RuntimeError` from the
   scanner's, dnsbrute's and netbios' socket exception tuple makes the sweep
   exit 1 with the `RuntimeError` escaping; the same for the mysql connector
   seam. With the guards restored all 16 pass.

`python -m ruff check ethscan/ tests/` -> All checks passed.
`python -m pytest tests/` -> **5060 passed, 48 skipped, 2 warnings** (baseline
5050 passed, 48 skipped; the +10 are the new CLI checks). `git diff --check`
clean. Nothing is committed.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash
  into the module's documented error signal.
- Keep the permanent sweeps in the repository.
- Do not commit unless explicitly asked.

## One precise next task

Extend the permanent CLI-level sweep to the network commands that still have
no failure-field check at the CLI level: `redis`, `memcached`, `ntp`, `ldap`,
`smb`, `snmp`, `ssh`, `dnssec`, `ssl`, `tls`, `whois` and `service`.

The method is the one of `tests/test_cli_unreachable_sweep.py`: patch the
transport seam the module really uses (the `connector(host, port, request,
timeout)` seam for the protocol modules, the socket seam for the others),
run the command through `CliRunner`, and assert that it exits 0, leaks no
traceback and prints the module's own failure signal. The signal differs per
command, so assert the signal the module documents, not a fixed wording.

The list of the commands that still have no such check is in
`HANDOFF_NEXT.md` under "What remains unresolved".

(End of file - total 60 lines)
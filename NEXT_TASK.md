# NEXT TASK

## Status: COMPLETE (CLI verification of the six commands, turned permanent)

The task of the previous handoff is done: the CLI was run against an
unreachable target for each of the six commands (`ping`, `osdetect`,
`resolve`, `dns`, `stale`, `subdomains`), every one printed its own error
field and exited 0, and the check is now a permanent sweep instead of a
manual step.

1. **The six commands were verified through the CLI.** `ping` against
   `192.0.2.1` -> `response_type="NO-RESPONSE"`, `error="connect error 11"`,
   `failed=1`; `osdetect` -> `response="NO-RESPONSE"`,
   `error="connection timed out"`; `resolve`/`dns` -> empty `records`;
   `stale` -> `A=[]`, `stale=True`; `subdomains` -> `resolved=[]` with every
   `ip is None`. All exit 0.

2. **The result is a permanent sweep.** `tests/test_cli_unreachable_sweep.py`
   (new, 6 checks) patches the transport seam the module really uses, runs the
   command through `CliRunner` and asserts exit 0, no traceback and the
   command's own failure signal. It is hermetic: no network is needed and the
   result does not depend on what the machine can reach.

3. **One latent flake was fixed.** The first full-suite run failed on
   `tests/test_option_sweep.py::...[subtake]` (`timed out after 5s`). The
   `subtake` command does 78 DNS round trips (26 labels, three record types
   each) and needs 6.1s when the resolver does not answer, which is over the
   5s alarm of that sweep. `subtake` now joins `subdomains` in `DNS_COMMANDS`
   and gets the 20s timeout the file already gives to the command with the
   same DNS-per-label behaviour.

`python -m ruff check ethscan/ tests/` -> All checks passed.
`python -m pytest tests/` -> **5050 passed, 48 skipped, 2 warnings** (baseline
5044 passed, 48 skipped; the +6 are the new CLI checks). `git diff --check`
clean. Nothing is committed.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash
  into the module's documented error signal.
- Keep the permanent sweeps in the repository.
- Do not commit unless explicitly asked.

## One precise next task

Extend the permanent CLI-level sweep to the network commands that still have
no failure-field check at the CLI level, starting with the ten commands of
the session before this one: `netbios`, `ftp`, `smtp`, `scan` (scanner),
`dnsbrute`, `mysql`, `mongodb`, `postgresql`, `mssql`, `oracle`.

The method is the one of `tests/test_cli_unreachable_sweep.py`: patch the
transport seam the module really uses (the
`connector(host, port, request, timeout)` seam for the protocol modules, the
socket seam for the others), run the command through `CliRunner`, and assert
that it exits 0, leaks no traceback and prints the module's own failure
signal. The signal differs per command, so assert the signal the module
documents, not a fixed wording.

The list of the commands that still have no such check is in
`HANDOFF_NEXT.md` under "What remains unresolved".

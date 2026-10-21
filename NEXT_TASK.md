# NEXT TASK

## Status: COMPLETE (the CLI-level sweep is complete for every command that opens a transport of its own, except the three aggregators)

The task of the previous handoff is done. The permanent CLI-level sweep now
covers 40 of the 53 commands, every command that opens a transport of its
own, except the three aggregators `vuln`, `recon` and `report`.

## What this session changed

1. **A regression of the previous session is fixed.** The `run_brute`
   wrapper of `ethscan/cli.py` was defined below the `__main__` guard, so
   `python -m ethscan.cli brute ...` died with
   `NameError: name 'run_brute' is not defined` (exit 1, no report). The
   wrapper is now defined above the guard.

2. **The trace and brute sweep is complete and proved.** The file
   `tests/test_cli_trace_brute_unreachable_sweep.py` was rewritten in the
   conventions of the other sweeps and grew from three to six checks: the
   FTP client that cannot be constructed, the SSH login that fails and the
   SSH client that cannot be constructed are new. The two new ones exposed
   a second instance of the defect of `ethscan/brute.py:110` in the SSH
   branch (`paramiko.SSHClient()` was built outside the guard); it is
   fixed.

3. **Two sources of flakiness are gone.** The `cert` command fetches
   certificate transparency data from `crt.sh` and the `whois` command
   talks to a whois server, so the two option sweeps depended on the
   latency of the internet and tripped their own five second alarm. A
   shared fixture (`tests/conftest.py`) keeps them off the internet.

4. **Four commands no longer crash on a resolver failure.** A resolver
   that fails with an error type the modules did not name in their guards
   (a plain `OSError`) escaped the `cert`, `geo`, `mac` and `ping`
   commands with a traceback (exit 1). All four now report the failure
   (exit 0), and the `ping` command no longer lets a `connect_ex` failure
   of an unknown type escape either.

5. **The entry-point regression has a permanent check.** `tests/test_main.py`
   now asserts that the `__main__` guard is the last statement of the
   three entry-point modules, and that the `brute` command runs when
   `ethscan/cli.py` is executed as `__main__`.

## What was actually verified

- The crash was reproduced before the fix and is gone after it.
- Every new check was proved by reverting the guard of its own module and
  watching the check fail; with the guards restored all of them pass.
- The new checks are hermetic: 20 passed with the network blocked (a
  plugin that raises on every connection and on every name lookup that is
  not a numeric address; the plugin is not part of the repository).
- The two option sweeps were run three times in a row: 97 passed, 9
  skipped, every time.
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **5097 passed, 48 skipped, 3 warnings**
  (baseline at the start of the session: 5085 passed, 48 skipped, 2
  warnings). The suite was run twice in a row with the same result.
- `git diff --check` -> clean. Nothing is committed.

The full evidence, the mutation table and the open points are in
`HANDOFF_NEXT.md`.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the
  crash into the module's documented error signal.
- Keep the permanent sweeps in the repository, and prove every new check by
  reverting the guard of its own module.
- Do not commit unless explicitly asked.

## One precise next task

Extend the permanent CLI-level sweep to the last three commands that open a
transport of their own without a failure-field check at the command line:
the aggregators `vuln`, `recon` and `report`.

The method is the one of `tests/test_cli_unreachable_sweep.py`,
`tests/test_cli_http_unreachable_sweep.py` and
`tests/test_cli_trace_brute_unreachable_sweep.py`: patch the transport the
command really opens, run the command through `CliRunner`, and assert that
it exits 0, leaks no traceback and prints the command's own failure signal.

What is already known about the three commands:

- `vuln` (`--target`, optional `--services-file`, `--tls-file`,
  `--ssl-file`): the services file lists the ports to probe, so a check
  needs a file with one port.
- `recon` (`--target`, optional `--modules`): the modules of the recon run
  can be limited with `--modules`, so a check can pick the ones that open a
  socket and leave the rest out.
- `report` (`--target`, optional `--audit-file`): it scans the ports of the
  target and audits the credentials.

The other open points (the process-wide side effect of
`socket.setdefaulttimeout()`, the `python ethscan/cli.py` script path) are
in `HANDOFF_NEXT.md` under "What remains unresolved".

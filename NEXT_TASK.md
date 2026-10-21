# NEXT TASK

## Status: COMPLETE (CLI-level sweep extended to the HTTP-facing commands)

The task of the previous handoff is done: the permanent CLI-level sweep now
covers the ten HTTP-facing commands (`web`, `headers`, `fuzz`, `urlcheck`,
`cert`, `geo`, `mac`, `s3`, `cve` and `subtake`), each of them printing its
own failure signal and exiting 0.

1. **The ten commands were verified through the CLI.** With the transport
   seam patched to raise a `RuntimeError("hostile transport")`:
   - `web` -> `error="header fetch failed: hostile transport"`,
     `ssl.error="hostile transport"`, no header;
   - `headers` -> `error="header fetch failed: hostile transport"`, no
     header;
   - `fuzz` -> `error="hostile transport"` on every probed path, no finding;
   - `urlcheck` -> `web.error`, `ssl.error` and the error of every fuzzed
     path;
   - `cert` -> `cert_data.error="Failed to fetch certificate transparency
     data"`;
   - `geo` -> `geolocation.error="Failed to fetch geolocation data"`;
   - `mac` -> `mac_data.error="Failed to fetch MAC vendor data"`;
   - `s3` -> `error="hostile transport"` on every probed bucket, no public
     bucket;
   - `cve` -> `error="NVD lookup failed for CVE-2016-6210: Failed to fetch
     CVE data"`;
   - `subtake` -> the subdomain is reported without a CNAME and
     `vulnerable=false`.
   All exit 0.

2. **The result is a permanent sweep.** `tests/test_cli_http_unreachable_sweep.py`
   holds the ten checks. Each one patches the transport the module really
   opens (the command line never injects a transport), runs the command
   through `CliRunner` and asserts exit 0, no traceback and the command's own
   failure signal. It is hermetic: the transport is patched, so it needs no
   network and the result does not depend on what the machine can reach.

3. **The checks are meaningful.** All ten were proved by reverting the guard
   of their own module (narrowing the broad `except Exception` to
   `except ValueError`, dropping `RuntimeError` from the caught tuple, or
   dropping the reason of the failure) and watching the matching check fail.
   With the guards restored all ten pass.

4. **The checks are hermetic.** The file was run with the network blocked (a
   plugin that raises on every connection and on every name lookup that is
   not a numeric address): 10 passed. The plugin was used for the proof
   only and is not part of the repository.

`python -m ruff check ethscan/ tests/` -> All checks passed.
`python -m pytest tests/` -> **5082 passed, 48 skipped, 2 warnings** (baseline
5072 passed, 48 skipped; the +10 are the checks of the rewritten file).
`git diff --check` clean. Nothing is committed.

The file was already in the repository as a draft. It was rewritten, because
the draft proved nothing (`test_fuzz` had no assertion and probed an empty
wordlist), depended on the filesystem cache (`cert`, `geo`, `mac`, `cve` ran
with the cache enabled) and on the real resolver (`s3`, `subtake`).

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the
  crash into the module's documented error signal.
- Keep the permanent sweeps in the repository.
- Do not commit unless explicitly asked.

## One precise next task

Extend the permanent CLI-level sweep to the two commands that still open a
transport of their own without a failure-field check at the command line:
`trace` and `brute` (the aggregators `vuln`, `recon` and `report` have
their modules covered one level down).

The method is the one of `tests/test_cli_unreachable_sweep.py` and
`tests/test_cli_http_unreachable_sweep.py`: patch the transport the module
really opens, run the command through `CliRunner`, and assert that it exits
0, leaks no traceback and prints the module's own failure signal.

The expected signals are already measured:

- `trace`: patching `ethscan.trace.socket.gethostbyname` gives exit 0,
  `error="hostile transport"`, `reached=false`; patching
  `ethscan.trace.socket.socket` gives exit 0, `error="hostile transport"` and
  a hop whose `error_code` is the failure.
- `brute`: patching `ethscan.brute.FTP` with a stand-in class whose
  `connect` raises gives exit 0, `attempts=1`, `successful_count=0` and
  `results[0]["error"]="hostile transport"`. The command line takes the
  wordlists as `--user-file` and `--pass-file`.

The brute check may expose the defect of `ethscan/brute.py:110`, where the
FTP client is built outside the guard of `_attempt_ftp`: a failure of the
constructor escapes the command (exit 1 with a bare `RuntimeError`). The
smallest fix is to build the client inside the `try:`.

The list of the commands that still have no such check, and the other open
points, are in `HANDOFF_NEXT.md` under "What remains unresolved".

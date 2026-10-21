# NEXT TASK

## Status: COMPLETE (the CLI-level sweep covers every command that opens a transport of its own)

The task of the previous handoff is done. The permanent CLI-level sweep now
covers 43 of the 53 commands: every command that opens a transport of its
own, the three aggregators `vuln`, `recon` and `report` included.

## What this session changed

1. **The `vuln` command no longer crashes on a JSON document it cannot
   read.** The command reads the output of other commands from a file
   (`--services-file`, `--tls-file`, `--ssl-file`). The CLI checked that the
   file holds an object and nothing else, so a document whose *shape* was
   wrong reached the library and died with a traceback (exit 1, no report):
   eight distinct crashes, from `AttributeError: 'str' object has no
   attribute 'get'` to `TypeError: '<' not supported between instances of
   'str' and 'int'`. The library now reads those documents as foreign data:
   what cannot be read is skipped and named in the notes of the report
   (`Service data holds no 'results' list`, `TLS data holds no
   'supported_versions' list`, `Certificate data holds no 'cert' object`).

2. **A permanent CLI-level sweep for the three aggregators.**
   `tests/test_cli_aggregator_unreachable_sweep.py` (new, 9 checks) patches
   the transport each command really opens, runs the command through
   `CliRunner` and asserts that it exits 0, leaks no traceback and prints the
   command's own failure signal: the notes of the vuln report, the closed
   ports of the report scan section, the failure of each recon module.

3. **The partial work of the interrupted session was replaced.** Commit
   `1ea280d` added four checks to `tests/test_cli_unreachable_sweep.py`, two
   of them under the same name (`test_recon_cli_reports_module_failures`):
   the second definition shadowed the first, `ruff check` failed with F811,
   and the shadowed check would have failed as well (with the transports of
   the recon modules patched, every module reports its own failure and the
   notes stay empty, so its assertion `len(report["notes"]) > 0` was wrong).
   The file is back to its state before that commit and the checks live in
   the new sweep file.

## What was actually verified

- Every one of the eight crashes was reproduced at the command line before
  the fix and is gone after it (exit 0 with the note that names the file).
- Every new check was proved by reverting the guard of its own module and
  watching the check fail; with the guards restored all of them pass.
- The new sweep is hermetic: it runs with the `no_external_network` fixture
  of `tests/conftest.py`, so a transport that a check forgot to patch fails
  at once instead of reaching the network (9 passed in 0.13 s).
- `python -m ruff check ethscan/ tests/` -> **All checks passed**.
- `python -m pytest tests/` -> **5115 passed, 48 skipped, 3 warnings**
  (baseline at the start of the session: 5148 collected, of which 3 ran and
  1 was shadowed; the +15 are the 9 new CLI checks and the 9 new module
  checks minus the 3 partial checks that were removed).
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

The two commands that read the same kind of JSON document from a file and
still crash on a document they cannot read: `cve` and `osdetect`.

- `cve --services-file` with `{"results": [{"port": 22, "banner": 5}]}` dies
  with `TypeError: expected string or bytes-like object, got 'int'`
  (`ethscan/cve.py`, the banner is handed to `parse_banner` unchanged).
- `osdetect --banners-file` with `{"results": "abc"}` dies with
  `AttributeError: 'str' object has no attribute 'get'`
  (`ethscan/cli.py`, the entries of the file are read as objects).

The fix is the one of `ethscan/vuln.py` of this session: read the document as
foreign data, skip what cannot be read and name it in the notes of the
report. Give both commands a permanent check in the same sweep (the sweep
file of this session already holds the checks of the commands that read a
document from a file).

The other open points (the process-wide side effect of
`socket.setdefaulttimeout()`, the `python ethscan/cli.py` script path) are in
`HANDOFF_NEXT.md` under "What remains unresolved".

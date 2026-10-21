# NEXT TASK

## Status: COMPLETE (six remaining commands in the transport-failure sweep)

The optional extension from `HANDOFF_NEXT.md` / `TASK.md` is done: the six
commands that still let a transport failure of an unnamed type escape
(`ping`, `osdetect`, `resolve`, `dns`, `stale`, `subdomains`) are now covered
by the permanent protocol sweep and by regression tests next to each module's
own tests.

1. **`ethscan/ping.py` fixed.** `_try_create_raw_socket` also catches
   `RuntimeError`, and the TCP-fallback socket creation is guarded so a socket
   that cannot be created is reported as a failed probe (`NO-RESPONSE`,
   `error = str(exc)`) instead of crashing `run_ping`. The other five commands
   already caught `RuntimeError` on their socket seams.

2. **Sweep checks added.** `tests/test_protocol_hostile_sweep.py` gained one
   check per command (+6). Each patches the module's own socket seam to raise
   `RuntimeError` and asserts the module's own failure field.

3. **Regression tests added next to each module's own tests** (+1 test each in
   `test_ping.py`, `test_osdetect.py`, `test_resolve.py`, `test_dns.py`,
   `test_stale.py`, `test_subdomains.py`).

`python -m ruff check ethscan/ tests/` -> All checks passed.
`python -m pytest tests/` -> **5044 passed, 48 skipped, 2 warnings** (baseline
5032 passed, 48 skipped; the +12 are the new checks). `git diff --check` clean.
Nothing is committed.

## Constraints

- Smallest reversible change; do not weaken an existing guard; turn the crash
  into the module's documented error signal.
- Add regression tests next to the module's own tests; keep the permanent
  sweeps in the repository.
- Do not commit unless explicitly asked.

## One precise next task

Run the CLI against an unreachable target for each of the six commands
(`ping`, `osdetect`, `resolve`, `dns`, `stale`, `subdomains`) and confirm each
prints its own error field and exits 0, mirroring the verification done for the
ten commands in the previous session
(`ethscan <cmd> --target 127.0.0.1` -> error field printed, exit 0).
